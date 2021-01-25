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
