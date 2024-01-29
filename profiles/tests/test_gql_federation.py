import pytest
from graphql_relay import to_global_id
from guardian.shortcuts import assign_perm

from open_city_profile.tests.asserts import assert_match_error_code
from profiles.schema import AddressNode, ProfileNode
from profiles.tests.factories import AddressFactory, ProfileFactory
from services.tests.factories import ServiceConnectionFactory

GRAPHQL_SDL_QUERY = """
    query {
        _service {
            sdl
        }
    }
"""


ENTITY_QUERY = """
    query ($_representations: [_Any!]!) {
        _entities(representations: $_representations) {
            ... on ProfileNode {
                id
                firstName
            }
            ... on AddressNode {
                id
                address
                postalCode
            }
        }
    }
"""


@pytest.mark.parametrize("schema_type", ["ProfileNode", "AddressNode"])
def test_node_exposes_key_for_federation_gateway(schema_type, anon_user_gql_client):
    executed = anon_user_gql_client.execute(GRAPHQL_SDL_QUERY)
    type_definition = f'type {schema_type} implements Node @key(fields: "id")'
    sdl = executed["data"]["_service"]["sdl"]
    assert type_definition in sdl


def test_profile_connection_schema_matches_federated_schema(anon_user_gql_client):
    executed = anon_user_gql_client.execute(GRAPHQL_SDL_QUERY)

    assert (
        "type ProfileNodeConnection {\n"
        '  """Pagination data for this connection."""\n'
        "  pageInfo: PageInfo!\n"
        "\n"
        '  """Contains the nodes in this connection."""\n'
        "  edges: [ProfileNodeEdge]!\n"
        "  count: Int!\n"
        "  totalCount: Int!\n"
        "}\n" in executed["data"]["_service"]["sdl"]
    )


def test_address_connection_schema_matches_federated_schema(anon_user_gql_client):
    executed = anon_user_gql_client.execute(GRAPHQL_SDL_QUERY)

    assert (
        "type AddressNodeConnection {\n"
        '  """Pagination data for this connection."""\n'
        "  pageInfo: PageInfo!\n"
        "\n"
        '  """Contains the nodes in this connection."""\n'
        "  edges: [AddressNodeEdge]!\n"
        "}\n" in executed["data"]["_service"]["sdl"]
    )


def _create_profile_and_variables(with_serviceconnection, service, user=None):
    profile = ProfileFactory(user=user)
    if with_serviceconnection:
        ServiceConnectionFactory(profile=profile, service=service)

    profile._global_id = to_global_id(ProfileNode._meta.name, profile.id)

    variables = {
        "_representations": [
            {"id": profile._global_id, "__typename": ProfileNode._meta.name}
        ]
    }

    return profile, variables


def _create_address_and_variables(with_serviceconnection, service, user=None):
    profile = ProfileFactory(user=user)
    address = AddressFactory(profile=profile)
    if with_serviceconnection:
        ServiceConnectionFactory(profile=profile, service=service)

    address._global_id = to_global_id(AddressNode._meta.name, address.id)

    variables = {
        "_representations": [
            {"id": address._global_id, "__typename": AddressNode._meta.name}
        ]
    }

    return address, variables


@pytest.mark.parametrize(
    "with_service",
    (pytest.param(True, id="service"), pytest.param(False, id="no_service")),
)
@pytest.mark.parametrize(
    "with_serviceconnection",
    (
        pytest.param(True, id="serviceconnection"),
        pytest.param(False, id="no_serviceconnection"),
    ),
)
def test_anonymous_user_can_not_resolve_profile_entity(
    anon_user_gql_client, service, with_service, with_serviceconnection
):
    profile, variables = _create_profile_and_variables(with_serviceconnection, service)
    executed = anon_user_gql_client.execute(
        ENTITY_QUERY, variables=variables, service=service if with_service else None
    )

    assert_match_error_code(executed, "PERMISSION_DENIED_ERROR")
    assert executed["data"] is None


@pytest.mark.parametrize(
    "with_service",
    (pytest.param(True, id="service"), pytest.param(False, id="no_service")),
)
@pytest.mark.parametrize(
    "with_serviceconnection",
    (
        pytest.param(True, id="serviceconnection"),
        pytest.param(False, id="no_serviceconnection"),
    ),
)
def test_owner_can_resolve_profile_entity(
    user_gql_client, service, with_service, with_serviceconnection
):
    profile, variables = _create_profile_and_variables(
        with_serviceconnection, service, user=user_gql_client.user
    )
    expected_data = {
        "_entities": [{"id": profile._global_id, "firstName": profile.first_name}]
    }
    executed = user_gql_client.execute(
        ENTITY_QUERY, variables=variables, service=service if with_service else None
    )

    if with_service and with_serviceconnection:
        assert executed["data"] == expected_data
    elif not with_service:
        assert_match_error_code(executed, "SERVICE_NOT_IDENTIFIED_ERROR")
        assert executed["data"] is None
    else:
        assert_match_error_code(executed, "PERMISSION_DENIED_ERROR")
        assert executed["data"] is None


@pytest.mark.parametrize(
    "with_service",
    (pytest.param(True, id="service"), pytest.param(False, id="no_service")),
)
@pytest.mark.parametrize(
    "with_serviceconnection",
    (
        pytest.param(True, id="serviceconnection"),
        pytest.param(False, id="no_serviceconnection"),
    ),
)
def test_non_owner_user_can_not_resolve_profile_entity(
    user_gql_client, service, with_service, with_serviceconnection
):
    profile, variables = _create_profile_and_variables(with_serviceconnection, service)
    executed = user_gql_client.execute(
        ENTITY_QUERY, variables=variables, service=service if with_service else None
    )

    if not with_service:
        assert_match_error_code(executed, "SERVICE_NOT_IDENTIFIED_ERROR")
        assert executed["data"] is None
    else:
        assert_match_error_code(executed, "PERMISSION_DENIED_ERROR")
        assert executed["data"] is None


@pytest.mark.parametrize(
    "with_serviceconnection",
    (
        pytest.param(True, id="serviceconnection"),
        pytest.param(False, id="no_serviceconnection"),
    ),
)
def test_staff_user_can_resolve_profile_entity(
    user_gql_client, group, service, with_serviceconnection
):
    profile, variables = _create_profile_and_variables(with_serviceconnection, service)
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service)

    expected_data = {
        "_entities": [{"id": profile._global_id, "firstName": profile.first_name}]
    }
    executed = user_gql_client.execute(
        ENTITY_QUERY, variables=variables, service=service
    )

    if with_serviceconnection:
        assert executed["data"] == expected_data
    else:
        assert_match_error_code(executed, "PERMISSION_DENIED_ERROR")
        assert executed["data"] is None


@pytest.mark.parametrize(
    "with_service",
    (pytest.param(True, id="service"), pytest.param(False, id="no_service")),
)
@pytest.mark.parametrize(
    "with_serviceconnection",
    (
        pytest.param(True, id="serviceconnection"),
        pytest.param(False, id="no_serviceconnection"),
    ),
)
def test_anonymous_user_can_not_resolve_address_entity(
    anon_user_gql_client, service, with_service, with_serviceconnection
):
    address, variables = _create_address_and_variables(with_serviceconnection, service)
    executed = anon_user_gql_client.execute(
        ENTITY_QUERY, variables=variables, service=service if with_service else None
    )

    assert_match_error_code(executed, "PERMISSION_DENIED_ERROR")
    assert executed["data"] is None


@pytest.mark.parametrize(
    "with_service",
    (pytest.param(True, id="service"), pytest.param(False, id="no_service")),
)
@pytest.mark.parametrize(
    "with_serviceconnection",
    (
        pytest.param(True, id="serviceconnection"),
        pytest.param(False, id="no_serviceconnection"),
    ),
)
def test_owner_can_resolve_address_entity(
    user_gql_client, service, with_service, with_serviceconnection
):
    address, variables = _create_address_and_variables(
        with_serviceconnection, service, user=user_gql_client.user
    )
    expected_data = {
        "_entities": [
            {
                "id": address._global_id,
                "address": address.address,
                "postalCode": address.postal_code,
            }
        ]
    }

    executed = user_gql_client.execute(
        ENTITY_QUERY, variables=variables, service=service if with_service else None
    )

    if with_service and with_serviceconnection:
        assert executed["data"] == expected_data
    elif not with_service:
        assert_match_error_code(executed, "SERVICE_NOT_IDENTIFIED_ERROR")
        assert executed["data"] is None
    else:
        assert_match_error_code(executed, "PERMISSION_DENIED_ERROR")
        assert executed["data"] is None


@pytest.mark.parametrize(
    "with_service",
    (pytest.param(True, id="service"), pytest.param(False, id="no_service")),
)
@pytest.mark.parametrize(
    "with_serviceconnection",
    (
        pytest.param(True, id="serviceconnection"),
        pytest.param(False, id="no_serviceconnection"),
    ),
)
def test_non_owner_user_can_not_resolve_address_entity(
    user_gql_client, service, with_service, with_serviceconnection
):
    address, variables = _create_address_and_variables(with_serviceconnection, service)
    executed = user_gql_client.execute(
        ENTITY_QUERY, variables=variables, service=service if with_service else None
    )

    if not with_service:
        assert_match_error_code(executed, "SERVICE_NOT_IDENTIFIED_ERROR")
        assert executed["data"] is None
    else:
        assert_match_error_code(executed, "PERMISSION_DENIED_ERROR")
        assert executed["data"] is None


@pytest.mark.parametrize(
    "with_serviceconnection",
    (
        pytest.param(True, id="serviceconnection"),
        pytest.param(False, id="no_serviceconnection"),
    ),
)
def test_staff_user_can_resolve_address_entity(
    user_gql_client, group, service, with_serviceconnection
):
    address, variables = _create_address_and_variables(with_serviceconnection, service)
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service)

    expected_data = {
        "_entities": [
            {
                "id": address._global_id,
                "address": address.address,
                "postalCode": address.postal_code,
            }
        ]
    }
    executed = user_gql_client.execute(
        ENTITY_QUERY, variables=variables, service=service
    )

    if with_serviceconnection:
        assert executed["data"] == expected_data
    else:
        assert_match_error_code(executed, "PERMISSION_DENIED_ERROR")
        assert executed["data"] is None
