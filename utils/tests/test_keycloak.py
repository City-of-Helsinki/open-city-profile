import urllib

import pytest

from utils.keycloak import KeycloakAdminClient

server_url = "https://keycloak.example"
realm_name = "test-realm"

client_id = "test-client-id"
client_secret = "test-client-secret"

token_endpoint_url = f"{server_url}/token-endpoint"
access_token = "test-access-token"

req_mock = None


@pytest.fixture(autouse=True)
def global_requests_mock(requests_mock):
    global req_mock
    req_mock = requests_mock
    yield requests_mock

    req_mock = None


@pytest.fixture
def keycloak_client():
    return KeycloakAdminClient(server_url, realm_name, client_id, client_secret)


def setup_well_known():
    req_mock.get(
        f"{server_url}/auth/realms/{realm_name}/.well-known/openid-configuration",
        json={"token_endpoint": token_endpoint_url},
    )


def setup_client_credentials():
    def body_matcher(request):
        body = urllib.parse.parse_qs(request.text, strict_parsing=True)
        return body == {
            "grant_type": ["client_credentials"],
            "client_id": [client_id],
            "client_secret": [client_secret],
        }

    req_mock.post(
        token_endpoint_url,
        request_headers={"Content-Type": "application/x-www-form-urlencoded"},
        additional_matcher=body_matcher,
        json={"access_token": access_token},
    )


def setup_user_response(user_id, user_data):
    req_mock.get(
        f"{server_url}/auth/admin/realms/{realm_name}/users/{user_id}",
        request_headers={"Authorization": f"Bearer {access_token}"},
        json=user_data,
    )


def test_fetch_single_user_data(keycloak_client):
    setup_well_known()
    setup_client_credentials()
    user_id = "test-user-id"
    user_data = {
        "id": user_id,
        "firstName": "John",
        "lastName": "Smith",
    }
    setup_user_response(user_id, user_data)

    received_user = keycloak_client.get_user(user_id)

    assert received_user == user_data
