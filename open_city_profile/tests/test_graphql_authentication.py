from helusers.models import OIDCBackChannelLogoutEvent

from .graphql_test_helpers import BearerTokenAuth, do_graphql_call, generate_jwt_token


def test_not_presenting_an_access_token_with_operation_needing_authentication_returns_permission_denied_error(
    live_server,
):
    data, errors = do_graphql_call(live_server)

    # myProfile query produces an error and no data
    assert len(errors) == 1
    error = errors[0]
    assert error["path"] == ["myProfile"]
    assert error["extensions"]["code"] == "PERMISSION_DENIED_ERROR"
    assert data["myProfile"] is None

    # _service query produces data and no error
    assert type(data["_service"]["sdl"]) is str


def test_presenting_an_expired_access_token_with_any_operation_returns_jwt_authentication_error(
    unix_timestamp_now, live_server
):
    claims = {"exp": unix_timestamp_now - 1}
    data, errors = do_graphql_call(live_server, BearerTokenAuth(extra_claims=claims))

    assert len(errors) == 2

    for path in ["myProfile", "_service"]:
        assert data[path] is None

        error = next(err for err in errors if err["path"] == [path])
        assert error["extensions"]["code"] == "JWT_AUTHENTICATION_ERROR"


def test_presenting_a_logged_out_token_returns_jwt_authentication_error(live_server):
    jwt_data, encoded_jwt_token = generate_jwt_token()

    OIDCBackChannelLogoutEvent.objects.create(
        iss=jwt_data["iss"], sid=jwt_data["sid"], sub=jwt_data["sub"]
    )

    data, errors = do_graphql_call(
        live_server,
        extra_request_args={
            "headers": {"Authorization": f"Bearer {encoded_jwt_token}"},
        },
    )

    assert len(errors) == 2

    for path in ["myProfile", "_service"]:
        assert data[path] is None

        error = next(err for err in errors if err["path"] == [path])
        assert error["extensions"]["code"] == "JWT_AUTHENTICATION_ERROR"
