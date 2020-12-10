import requests


def test_not_presenting_an_access_token_with_operation_needing_authentication_returns_permission_denied_error(
    live_server,
):
    url = live_server.url + "/graphql/"

    query = """
        query {
            myProfile {
                id
            },
            _service {
                sdl
            }
        }"""

    payload = {
        "query": query,
    }

    response = requests.post(url, json=payload)

    assert response.status_code == 200

    body = response.json()
    data = body["data"]

    # myProfile query produces an error and no data
    assert len(body["errors"]) == 1
    error = body["errors"][0]
    assert error["path"] == ["myProfile"]
    assert error["extensions"]["code"] == "PERMISSION_DENIED_ERROR"
    assert data["myProfile"] is None

    # _service query produces data and no error
    assert type(data["_service"]["sdl"]) is str
