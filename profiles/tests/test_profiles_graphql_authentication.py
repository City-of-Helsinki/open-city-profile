import pytest

from open_city_profile.tests.authentication_tests_base import (
    BearerTokenAuth,
    do_graphql_authentication_test,
)


def test_presenting_a_valid_access_token_grants_access(
    profile, live_server, mock_responses
):
    claims = {"sub": str(profile.user.uuid)}
    data, errors = do_graphql_authentication_test(
        live_server, mock_responses, BearerTokenAuth(extra_claims=claims)
    )

    assert not errors
    assert data["myProfile"]["id"]


@pytest.mark.parametrize("loa,returns_errors", [("substantial", False), ("low", True)])
def test_jwt_claims_are_usable_in_field_resolvers(
    loa,
    returns_errors,
    profile_with_verified_personal_information,
    live_server,
    mock_responses,
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
    data, errors = do_graphql_authentication_test(
        live_server, mock_responses, BearerTokenAuth(extra_claims=claims), query=query,
    )

    assert isinstance(errors, list) == returns_errors
