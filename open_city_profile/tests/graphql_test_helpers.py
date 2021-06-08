import uuid

import requests
import requests_mock
from django.conf import settings
from jose import jwt

from services.tests.factories import ServiceClientIdFactory

from .conftest import get_unix_timestamp_now
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
    def __init__(self, extra_claims=None):
        self._extra_claims = extra_claims or {}

    def __call__(self, request):
        jwt_data = {
            "iss": ISSUER,
            "iat": get_unix_timestamp_now() - 10,
            "aud": AUDIENCE,
            "sub": str(uuid.uuid4()),
            "exp": get_unix_timestamp_now() + 120,
        }
        jwt_data.update(self._extra_claims)
        encoded_jwt = jwt.encode(
            jwt_data, key=rsa_key.private_key_pem, algorithm=rsa_key.jose_algorithm
        )

        request.headers["Authorization"] = f"Bearer {encoded_jwt}"
        return request


_QUERY = """
query {
    myProfile {
        id
    },
    _service {
        sdl
    }
}"""


def do_graphql_call(
    live_server, request_auth=None, query=_QUERY, extra_request_args=None
):
    if extra_request_args is None:
        extra_request_args = {}

    url = live_server.url + "/graphql/"
    payload = {
        "query": query,
    }

    with requests_mock.Mocker(real_http=True) as mock:
        mock.get(CONFIG_URL, json=CONFIGURATION)
        mock.get(JWKS_URL, json=KEYS)

        request_args = {
            "auth": request_auth,
        }
        request_args.update(extra_request_args)

        response = requests.post(url, json=payload, **request_args)

    assert response.status_code == 200

    body = response.json()
    return body.get("data"), body.get("errors")


_not_provided = object()


def do_graphql_call_as_user(
    live_server, user, service=_not_provided, query=_QUERY, extra_request_args=None,
):
    if extra_request_args is None:
        extra_request_args = {}

    claims = {"sub": str(user.uuid)}

    service_client_id = None
    if service is _not_provided:
        service_client_id = ServiceClientIdFactory(
            service__service_type=None, service__implicit_connection=True,
        )
    elif service:
        service_client_id = service.client_ids.first()

    if service_client_id:
        claims["azp"] = service_client_id.client_id

    return do_graphql_call(
        live_server,
        BearerTokenAuth(extra_claims=claims),
        query=query,
        extra_request_args=extra_request_args,
    )
