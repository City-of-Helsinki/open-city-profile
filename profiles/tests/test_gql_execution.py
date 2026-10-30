from unittest.mock import Mock

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from graphene import relay
from graphql.execution.execute import ExecutionContext
from graphql.pyutils import Undefined
from graphql.type.definition import GraphQLNonNull

from open_city_profile.schema import schema
from profiles.execution import PrimaryContactBatchingExecutionContext
from profiles.models import Address, Email, Phone
from profiles.schema import ProfileNode
from services.tests.factories import AllowedDataFieldFactory, ServiceConnectionFactory

from ..helpers import to_global_id
from .factories import (
    AddressFactory,
    ClaimTokenFactory,
    EmailFactory,
    PhoneFactory,
    ProfileFactory,
    TemporaryReadAccessTokenFactory,
)


def _count_contact_queries(captured_queries):
    """Count captured SQL statements touching each contact table."""
    query_counts = {model._meta.db_table: 0 for model in (Address, Email, Phone)}
    for captured_query in captured_queries.captured_queries:
        sql = captured_query["sql"].lower()
        for table_name in query_counts:
            if table_name in sql:
                query_counts[table_name] += 1
    return query_counts


def _expected_contact_query_counts(*, address_count, email_count, phone_count):
    return {
        Address._meta.db_table: address_count,
        Email._meta.db_table: email_count,
        Phone._meta.db_table: phone_count,
    }


@pytest.fixture
def make_primary_contacts():
    """Return a factory for selected primary contacts on an existing profile."""
    factories = {
        "email": EmailFactory,
        "phone": PhoneFactory,
        "address": AddressFactory,
    }

    def create_contacts(profile, fields=("email", "phone", "address")):
        return {
            field_name: factories[field_name](profile=profile, primary=True)
            for field_name in fields
        }

    return create_contacts


@pytest.fixture
def allow_service_fields(service):
    """Return a callable granting the service access to the specified fields."""

    def allow_fields(*field_names):
        service.allowed_data_fields.add(
            *(
                AllowedDataFieldFactory(field_name=field_name)
                for field_name in field_names
            )
        )

    return allow_fields


@pytest.mark.parametrize(
    "query",
    [
        pytest.param(
            """
                { ...ServiceFields }
                fragment ServiceFields on Query {
                    available: services { edges { node { id } } }
                }
            """,
            id="services-with-alias-and-fragment",
        ),
        pytest.param("{ __schema { queryType { name } } }", id="introspection"),
        pytest.param("{ _service { sdl } }", id="federation-sdl"),
        pytest.param(
            "{ __typename myProfile @skip(if: true) { id } }",
            id="skipped-profile",
        ),
    ],
)
def test_non_profile_queries_bypass_contact_batching(
    superuser_gql_client, monkeypatch, query
):
    """Test that queries without profile results bypass contact batching."""
    prefetch = Mock()
    monkeypatch.setattr(
        PrimaryContactBatchingExecutionContext,
        "_prefetch_primary_contacts",
        prefetch,
    )

    executed = superuser_gql_client.execute(query)

    assert "errors" not in executed
    assert executed["data"]
    prefetch.assert_not_called()


@pytest.mark.parametrize("profile_count", [1, 3], ids=["one-profile", "three-profiles"])
@pytest.mark.parametrize("connection_count", [1, 3], ids=["one-root", "three-roots"])
def test_primary_contact_prefetch_queries_each_contact_table_once(
    superuser_gql_client,
    service,
    make_primary_contacts,
    allow_service_fields,
    profile_count,
    connection_count,
):
    """Test that aliased profile lists use one query per contact table."""
    profiles = ProfileFactory.create_batch(profile_count)
    for profile in profiles:
        ServiceConnectionFactory(profile=profile, service=service)
        make_primary_contacts(profile)
    allow_service_fields("email", "phone", "address")

    selection = """
        profiles {
            edges {
                node {
                    primaryEmail { email }
                    primaryPhone { phone }
                    primaryAddress { address }
                }
            }
        }
    """
    query = (
        "{ "
        + " ".join(f"list{index}: {selection}" for index in range(connection_count))
        + " }"
    )

    with CaptureQueriesContext(connection) as captured_queries:
        executed = superuser_gql_client.execute(query, service=service)

    assert "errors" not in executed
    assert len(executed["data"]) == connection_count
    for result in executed["data"].values():
        edges = result["edges"]
        assert len(edges) == profile_count
        for edge in edges:
            node = edge["node"]
            assert node["primaryEmail"] is not None
            assert node["primaryPhone"] is not None
            assert node["primaryAddress"] is not None

    assert _count_contact_queries(captured_queries) == _expected_contact_query_counts(
        address_count=1, email_count=1, phone_count=1
    )


@pytest.mark.parametrize("profile_count", [1, 3], ids=["one-profile", "three-profiles"])
def test_primary_contact_fallback_queries_each_profile(
    superuser_gql_client,
    service,
    monkeypatch,
    make_primary_contacts,
    allow_service_fields,
    profile_count,
):
    """Test that disabled batching queries each profile and contact type separately."""
    profiles = ProfileFactory.create_batch(profile_count)
    for profile in profiles:
        ServiceConnectionFactory(profile=profile, service=service)
        make_primary_contacts(profile)
    allow_service_fields("email", "phone", "address")

    monkeypatch.setattr(
        PrimaryContactBatchingExecutionContext,
        "_prefetch_primary_contacts",
        staticmethod(lambda contact_batches: None),
    )
    query = """
        {
            profiles {
                edges {
                    node {
                        primaryEmail { email }
                        primaryPhone { phone }
                        primaryAddress { address }
                    }
                }
            }
        }
    """

    with CaptureQueriesContext(connection) as captured_queries:
        executed = superuser_gql_client.execute(query, service=service)

    assert "errors" not in executed
    assert len(executed["data"]) == 1
    edges = executed["data"]["profiles"]["edges"]
    assert len(edges) == profile_count
    for edge in edges:
        node = edge["node"]
        assert node["primaryEmail"] is not None
        assert node["primaryPhone"] is not None
        assert node["primaryAddress"] is not None

    assert _count_contact_queries(captured_queries) == _expected_contact_query_counts(
        address_count=profile_count,
        email_count=profile_count,
        phone_count=profile_count,
    )


def test_primary_contacts_batch_with_missing_and_non_primary_contacts(
    superuser_gql_client, service, make_primary_contacts, allow_service_fields
):
    """Test that missing primary contacts stay null without per-profile queries."""
    profiles = sorted(ProfileFactory.create_batch(3), key=lambda profile: profile.pk)
    populated_profile, empty_profile, non_primary_profile = profiles
    for profile in profiles:
        ServiceConnectionFactory(profile=profile, service=service)
    contacts = make_primary_contacts(populated_profile)
    EmailFactory(profile=non_primary_profile, primary=False)
    PhoneFactory(profile=non_primary_profile, primary=False)
    AddressFactory(profile=non_primary_profile, primary=False)
    allow_service_fields("email", "phone", "address")

    query = """
        {
            first: profiles { edges { node { ...PrimaryContacts } } }
            second: profiles { edges { node { ...PrimaryContacts } } }
        }

        fragment PrimaryContacts on ProfileNode {
            primaryEmail { email }
            primaryPhone { phone }
            primaryAddress { address }
        }
    """

    with CaptureQueriesContext(connection) as captured_queries:
        executed = superuser_gql_client.execute(query, service=service)

    assert "errors" not in executed
    expected_nodes = [
        {
            "primaryEmail": {"email": contacts["email"].email},
            "primaryPhone": {"phone": contacts["phone"].phone},
            "primaryAddress": {"address": contacts["address"].address},
        },
        {"primaryEmail": None, "primaryPhone": None, "primaryAddress": None},
        {"primaryEmail": None, "primaryPhone": None, "primaryAddress": None},
    ]
    assert set(executed["data"]) == {"first", "second"}
    for result in executed["data"].values():
        assert [edge["node"] for edge in result["edges"]] == expected_nodes
    assert _count_contact_queries(captured_queries) == _expected_contact_query_counts(
        address_count=1, email_count=1, phone_count=1
    )


def test_primary_contacts_batch_across_aliased_profile_roots(
    superuser_gql_client, service, make_primary_contacts, allow_service_fields
):
    """Test that aliased profile lookups share one query per contact table."""
    profiles = ProfileFactory.create_batch(2)
    contacts = []
    for profile in profiles:
        ServiceConnectionFactory(profile=profile, service=service)
        contacts.append(make_primary_contacts(profile))

    allow_service_fields("email", "phone", "address")

    profile_ids = [
        relay.Node.to_global_id(ProfileNode._meta.name, profile.id)
        for profile in profiles
    ]
    query = """
        query($firstId: ID!, $secondId: ID!) {
            first: profile(id: $firstId) {
                email: primaryEmail { email }
                phone: primaryPhone { phone }
                address: primaryAddress { address }
            }
            second: profile(id: $secondId) {
                email: primaryEmail { email }
                phone: primaryPhone { phone }
                address: primaryAddress { address }
            }
        }
    """

    with CaptureQueriesContext(connection) as captured_queries:
        executed = superuser_gql_client.execute(
            query,
            variables={"firstId": profile_ids[0], "secondId": profile_ids[1]},
            service=service,
        )

    assert "errors" not in executed
    for alias, contact in zip(("first", "second"), contacts, strict=True):
        assert executed["data"][alias] == {
            "email": {"email": contact["email"].email},
            "phone": {"phone": contact["phone"].phone},
            "address": {"address": contact["address"].address},
        }

    assert _count_contact_queries(captured_queries) == _expected_contact_query_counts(
        address_count=1, email_count=1, phone_count=1
    )


def test_primary_contacts_batch_shared_profile_with_different_selections(
    superuser_gql_client, service, make_primary_contacts, allow_service_fields
):
    """Test that aliases reuse contact queries without fetching unrequested types."""
    profile = ProfileFactory()
    ServiceConnectionFactory(profile=profile, service=service)
    contacts = make_primary_contacts(profile, fields=("email", "phone"))
    allow_service_fields("email", "phone")
    profile_id = relay.Node.to_global_id(ProfileNode._meta.name, profile.id)
    query = """
        query($id: ID!) {
            first: profile(id: $id) { primaryEmail { email } }
            second: profile(id: $id) { primaryPhone { phone } }
            third: profile(id: $id) { primaryEmail { email } }
        }
    """

    with CaptureQueriesContext(connection) as captured_queries:
        executed = superuser_gql_client.execute(
            query, variables={"id": profile_id}, service=service
        )

    assert "errors" not in executed
    assert executed["data"] == {
        "first": {"primaryEmail": {"email": contacts["email"].email}},
        "second": {"primaryPhone": {"phone": contacts["phone"].phone}},
        "third": {"primaryEmail": {"email": contacts["email"].email}},
    }
    assert _count_contact_queries(captured_queries) == _expected_contact_query_counts(
        address_count=0, email_count=1, phone_count=1
    )


def test_primary_contacts_batch_across_paginated_connections_and_other_roots(
    superuser_gql_client, service, make_primary_contacts, allow_service_fields
):
    """Test that paginated lists and other profile roots share contact queries."""
    profiles = sorted(ProfileFactory.create_batch(3), key=lambda profile: profile.pk)
    expected_contacts = []
    for profile in profiles:
        ServiceConnectionFactory(profile=profile, service=service)
        contacts = make_primary_contacts(profile)
        expected_contacts.append(
            {
                "email": {"email": contacts["email"].email},
                "phone": {"phone": contacts["phone"].phone},
                "address": {"address": contacts["address"].address},
            }
        )

    allow_service_fields("email", "phone", "address")
    profile_id = relay.Node.to_global_id(ProfileNode._meta.name, profiles[1].id)
    query = """
        query($id: ID!, $representations: [_Any!]!) {
            rootType: __typename
            first: profiles(first: 1) {
                rows: edges {
                    profile: node { ...PrimaryContacts }
                }
            }
            last: profiles(last: 1) { ...ConnectionContacts }
            individual: profile(id: $id) { ...PrimaryContacts }
            _entities(representations: $representations) {
                ... on ProfileNode { ...PrimaryContacts }
            }
        }

        fragment ConnectionContacts on ProfileNodeConnection {
            edges {
                node { ...PrimaryContacts }
            }
        }

        fragment PrimaryContacts on ProfileNode {
            email: primaryEmail { email }
            phone: primaryPhone { phone }
            address: primaryAddress { address }
        }
    """

    with CaptureQueriesContext(connection) as captured_queries:
        executed = superuser_gql_client.execute(
            query,
            variables={
                "id": profile_id,
                "representations": [
                    {
                        "id": profile_id,
                        "__typename": ProfileNode._meta.name,
                    }
                ],
            },
            service=service,
        )

    assert "errors" not in executed
    assert executed["data"] == {
        "rootType": "Query",
        "first": {"rows": [{"profile": expected_contacts[0]}]},
        "last": {"edges": [{"node": expected_contacts[2]}]},
        "individual": expected_contacts[1],
        "_entities": [expected_contacts[1]],
    }
    assert _count_contact_queries(captured_queries) == _expected_contact_query_counts(
        address_count=1, email_count=1, phone_count=1
    )


def test_primary_contacts_batch_across_other_profile_roots(
    superuser_gql_client, service, make_primary_contacts, allow_service_fields
):
    """Test that myProfile and token-based profile roots share contact queries."""
    my_profile = ProfileFactory(user=superuser_gql_client.user)
    ServiceConnectionFactory(profile=my_profile, service=service)
    claimable_profile = ProfileFactory(user=None)
    claim_token = ClaimTokenFactory(profile=claimable_profile)
    access_profile = ProfileFactory()
    access_token = TemporaryReadAccessTokenFactory(profile=access_profile)

    profiles = (my_profile, claimable_profile, access_profile)
    contacts = [make_primary_contacts(profile) for profile in profiles]

    allow_service_fields("email", "phone", "address")
    query = """
        query($claimToken: UUID!, $accessToken: UUID!) {
            mine: myProfile {
                primaryEmail { email }
                primaryPhone { phone }
                primaryAddress { address }
            }
            claimable: claimableProfile(token: $claimToken) {
                primaryEmail { email }
                primaryPhone { phone }
                primaryAddress { address }
            }
            temporary: profileWithAccessToken(token: $accessToken) {
                primaryEmail { email }
                primaryPhone { phone }
                primaryAddress { address }
            }
        }
    """

    with CaptureQueriesContext(connection) as captured_queries:
        executed = superuser_gql_client.execute(
            query,
            variables={
                "claimToken": str(claim_token.token),
                "accessToken": str(access_token.token),
            },
            service=service,
        )

    assert "errors" not in executed
    for alias, contact in zip(
        ("mine", "claimable", "temporary"), contacts, strict=True
    ):
        assert executed["data"][alias] == {
            "primaryEmail": {"email": contact["email"].email},
            "primaryPhone": {"phone": contact["phone"].phone},
            "primaryAddress": {"address": contact["address"].address},
        }

    assert _count_contact_queries(captured_queries) == _expected_contact_query_counts(
        address_count=1, email_count=1, phone_count=1
    )


def test_profile_entities_batch_primary_contacts(
    superuser_gql_client, service, make_primary_contacts, allow_service_fields
):
    """Test that federated profiles use one query per contact table."""
    profiles = ProfileFactory.create_batch(2)
    contacts = []
    for profile in profiles:
        ServiceConnectionFactory(profile=profile, service=service)
        contacts.append(make_primary_contacts(profile))

    allow_service_fields("email", "phone", "address")
    representations = [
        {
            "id": to_global_id(ProfileNode._meta.name, profile.id),
            "__typename": ProfileNode._meta.name,
        }
        for profile in profiles
    ]
    query = """
        query ($_representations: [_Any!]!) {
            _entities(representations: $_representations) {
                ... on ProfileNode {
                    primaryEmail { email }
                    primaryPhone { phone }
                    primaryAddress { address }
                }
            }
        }
    """

    with CaptureQueriesContext(connection) as captured_queries:
        executed = superuser_gql_client.execute(
            query,
            variables={"_representations": representations},
            service=service,
        )

    assert "errors" not in executed
    entities = executed["data"]["_entities"]
    assert len(entities) == len(profiles)
    for entity, contact in zip(entities, contacts, strict=True):
        assert entity == {
            "primaryEmail": {"email": contact["email"].email},
            "primaryPhone": {"phone": contact["phone"].phone},
            "primaryAddress": {"address": contact["address"].address},
        }

    assert _count_contact_queries(captured_queries) == _expected_contact_query_counts(
        address_count=1, email_count=1, phone_count=1
    )


def test_profiles_query_does_not_prefetch_excluded_contacts(
    superuser_gql_client, service, allow_service_fields, monkeypatch
):
    """Test that contacts excluded by GraphQL directives are not fetched."""
    profiles = ProfileFactory.create_batch(2)
    for profile in profiles:
        ServiceConnectionFactory(profile=profile, service=service)
    allow_service_fields("email", "phone", "address")
    resolve_root_fields = Mock()
    monkeypatch.setattr(
        PrimaryContactBatchingExecutionContext,
        "_resolve_root_fields",
        resolve_root_fields,
    )

    query = """
        query($shouldSkip: Boolean!, $shouldInclude: Boolean!) {
            profiles {
                edges {
                    node {
                        primaryEmail @skip(if: $shouldSkip) { email }
                        primaryPhone @include(if: $shouldInclude) { phone }
                        primaryAddress @include(if: false) { address }
                        ... on ProfileNode @skip(if: $shouldSkip) {
                            primaryAddress { address }
                        }
                        ...ContactFields @skip(if: $shouldSkip)
                    }
                }
            }
        }

        fragment ContactFields on ProfileNode {
            primaryPhone { phone }
        }
    """

    with CaptureQueriesContext(connection) as captured_queries:
        executed = superuser_gql_client.execute(
            query,
            variables={"shouldSkip": True, "shouldInclude": False},
            service=service,
        )

    assert "errors" not in executed
    assert _count_contact_queries(captured_queries) == _expected_contact_query_counts(
        address_count=0, email_count=0, phone_count=0
    )
    resolve_root_fields.assert_not_called()


def test_profiles_query_does_not_prefetch_unrequested_contacts(
    superuser_gql_client, service, allow_service_fields, monkeypatch
):
    """Test that unrequested contact fields cause no contact-table queries."""
    profiles = ProfileFactory.create_batch(3)
    for profile in profiles:
        ServiceConnectionFactory(profile=profile, service=service)
    allow_service_fields("name")
    resolve_root_fields = Mock()
    monkeypatch.setattr(
        PrimaryContactBatchingExecutionContext,
        "_resolve_root_fields",
        resolve_root_fields,
    )

    query = """
        {
            profiles {
                edges {
                    node { firstName }
                }
            }
        }
    """

    with CaptureQueriesContext(connection) as captured_queries:
        executed = superuser_gql_client.execute(query, service=service)

    assert "errors" not in executed
    assert len(executed["data"]["profiles"]["edges"]) == len(profiles)
    assert _count_contact_queries(captured_queries) == _expected_contact_query_counts(
        address_count=0, email_count=0, phone_count=0
    )
    resolve_root_fields.assert_not_called()


@pytest.mark.parametrize(
    "field_name, query",
    [
        pytest.param(
            "profile",
            '{ result: profile(id: "unused") { id primaryEmail { email } } }',
            id="single-profile",
        ),
        pytest.param(
            "profiles",
            "{ result: profiles { edges { node { id primaryEmail { email } } } } }",
            id="profile-list",
        ),
    ],
)
def test_undefined_nullable_root_results_match_base_execution(
    superuser_gql_client, monkeypatch, field_name, query
):
    """Test that Undefined nullable roots return null and the same base error."""
    query_type = schema.graphql_schema.query_type
    assert query_type is not None
    field = query_type.fields[field_name]

    base_resolver = Mock(return_value=Undefined)
    monkeypatch.setattr(field, "resolve", base_resolver)
    expected = superuser_gql_client.execute(
        query, execution_context_class=ExecutionContext
    )
    base_resolver.assert_called_once()

    batching_resolver = Mock(return_value=Undefined)
    monkeypatch.setattr(field, "resolve", batching_resolver)
    executed = superuser_gql_client.execute(query)
    batching_resolver.assert_called_once()

    assert executed == expected
    assert executed["data"] == {"result": None}
    assert executed["errors"][0]["path"] == ["result"]


@pytest.mark.parametrize(
    "field_name, query",
    [
        pytest.param(
            "profile",
            '{ result: profile(id: "unused") { id primaryEmail { email } } }',
            id="single-profile",
        ),
        pytest.param(
            "profiles",
            "{ result: profiles { edges { node { id primaryEmail { email } } } } }",
            id="profile-list",
        ),
    ],
)
def test_undefined_non_null_root_results_match_base_execution(
    superuser_gql_client, monkeypatch, field_name, query
):
    """Test that Undefined non-null roots null the response like the base executor."""
    query_type = schema.graphql_schema.query_type
    assert query_type is not None
    field = query_type.fields[field_name]
    monkeypatch.setattr(field, "type", GraphQLNonNull(field.type))

    base_resolver = Mock(return_value=Undefined)
    monkeypatch.setattr(field, "resolve", base_resolver)
    expected = superuser_gql_client.execute(
        query, execution_context_class=ExecutionContext
    )
    base_resolver.assert_called_once()

    batching_resolver = Mock(return_value=Undefined)
    monkeypatch.setattr(field, "resolve", batching_resolver)
    executed = superuser_gql_client.execute(query)
    batching_resolver.assert_called_once()

    assert executed == expected
    assert executed["data"] is None
    assert executed["errors"][0]["path"] == ["result"]
