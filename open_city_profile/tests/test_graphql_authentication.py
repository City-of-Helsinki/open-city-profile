from .graphql_test_helpers import BearerTokenAuth, do_graphql_call


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


def test_presenting_an_expired_access_token_with_any_operation_returns_general_error(
    unix_timestamp_now, live_server,
):
    claims = {"exp": unix_timestamp_now - 1}
    data, errors = do_graphql_call(live_server, BearerTokenAuth(extra_claims=claims),)

    assert len(errors) == 2

    for path in ["myProfile", "_service"]:
        assert data[path] is None

        error = next(err for err in errors if err["path"] == [path])
        assert error["extensions"]["code"] == "GENERAL_ERROR"
