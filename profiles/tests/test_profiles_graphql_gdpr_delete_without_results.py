import pytest
import requests

from open_city_profile.consts import (
    CONNECTED_SERVICE_DELETION_FAILED_ERROR,
    CONNECTED_SERVICE_DELETION_NOT_ALLOWED_ERROR,
    MISSING_GDPR_API_TOKEN_ERROR,
    PROFILE_DOES_NOT_EXIST_ERROR,
)
from open_city_profile.oidc import TunnistamoTokenExchange
from open_city_profile.tests.asserts import assert_match_error_code
from services.models import ServiceConnection
from services.tests.factories import ServiceConnectionFactory
from users.models import User
from utils.keycloak import KeycloakAdminClient

from ..models import Profile
from .factories import ProfileFactory, ProfileWithPrimaryEmailFactory

AUTHORIZATION_CODE = "code123"
DELETE_MY_PROFILE_MUTATION = """
    mutation {
        deleteMyProfile(input: {authorizationCode: "code123"}) {
            clientMutationId
        }
    }
"""
SCOPE_1 = "https://api.hel.fi/auth/api-1"
SCOPE_2 = "https://api.hel.fi/auth/api-2"
API_TOKEN_1 = "api_token_1"
API_TOKEN_2 = "api_token_2"
GDPR_API_TOKENS = {
    SCOPE_1: API_TOKEN_1,
    SCOPE_2: API_TOKEN_2,
}


@pytest.fixture
def service_1(service_factory):
    return service_factory(
        name="service-1",
        gdpr_url="https://example-1.com/",
        gdpr_query_scope=f"{SCOPE_1}.gdprquery",
        gdpr_delete_scope=f"{SCOPE_1}.gdprdelete",
    )


@pytest.fixture
def service_2(service_factory):
    return service_factory(
        name="service-2",
        gdpr_url="https://example-2.com/",
        gdpr_query_scope=f"{SCOPE_2}.gdprquery",
        gdpr_delete_scope=f"{SCOPE_2}.gdprdelete",
    )


@pytest.mark.parametrize("with_serviceconnection", (True, False))
def test_user_can_delete_his_profile(
    user_gql_client,
    profile_service,
    service_1,
    requests_mock,
    mocker,
    with_serviceconnection,
):
    """Deletion is allowed when GDPR URL is set, and service returns a successful status."""
    profile = ProfileFactory(user=user_gql_client.user)
    ServiceConnectionFactory(profile=profile, service=profile_service)

    if with_serviceconnection:
        requests_mock.delete(
            f"{service_1.gdpr_url}{profile.pk}", json={}, status_code=204
        )
        ServiceConnectionFactory(profile=profile, service=service_1)
        mocker.patch.object(
            TunnistamoTokenExchange, "fetch_api_tokens", return_value=GDPR_API_TOKENS
        )

    executed = user_gql_client.execute(DELETE_MY_PROFILE_MUTATION, service=service_1)

    if with_serviceconnection:
        expected_data = {"deleteMyProfile": {"clientMutationId": None}}
        assert executed["data"] == expected_data

        with pytest.raises(Profile.DoesNotExist):
            profile.refresh_from_db()
        with pytest.raises(User.DoesNotExist):
            user_gql_client.user.refresh_from_db()
    else:
        assert_match_error_code(executed, "PERMISSION_DENIED_ERROR")
        assert executed["data"]["deleteMyProfile"] is None
        assert Profile.objects.filter(pk=profile.pk).exists()


@pytest.mark.parametrize("should_fail", [False, True])
def test_user_can_dry_run_profile_deletion(
    user_gql_client, service_1, service_2, mocker, requests_mock, should_fail
):
    query = """
        mutation {
            deleteMyProfile(input: {authorizationCode: "code123", dryRun: true}) {
                clientMutationId
            }
        }
    """
    mocker.patch.object(
        TunnistamoTokenExchange, "fetch_api_tokens", return_value=GDPR_API_TOKENS
    )
    profile = ProfileFactory(user=user_gql_client.user)
    ServiceConnectionFactory(profile=profile, service=service_1)
    ServiceConnectionFactory(profile=profile, service=service_2)

    def get_response(request, context):
        if should_fail:
            context.status_code = 403

    service1_mocker = requests_mock.delete(
        service_1.get_gdpr_url_for_profile(profile), status_code=204, text=get_response
    )
    service2_mocker = requests_mock.delete(
        service_2.get_gdpr_url_for_profile(profile), status_code=204, text=get_response
    )

    executed = user_gql_client.execute(query)

    assert service1_mocker.call_count == 1
    assert service2_mocker.call_count == 1
    assert "dry_run=True" in service1_mocker.request_history[0].text
    assert "dry_run=True" in service2_mocker.request_history[0].text
    assert Profile.objects.filter(pk=profile.pk).exists()
    assert ServiceConnection.objects.count() == 2

    if should_fail:
        assert_match_error_code(executed, CONNECTED_SERVICE_DELETION_NOT_ALLOWED_ERROR)
    else:
        assert "errors" not in executed


@pytest.mark.parametrize("kc_delete_user_response_code", [204, 403, 404])
def test_user_deletion_from_keycloak(
    user_gql_client, mocker, kc_delete_user_response_code, keycloak_setup
):
    user = user_gql_client.user
    profile = ProfileFactory(user=user)

    def kc_delete_user_response(*args, **kwargs):
        response = requests.Response()
        response.status_code = kc_delete_user_response_code
        response.raise_for_status()

    mocked_keycloak_delete_user = mocker.patch.object(
        KeycloakAdminClient, "delete_user", side_effect=kc_delete_user_response
    )

    executed = user_gql_client.execute(DELETE_MY_PROFILE_MUTATION)

    if kc_delete_user_response_code in [204, 404]:
        assert executed["data"] == {"deleteMyProfile": {"clientMutationId": None}}
        assert "errors" not in executed
    else:
        assert Profile.objects.filter(pk=profile.pk).exists()
        assert executed["data"]["deleteMyProfile"] is None
        assert_match_error_code(executed, "CONNECTED_SERVICE_DELETION_FAILED_ERROR")

    mocked_keycloak_delete_user.assert_called_once_with(user.uuid)


def test_user_tries_deleting_his_profile_but_it_fails_partially(
    user_gql_client, service_1, service_2, mocker, requests_mock
):
    """Test an edge case where dry runs passes for all connected services, but the
    proper service connection delete fails for a single connected service. All other
    connected services should still get deleted.
    """
    mocker.patch.object(
        TunnistamoTokenExchange, "fetch_api_tokens", return_value=GDPR_API_TOKENS
    )
    profile = ProfileFactory(user=user_gql_client.user)
    ServiceConnectionFactory(profile=profile, service=service_1)
    ServiceConnectionFactory(profile=profile, service=service_2)

    def get_response(request, context):
        if not request.body or "dry_run" not in request.body:
            context.status_code = 403

    requests_mock.delete(service_1.get_gdpr_url_for_profile(profile), status_code=204)
    requests_mock.delete(
        service_2.get_gdpr_url_for_profile(profile), status_code=204, text=get_response
    )

    executed = user_gql_client.execute(DELETE_MY_PROFILE_MUTATION)

    expected_data = {"deleteMyProfile": None}

    assert ServiceConnection.objects.count() == 1
    assert ServiceConnection.objects.first().service == service_2
    assert executed["data"] == expected_data
    assert_match_error_code(executed, CONNECTED_SERVICE_DELETION_FAILED_ERROR)


@pytest.mark.parametrize(
    "gdpr_url, response_status",
    [("", 204), ("", 405), ("https://gdpr-url.example/", 405)],
)
def test_user_cannot_delete_his_profile_if_service_doesnt_allow_it(
    user_gql_client, service_1, requests_mock, gdpr_url, response_status, mocker
):
    """Profile cannot be deleted if connected service doesn't have GDPR URL configured or if the service
    returns a failed status for the dry_run call.
    """
    mocker.patch.object(
        TunnistamoTokenExchange, "fetch_api_tokens", return_value=GDPR_API_TOKENS
    )
    profile = ProfileFactory(user=user_gql_client.user)
    requests_mock.delete(
        f"{gdpr_url}{profile.pk}", json={}, status_code=response_status
    )
    service_1.gdpr_url = gdpr_url
    service_1.save()
    ServiceConnectionFactory(profile=profile, service=service_1)

    executed = user_gql_client.execute(DELETE_MY_PROFILE_MUTATION)

    expected_data = {"deleteMyProfile": None}
    assert executed["data"] == expected_data
    assert_match_error_code(executed, CONNECTED_SERVICE_DELETION_NOT_ALLOWED_ERROR)


def test_user_gets_error_when_deleting_non_existent_profile(user_gql_client):
    executed = user_gql_client.execute(DELETE_MY_PROFILE_MUTATION)

    expected_data = {"deleteMyProfile": None}
    assert executed["data"] == expected_data
    assert_match_error_code(executed, PROFILE_DOES_NOT_EXIST_ERROR)


def test_user_can_delete_his_profile_using_correct_api_tokens(
    user_gql_client, service_1, service_2, mocker, requests_mock
):
    profile = ProfileFactory(user=user_gql_client.user)
    ServiceConnectionFactory(profile=profile, service=service_1)
    ServiceConnectionFactory(profile=profile, service=service_2)

    service_1_gdpr_url = service_1.get_gdpr_url_for_profile(profile)
    service_2_gdpr_url = service_2.get_gdpr_url_for_profile(profile)

    def get_response(request, context):
        if (
            request.url == service_1_gdpr_url
            and request.headers["authorization"] == f"Bearer {API_TOKEN_1}"
        ):
            return

        if (
            request.url == service_2_gdpr_url
            and request.headers["authorization"] == f"Bearer {API_TOKEN_2}"
        ):
            return

        context.status_code = 401

    requests_mock.delete(service_1_gdpr_url, status_code=204, text=get_response)
    requests_mock.delete(service_2_gdpr_url, status_code=204, text=get_response)

    mocked_token_exchange = mocker.patch.object(
        TunnistamoTokenExchange, "fetch_api_tokens", return_value=GDPR_API_TOKENS
    )

    executed = user_gql_client.execute(DELETE_MY_PROFILE_MUTATION)

    mocked_token_exchange.assert_called_once()
    assert mocked_token_exchange.call_args == ((AUTHORIZATION_CODE,),)

    expected_data = {"deleteMyProfile": {"clientMutationId": None}}
    assert executed["data"] == expected_data
    with pytest.raises(Profile.DoesNotExist):
        profile.refresh_from_db()
    with pytest.raises(User.DoesNotExist):
        user_gql_client.user.refresh_from_db()


def test_connection_to_profile_service_without_gdpr_api_settings_does_not_prevent_profile_deletion(
    user_gql_client, profile_service
):
    profile = ProfileFactory(user=user_gql_client.user)
    ServiceConnectionFactory(profile=profile, service=profile_service)

    executed = user_gql_client.execute(
        DELETE_MY_PROFILE_MUTATION, service=profile_service
    )

    assert "errors" not in executed
    with pytest.raises(Profile.DoesNotExist):
        profile.refresh_from_db()
    with pytest.raises(User.DoesNotExist):
        user_gql_client.user.refresh_from_db()


def test_service_doesnt_have_gdpr_delete_scope_set(user_gql_client, service_1, mocker):
    """Missing delete scope shouldn't allow deleting a connected profile."""
    service_1.gdpr_delete_scope = ""
    service_1.save()
    response = {
        "key": "SERVICE-1",
        "children": [{"key": "CUSTOMERID", "value": "123"}],
    }
    mocker.patch.object(ServiceConnection, "download_gdpr_data", return_value=response)
    mocker.patch.object(
        TunnistamoTokenExchange, "fetch_api_tokens", return_value=GDPR_API_TOKENS
    )
    profile = ProfileWithPrimaryEmailFactory(user=user_gql_client.user)
    ServiceConnectionFactory(profile=profile, service=service_1)

    executed = user_gql_client.execute(DELETE_MY_PROFILE_MUTATION)

    assert_match_error_code(executed, CONNECTED_SERVICE_DELETION_NOT_ALLOWED_ERROR)


def test_api_tokens_missing(user_gql_client, service_1, mocker):
    """Missing API token for a service connection that has the query/delete scope set, should be an error."""
    mocker.patch.object(TunnistamoTokenExchange, "fetch_api_tokens", return_value={})
    profile = ProfileFactory(user=user_gql_client.user)
    ServiceConnectionFactory(profile=profile, service=service_1)

    executed = user_gql_client.execute(DELETE_MY_PROFILE_MUTATION)

    assert_match_error_code(executed, MISSING_GDPR_API_TOKEN_ERROR)
