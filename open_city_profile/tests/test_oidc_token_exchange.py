from urllib.parse import parse_qs

import pytest
from requests import HTTPError

from open_city_profile.exceptions import TokenExchangeError
from open_city_profile.oidc import KeycloakTokenExchange

AUTHORIZATION_CODE = "keycloak_auth_code"
KEYCLOAK_API_TOKEN_MARKER = "keycloak_api_token"

KEYCLOAK_BASE_URL = "https://keycloak.example.com/auth"
KEYCLOAK_REALM = "example-realm"
KEYCLOAK_OPENID_CONFIGURATION_ENDPOINT = (
    f"{KEYCLOAK_BASE_URL}/realms/{KEYCLOAK_REALM}/.well-known/openid-configuration"
)
KEYCLOAK_TOKEN_ENDPOINT = (
    f"{KEYCLOAK_BASE_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"
)


def get_keycloak_token_response(token_request, context):
    grant_type = parse_qs(token_request.body).get("grant_type")[0]
    if grant_type == "authorization_code":
        return {"access_token": "keycloak_access_token"}
    elif grant_type == "urn:ietf:params:oauth:grant-type:uma-ticket":
        return {"access_token": "keycloak_api_token"}


def test_authorization_code_exchange_successful(settings, user, requests_mock):
    settings.KEYCLOAK_BASE_URL = KEYCLOAK_BASE_URL
    settings.KEYCLOAK_REALM = KEYCLOAK_REALM
    settings.KEYCLOAK_GDPR_CLIENT_ID = "test-gdpr-client"
    settings.KEYCLOAK_GDPR_CLIENT_SECRET = "testsecret"
    kte = KeycloakTokenExchange()
    expected_access_token_response = "keycloak_access_token"
    expected_api_token_response = "keycloak_api_token"
    requests_mock.get(
        KEYCLOAK_OPENID_CONFIGURATION_ENDPOINT,
        json={"token_endpoint": KEYCLOAK_TOKEN_ENDPOINT},
    )
    requests_mock.post(
        KEYCLOAK_TOKEN_ENDPOINT,
        json=get_keycloak_token_response,
    )

    access_token_response = kte.fetch_access_token("auhorization_code")
    api_token_response = kte.fetch_api_token("audience", "auth_code")

    assert access_token_response == expected_access_token_response
    assert api_token_response == expected_api_token_response


def test_authorization_code_exchange_failed(settings, requests_mock):
    settings.KEYCLOAK_BASE_URL = KEYCLOAK_BASE_URL
    settings.KEYCLOAK_REALM = KEYCLOAK_REALM
    settings.KEYCLOAK_GDPR_CLIENT_ID = "test-gdpr-client"
    settings.KEYCLOAK_GDPR_CLIENT_SECRET = "testsecret"
    kte = KeycloakTokenExchange()
    requests_mock.get(
        KEYCLOAK_OPENID_CONFIGURATION_ENDPOINT,
        json={"token_endpoint": KEYCLOAK_TOKEN_ENDPOINT},
    )
    requests_mock.post(KEYCLOAK_TOKEN_ENDPOINT, json={}, status_code=403)

    with pytest.raises(TokenExchangeError) as e:
        kte.fetch_access_token("authorization_code")

    assert str(e.value) == "Failed to obtain an access token."

    with pytest.raises(HTTPError) as e:
        kte.fetch_api_token("audience", "auth_code")

    assert (
        str(e.value)
        == "403 Client Error: None for url: https://keycloak.example.com/auth/realms/example-realm/protocol/openid-connect/token"
    )
