import uuid

import requests
from django.conf import settings
from jose import jwt

from .keys import rsa_key

AUDIENCE = getattr(settings, "OIDC_API_TOKEN_AUTH")["AUDIENCE"]
ISSUER = getattr(settings, "OIDC_API_TOKEN_AUTH")["ISSUER"]

CONFIG_URL = f"{ISSUER}/.well-known/openid-configuration"
JWKS_URL = f"{ISSUER}/jwks"

CONFIGURATION = {
    "issuer": ISSUER,
    "jwks_uri": JWKS_URL,
}

KEYS = {"keys": [rsa_key.public_key_jwk]}


class BearerTokenAuth(requests.auth.AuthBase):
    def __call__(self, request):
        user_uuid = uuid.uuid4()
        jwt_data = {
            "iss": ISSUER,
            "aud": AUDIENCE,
            "sub": str(user_uuid),
            "exp": 1,
        }
        encoded_jwt = jwt.encode(
            jwt_data, key=rsa_key.private_key_pem, algorithm=rsa_key.jose_algorithm
        )

        request.headers["Authorization"] = f"Bearer {encoded_jwt}"
        return request


def do_graphql_authentication_test(live_server, mock_responses, request_auth=None):
    url = live_server.url + "/graphql/"

    mock_responses.add_passthru(url)
    mock_responses.add(method="GET", url=CONFIG_URL, json=CONFIGURATION)
    mock_responses.add(method="GET", url=JWKS_URL, json=KEYS)

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

    response = requests.post(url, json=payload, auth=request_auth)

    assert response.status_code == 200

    body = response.json()
    return body["data"], body["errors"]


def test_not_presenting_an_access_token_with_operation_needing_authentication_returns_permission_denied_error(
    live_server, mock_responses,
):
    data, errors = do_graphql_authentication_test(live_server, mock_responses)

    # myProfile query produces an error and no data
    assert len(errors) == 1
    error = errors[0]
    assert error["path"] == ["myProfile"]
    assert error["extensions"]["code"] == "PERMISSION_DENIED_ERROR"
    assert data["myProfile"] is None

    # _service query produces data and no error
    assert type(data["_service"]["sdl"]) is str


def test_presenting_an_expired_access_token_with_any_operation_returns_general_error(
    live_server, mock_responses,
):
    data, errors = do_graphql_authentication_test(
        live_server, mock_responses, BearerTokenAuth()
    )

    assert len(errors) == 2

    for path in ["myProfile", "_service"]:
        assert data[path] is None

        error = next(err for err in errors if err["path"] == [path])
        assert error["extensions"]["code"] == "GENERAL_ERROR"
