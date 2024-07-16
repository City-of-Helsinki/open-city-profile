import urllib

import pytest
import requests
from requests_mock import Mocker

from utils import keycloak

server_url = "https://keycloak.example"
realm_name = "test-realm"

client_id = "test-client-id"
client_secret = "test-client-secret"

token_endpoint_url = f"{server_url}/token-endpoint"
access_token = "test-access-token"
unaccepted_access_token = "unaccepted-access-token"

req_mock: Mocker = None

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
    return keycloak.KeycloakAdminClient(
        server_url, realm_name, client_id, client_secret
    )


def build_mock_kwargs(response, json: dict = None):
    json = json or {}
    if isinstance(response, int):
        mock_kwargs = {
            "status_code": response,
            "json": json,
        }
    else:
        mock_kwargs = {"exc": response}

    return mock_kwargs


def setup_well_known(response=200):
    return req_mock.get(
        f"{server_url}/realms/{realm_name}/.well-known/openid-configuration",
        **build_mock_kwargs(response, json={"token_endpoint": token_endpoint_url}),
    )


def setup_client_credentials(response_access_tokens=None, response=200):
    def body_matcher(request):
        body = urllib.parse.parse_qs(request.text, strict_parsing=True)
        return body == {
            "grant_type": ["client_credentials"],
            "client_id": [client_id],
            "client_secret": [client_secret],
        }

    if response_access_tokens is None:
        response_access_tokens = [access_token]
    responses = [
        build_mock_kwargs(response, {"access_token": token})
        for token in response_access_tokens
    ]

    return req_mock.post(
        token_endpoint_url,
        responses,
        request_headers={"Content-Type": "application/x-www-form-urlencoded"},
        additional_matcher=body_matcher,
    )


def setup_user_response(user_id, user_data, token=access_token, response=200):
    req_mock.get(
        f"{server_url}/admin/realms/{realm_name}/users/{user_id}",
        request_headers={"Authorization": f"Bearer {token}"},
        **build_mock_kwargs(response, user_data),
    )


def setup_update_user_response(user_id, update_data, token=access_token, response=200):
    def body_matcher(request):
        return request.json() == update_data

    return req_mock.put(
        f"{server_url}/admin/realms/{realm_name}/users/{user_id}",
        request_headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        additional_matcher=body_matcher,
        **build_mock_kwargs(response),
    )


def setup_delete_user_response(user_id, token=access_token, response=200):
    return req_mock.delete(
        f"{server_url}/admin/realms/{realm_name}/users/{user_id}",
        request_headers={"Authorization": f"Bearer {token}"},
        **build_mock_kwargs(response),
    )


def setup_send_verify_email_response(user_id, token=access_token, response=200):
    return req_mock.put(
        f"{server_url}/admin/realms/{realm_name}/users/{user_id}/send-verify-email?client_id={client_id}",
        request_headers={"Authorization": f"Bearer {token}"},
        **build_mock_kwargs(response),
    )


@pytest.mark.parametrize(
    "well_known_response,client_credentials_response",
    (
        (500, 200),
        (599, 200),
        (requests.RequestException, 200),
        (200, 500),
        (200, 599),
        (200, requests.RequestException),
    ),
)
def test_raise_communication_error_when_can_not_communicate_with_keycloak_during_authentication(
    keycloak_client, well_known_response, client_credentials_response
):
    setup_well_known(response=well_known_response)
    setup_client_credentials(response=client_credentials_response)

    with pytest.raises(keycloak.CommunicationError):
        keycloak_client.get_user(user_id)


@pytest.mark.parametrize("status_code", (400, 404))
def test_raise_authentication_error_when_can_not_get_openid_configuration(
    keycloak_client, status_code
):
    setup_well_known(response=status_code)

    with pytest.raises(keycloak.AuthenticationError):
        keycloak_client.get_user(user_id)


@pytest.mark.parametrize("status_code", (400, 404))
def test_raise_authentication_error_when_can_not_get_client_credentials(
    keycloak_client, status_code
):
    setup_well_known()
    setup_client_credentials(response=status_code)

    with pytest.raises(keycloak.AuthenticationError):
        keycloak_client.get_user(user_id)


def test_fetch_single_user_data(keycloak_client):
    setup_well_known()
    setup_client_credentials()
    setup_user_response(user_id, user_data)

    received_user = keycloak_client.get_user(user_id)

    assert received_user == user_data


def test_raise_user_not_found_error_when_trying_to_get_data_for_non_existing_user(
    keycloak_client,
):
    setup_well_known()
    setup_client_credentials()
    setup_user_response(user_id, user_data, response=404)

    with pytest.raises(keycloak.UserNotFoundError):
        keycloak_client.get_user(user_id)


@pytest.mark.parametrize("response", (400, 403, 500, 599, requests.RequestException))
def test_raise_communication_error_when_can_not_communicate_with_keycloak_during_user_data_fetch(
    keycloak_client, response
):
    setup_well_known()
    setup_client_credentials()
    setup_user_response(user_id, user_data, response=response)

    with pytest.raises(keycloak.CommunicationError):
        keycloak_client.get_user(user_id)


def test_update_single_user_data(keycloak_client):
    setup_well_known()
    setup_client_credentials()
    update_mock = setup_update_user_response(user_id, user_data)

    keycloak_client.update_user(user_id, user_data)

    assert update_mock.call_count == 1


def test_raise_user_not_found_error_when_trying_to_update_data_for_non_existing_user(
    keycloak_client,
):
    setup_well_known()
    setup_client_credentials()
    setup_update_user_response(user_id, user_data, response=404)

    with pytest.raises(keycloak.UserNotFoundError):
        keycloak_client.update_user(user_id, user_data)


def test_raise_conflict_error_when_update_user_data_conflicts(keycloak_client):
    setup_well_known()
    setup_client_credentials()
    setup_update_user_response(user_id, user_data, response=409)

    with pytest.raises(keycloak.ConflictError):
        keycloak_client.update_user(user_id, user_data)


@pytest.mark.parametrize("response", (400, 403, 500, 599, requests.RequestException))
def test_raise_communication_error_when_can_not_communicate_with_keycloak_during_user_data_update(
    keycloak_client, response
):
    setup_well_known()
    setup_client_credentials()
    setup_update_user_response(user_id, user_data, response=response)

    with pytest.raises(keycloak.CommunicationError):
        keycloak_client.update_user(user_id, user_data)


def test_delete_single_user_data(keycloak_client):
    setup_well_known()
    setup_client_credentials()
    delete_mock = setup_delete_user_response(user_id)

    keycloak_client.delete_user(user_id)

    assert delete_mock.call_count == 1


def test_raise_user_not_found_error_when_trying_to_delete_non_existing_user(
    keycloak_client,
):
    setup_well_known()
    setup_client_credentials()
    setup_delete_user_response(user_id, response=404)

    with pytest.raises(keycloak.UserNotFoundError):
        keycloak_client.delete_user(user_id)


@pytest.mark.parametrize("response", (400, 403, 500, 599, requests.RequestException))
def test_raise_communication_error_when_can_not_communicate_with_keycloak_during_user_data_delete(
    keycloak_client, response
):
    setup_well_known()
    setup_client_credentials()
    setup_delete_user_response(user_id, response=response)

    with pytest.raises(keycloak.CommunicationError):
        keycloak_client.delete_user(user_id)


def test_send_verify_email_to_user(keycloak_client):
    setup_well_known()
    setup_client_credentials()
    send_email_mock = setup_send_verify_email_response(user_id)

    keycloak_client.send_verify_email(user_id)

    assert send_email_mock.call_count == 1


def test_raise_user_not_found_error_when_trying_to_send_verify_email_to_non_existing_user(
    keycloak_client,
):
    setup_well_known()
    setup_client_credentials()
    setup_send_verify_email_response(user_id, response=404)

    with pytest.raises(keycloak.UserNotFoundError):
        keycloak_client.send_verify_email(user_id)


@pytest.mark.parametrize("response", (400, 403, 500, 599, requests.RequestException))
def test_raise_communication_error_when_can_not_communicate_with_keycloak_during_verify_email_send(
    keycloak_client, response
):
    setup_well_known()
    setup_client_credentials()
    setup_send_verify_email_response(user_id, response=response)

    with pytest.raises(keycloak.CommunicationError):
        keycloak_client.send_verify_email(user_id)


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
    setup_user_response(user_id, user_data, token=unaccepted_access_token, response=401)
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
        user_id, user_data, token=unaccepted_access_token, response=401
    )
    success_mock = setup_update_user_response(user_id, user_data, token=access_token)

    keycloak_client.update_user(user_id, user_data)

    assert success_mock.call_count == 1


def test_renew_access_token_when_old_one_is_not_accepted_with_verify_email_sending(
    keycloak_client,
):
    setup_well_known()
    setup_client_credentials(
        response_access_tokens=[unaccepted_access_token, access_token]
    )
    setup_send_verify_email_response(
        user_id, token=unaccepted_access_token, response=401
    )
    success_mock = setup_send_verify_email_response(user_id, token=access_token)

    keycloak_client.send_verify_email(user_id)

    assert success_mock.call_count == 1


def test_get_user_federated_identities(keycloak_client):
    setup_well_known()
    setup_client_credentials()
    federated_identities = [
        {
            "identityProvider": "provider",
            "userId": "id",
            "userName": "username@example.test",
        },
    ]
    req_mock.get(
        f"{server_url}/admin/realms/{realm_name}/users/{user_id}/federated-identity",
        request_headers={"Authorization": f"Bearer {access_token}"},
        json=federated_identities,
    )

    result = keycloak_client.get_user_federated_identities(user_id)

    assert result == federated_identities
