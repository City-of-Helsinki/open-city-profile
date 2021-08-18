import urllib

import pytest

from utils.keycloak import KeycloakAdminClient

server_url = "https://keycloak.example"
realm_name = "test-realm"

client_id = "test-client-id"
client_secret = "test-client-secret"

token_endpoint_url = f"{server_url}/token-endpoint"
access_token = "test-access-token"
unaccepted_access_token = "unaccepted-access-token"

req_mock = None

user_id = "test-user-id"
user_data = {
    "id": user_id,
    "firstName": "John",
    "lastName": "Smith",
}


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
    return req_mock.get(
        f"{server_url}/auth/realms/{realm_name}/.well-known/openid-configuration",
        json={"token_endpoint": token_endpoint_url},
    )


def setup_client_credentials(response_access_tokens=None):
    def body_matcher(request):
        body = urllib.parse.parse_qs(request.text, strict_parsing=True)
        return body == {
            "grant_type": ["client_credentials"],
            "client_id": [client_id],
            "client_secret": [client_secret],
        }

    if response_access_tokens is None:
        response_access_tokens = [access_token]
    responses = [{"json": {"access_token": token}} for token in response_access_tokens]

    return req_mock.post(
        token_endpoint_url,
        responses,
        request_headers={"Content-Type": "application/x-www-form-urlencoded"},
        additional_matcher=body_matcher,
    )


def setup_user_response(user_id, user_data, token=access_token, status_code=200):
    req_mock.get(
        f"{server_url}/auth/admin/realms/{realm_name}/users/{user_id}",
        request_headers={"Authorization": f"Bearer {token}"},
        json=user_data,
        status_code=status_code,
    )


def setup_update_user_response(
    user_id, update_data, token=access_token, status_code=200
):
    def body_matcher(request):
        return request.json() == update_data

    return req_mock.put(
        f"{server_url}/auth/admin/realms/{realm_name}/users/{user_id}",
        request_headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        additional_matcher=body_matcher,
        status_code=status_code,
    )


def test_fetch_single_user_data(keycloak_client):
    setup_well_known()
    setup_client_credentials()
    setup_user_response(user_id, user_data)

    received_user = keycloak_client.get_user(user_id)

    assert received_user == user_data


def test_update_single_user_data(keycloak_client):
    setup_well_known()
    setup_client_credentials()
    update_mock = setup_update_user_response(user_id, user_data)

    keycloak_client.update_user(user_id, user_data)

    assert update_mock.call_count == 1


def test_remember_and_reuse_access_token(keycloak_client):
    well_known_mock = setup_well_known()
    client_credentials_mock = setup_client_credentials()
    setup_user_response(user_id, user_data)
    setup_update_user_response(user_id, user_data)

    keycloak_client.get_user(user_id)
    keycloak_client.update_user(user_id, user_data)
    keycloak_client.get_user(user_id)

    assert well_known_mock.call_count == 1
    assert client_credentials_mock.call_count == 1


def test_renew_access_token_when_old_one_is_not_accepted_with_user_data_fetch(
    keycloak_client,
):
    setup_well_known()
    setup_client_credentials(
        response_access_tokens=[unaccepted_access_token, access_token]
    )
    setup_user_response(
        user_id, user_data, token=unaccepted_access_token, status_code=401
    )
    setup_user_response(user_id, user_data, token=access_token)

    received_user = keycloak_client.get_user(user_id)

    assert received_user == user_data


def test_renew_access_token_when_old_one_is_not_accepted_with_user_update(
    keycloak_client,
):
    setup_well_known()
    setup_client_credentials(
        response_access_tokens=[unaccepted_access_token, access_token]
    )
    setup_update_user_response(
        user_id, user_data, token=unaccepted_access_token, status_code=401
    )
    success_mock = setup_update_user_response(user_id, user_data, token=access_token)

    keycloak_client.update_user(user_id, user_data)

    assert success_mock.call_count == 1
