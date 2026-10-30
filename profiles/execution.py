from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from inspect import signature
from typing import Any

from graphql.error import GraphQLError, located_error
from graphql.execution.execute import ExecutionContext, get_field_def
from graphql.execution.values import get_argument_values
from graphql.language import FieldNode, OperationType
from graphql.pyutils import AwaitableOrValue, Path
from graphql.type.definition import (
    GraphQLNamedType,
    GraphQLObjectType,
    GraphQLOutputType,
    GraphQLResolveInfo,
    get_named_type,
)

from profiles.models import Address, Email, Phone, Profile

# graphql-core 3.2.6 omits path in handle_field_error; 3.2.12 requires it.
# Inspect the signature to support both versions without a version-number check.
# Remove this check and _dispatch_field_error once support for 3.2.6 is dropped.
_HANDLE_FIELD_ERROR_ACCEPTS_PATH = (
    "path" in signature(ExecutionContext.handle_field_error).parameters
)


# GraphQL contact field -> Django model and attribute storing its prefetched rows.
CONTACT_FIELDS = {
    "primaryEmail": (Email, "_primary_emails"),
    "primaryPhone": (Phone, "_primary_phones"),
    "primaryAddress": (Address, "_primary_addresses"),
}

# GraphQL object type names whose results are Profile instances.
PROFILE_RESULT_TYPE_NAMES = {"ProfileNode", "RestrictedProfileNode"}


@dataclass
class _ResolvedRootField:
    """Keep a raw root result with the metadata needed to complete it later."""

    response_name: str
    info: GraphQLResolveInfo
    value: Any


def _iter_profiles_in_result(value: Any) -> Iterator[Profile]:
    """Yield Profile instances from a single or nested list/tuple resolver result.

    Used to collect profiles for contact batching, ignoring non-profile values.
    """
    if isinstance(value, Profile):
        yield value
    elif isinstance(value, list | tuple):
        for item in value:
            yield from _iter_profiles_in_result(item)


class PrimaryContactBatchingExecutionContext(ExecutionContext):
    """Batch primary contacts across query roots before completing child fields.

    When a query selects primary contacts, delay root completion so several
    profile roots can share contact queries. Mutations use the base executor
    and keep their standard order.

    Root field resolution follows graphql-core's synchronous execute_field
    flow. The custom code saves root results, fetches contacts, and completes
    them afterward. The base executor still handles operation setup and nested
    fields. Reference: graphql-core v3.2.12:
    https://github.com/graphql-python/graphql-core/blob/v3.2.12/src/graphql/execution/execute.py
    """

    def execute_fields(
        self,
        parent_type: GraphQLObjectType,
        source_value: Any,
        path: Path | None,
        fields: dict[str, list[FieldNode]],
    ) -> AwaitableOrValue[dict[str, Any]]:
        # The base execute_operation handles root lookup, field collection, and routing.
        # Only batch top-level queries; nested fields use the standard executor.
        if self.operation.operation != OperationType.QUERY or path is not None:
            return super().execute_fields(parent_type, source_value, path, fields)

        profile_roots = self._find_profile_roots_requesting_primary_contacts(
            parent_type, fields
        )
        # No primary contact fields selected; use standard execution.
        if not profile_roots:
            return super().execute_fields(parent_type, source_value, path, fields)

        resolved_fields = self._resolve_root_fields(parent_type, source_value, fields)
        contact_batches = self._collect_contact_batches(resolved_fields, profile_roots)

        # Fetch requested contacts in one batch per contact type across all roots.
        self._prefetch_primary_contacts(contact_batches)

        # Child resolvers can now read contacts attached to every profile instance.
        return self._complete_root_fields(resolved_fields)

    @staticmethod
    def _collect_contact_batches(
        resolved_fields: list[_ResolvedRootField],
        profile_roots: dict[str, tuple[GraphQLNamedType, set[str]]],
    ):
        """Collect profile instances for each selected primary-contact field."""
        contact_batches = {
            field_name: defaultdict(list) for field_name in CONTACT_FIELDS
        }

        for field in resolved_fields:
            # Skip null and exception results before collecting contacts.
            if field.value is None or isinstance(field.value, Exception):
                continue
            profile_root = profile_roots.get(field.response_name)
            if profile_root is None:
                continue

            profile_schema_type, requested_contact_fields = profile_root
            if profile_schema_type.name == "ProfileNodeConnection":
                profile_instances = (edge.node for edge in field.value.edges)
            else:
                profile_instances = _iter_profiles_in_result(field.value)

            for profile in profile_instances:
                for field_name in requested_contact_fields:
                    contact_batches[field_name][profile.pk].append(profile)

        return contact_batches

    def _get_profile_result_type(
        self,
        parent_type: GraphQLObjectType,
        field_nodes: list[FieldNode],
    ) -> GraphQLNamedType | None:
        """Return a supported GraphQL schema type, or None for unrelated fields."""
        field_def = get_field_def(self.schema, parent_type, field_nodes[0])
        if not field_def:
            return None

        # The federated _entities field can return profiles, so include it in
        # contact batching.
        if field_nodes[0].name.value == "_entities":
            return self.schema.get_type("ProfileNode")

        result_type = get_named_type(field_def.type)
        if result_type is not None and (
            result_type.name == "ProfileNodeConnection"
            or result_type.name in PROFILE_RESULT_TYPE_NAMES
        ):
            return result_type
        return None

    def _collect_connection_profile_selections(
        self, connection_schema_type, field_nodes: list[FieldNode]
    ) -> dict[str, list[FieldNode]]:
        """Collect query field selections under a connection's edges -> node.

        Returns selected GraphQL field nodes.
        """
        edge_schema_type = get_named_type(connection_schema_type.fields["edges"].type)
        profile_schema_type = get_named_type(edge_schema_type.fields["node"].type)
        profile_field_nodes = []
        connection_selections = self.collect_subfields(
            connection_schema_type, field_nodes
        )
        for edge_nodes in connection_selections.values():
            if edge_nodes[0].name.value != "edges":
                continue
            edge_fields = self.collect_subfields(edge_schema_type, edge_nodes)
            for node_nodes in edge_fields.values():
                if node_nodes[0].name.value == "node":
                    profile_field_nodes.extend(node_nodes)

        if not profile_field_nodes:
            return {}
        return self.collect_subfields(profile_schema_type, profile_field_nodes)

    def _get_profile_contact_fields(
        self, profile_schema_type, field_nodes: list[FieldNode]
    ) -> set[str]:
        """Return the selected primary-contact fields for a profile result."""
        if profile_schema_type.name == "ProfileNodeConnection":
            profile_selections = self._collect_connection_profile_selections(
                profile_schema_type, field_nodes
            )
        else:
            profile_selections = self.collect_subfields(
                profile_schema_type, field_nodes
            )

        return {
            field_node.name.value
            for field_nodes in profile_selections.values()
            for field_node in field_nodes
        }.intersection(CONTACT_FIELDS)

    def _find_profile_roots_requesting_primary_contacts(
        self,
        parent_type: GraphQLObjectType,
        fields: dict[str, list[FieldNode]],
    ) -> dict[str, tuple[GraphQLNamedType, set[str]]]:
        """Find profile roots that select primary-contact fields."""
        profile_roots = {}
        for response_name, field_nodes in fields.items():
            profile_schema_type = self._get_profile_result_type(
                parent_type, field_nodes
            )
            if profile_schema_type is None:
                continue

            requested_contact_fields = self._get_profile_contact_fields(
                profile_schema_type, field_nodes
            )
            if requested_contact_fields:
                profile_roots[response_name] = (
                    profile_schema_type,
                    requested_contact_fields,
                )

        return profile_roots

    def _dispatch_field_error(
        self,
        error: GraphQLError,
        return_type: GraphQLOutputType,
        path: Path,
    ) -> None:
        """Call graphql-core's error handler with the arguments it supports."""
        if _HANDLE_FIELD_ERROR_ACCEPTS_PATH:
            self.handle_field_error(error, return_type, path)
        else:
            self.handle_field_error(error, return_type)

    def _resolve_root_fields(
        self,
        parent_type: GraphQLObjectType,
        source_value: Any,
        fields: dict[str, list[FieldNode]],
    ) -> list[_ResolvedRootField]:
        """Run root resolvers without executing their child fields.

        Mirrors ExecutionContext.execute_field's field lookup, middleware,
        resolver invocation, and error handling. Unlike the base method, save
        raw results instead of completing them here; awaitables are not handled.
        """
        resolved_fields = []
        for response_name, field_nodes in fields.items():
            field_path = Path(None, response_name, parent_type.name)
            field_def = get_field_def(self.schema, parent_type, field_nodes[0])
            # Match the base executor's guard for queries run without validation.
            if not field_def:
                continue

            resolve_fn = field_def.resolve or self.field_resolver
            if self.middleware_manager:
                resolve_fn = self.middleware_manager.get_field_resolver(resolve_fn)
            info = self.build_resolve_info(
                field_def, field_nodes, parent_type, field_path
            )

            try:
                args = get_argument_values(
                    field_def, field_nodes[0], self.variable_values
                )
                result = resolve_fn(source_value, info, **args)
            except Exception as raw_error:
                error = located_error(raw_error, field_nodes, field_path.as_list())
                self._dispatch_field_error(error, field_def.type, field_path)
                result = None

            # The code above follows ExecutionContext.execute_field's resolver flow.
            # Save the raw result to complete it after contact batching.
            resolved_fields.append(_ResolvedRootField(response_name, info, result))

        return resolved_fields

    @staticmethod
    def _prefetch_primary_contacts(contact_batches: dict) -> None:
        """Fetch each contact type's batch and attach rows to its profile instances."""
        for field_name, profiles_by_id in contact_batches.items():
            model, prefetched_name = CONTACT_FIELDS[field_name]
            profile_ids = []
            for profile_id, profile_instances in profiles_by_id.items():
                if any(
                    not hasattr(profile, prefetched_name)
                    for profile in profile_instances
                ):
                    profile_ids.append(profile_id)

            if not profile_ids:
                continue

            contacts_by_profile_id = defaultdict(list)
            contacts = model.objects.filter(
                profile_id__in=profile_ids, primary=True
            ).order_by("profile_id", "id")
            for contact in contacts.iterator():
                contacts_by_profile_id[contact.profile_id].append(contact)

            for profile_id in profile_ids:
                for profile in profiles_by_id[profile_id]:
                    setattr(
                        profile,
                        prefetched_name,
                        contacts_by_profile_id.get(profile_id, []),
                    )

    def _complete_root_fields(
        self, resolved_fields: list[_ResolvedRootField]
    ) -> dict[str, Any]:
        """Complete saved root values after their contacts have been attached.

        Mirrors execute_field's synchronous completion/error handling and
        execute_fields' response assembly, but uses saved results without
        rerunning resolvers. The recursive complete_value method is inherited.
        """
        results = {}
        for field in resolved_fields:
            info = field.info
            try:
                result = self.complete_value(
                    info.return_type,
                    info.field_nodes,
                    info,
                    info.path,
                    field.value,
                )
            except Exception as raw_error:
                error = located_error(raw_error, info.field_nodes, info.path.as_list())
                self._dispatch_field_error(error, info.return_type, info.path)
                result = None

            results[field.response_name] = result

        return results
