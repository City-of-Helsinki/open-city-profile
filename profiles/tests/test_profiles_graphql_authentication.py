import pytest
from guardian.shortcuts import assign_perm

from open_city_profile.tests.graphql_test_helpers import (
    BearerTokenAuth,
    do_graphql_call,
    do_graphql_call_as_user,
)


def test_presenting_a_valid_access_token_grants_access(profile, live_server):
    data, errors = do_graphql_call_as_user(live_server, profile.user)

    assert not errors
    assert data["myProfile"]["id"]


@pytest.mark.parametrize("loa,returns_errors", [("substantial", False), ("low", True)])
def test_jwt_claims_are_usable_in_field_resolvers(
    loa, returns_errors, profile_with_verified_personal_information, live_server,
):
    user_uuid = profile_with_verified_personal_information.user.uuid
    claims = {"sub": str(user_uuid), "loa": loa}
    query = """
        query {
            myProfile {
                verifiedPersonalInformation {
                    firstName
                }
            }
    }
    """
    data, errors = do_graphql_call(
        live_server, BearerTokenAuth(extra_claims=claims), query=query,
    )

    assert isinstance(errors, list) == returns_errors


def test_determine_service_from_the_azp_claim(
    service_client_id, profile, service_connection_factory, group, live_server
):
    service = service_client_id.service
    service_connection_factory(profile=profile, service=service)
    user = profile.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service)

    claims = {"sub": str(user.uuid), "azp": service_client_id.client_id}
    query = """
        query {
            profiles {
                edges {
                    node {
                        firstName
                    }
                }
            }
        }
    """

    data, errors = do_graphql_call(
        live_server, BearerTokenAuth(extra_claims=claims), query=query,
    )
    expected_data = {
        "profiles": {"edges": [{"node": {"firstName": profile.first_name}}]}
    }

    assert data == expected_data
    assert errors is None
