from string import Template

import pytest

from open_city_profile.consts import (
    CONNECTED_SERVICE_DELETION_FAILED_ERROR,
    CONNECTED_SERVICE_DELETION_NOT_ALLOWED_ERROR,
    MISSING_GDPR_API_TOKEN_ERROR,
    PROFILE_DOES_NOT_EXIST_ERROR,
)
from open_city_profile.oidc import TunnistamoTokenExchange
from open_city_profile.tests.asserts import assert_match_error_code
from profiles.models import Profile
from profiles.tests.factories import ProfileFactory, ProfileWithPrimaryEmailFactory
from services.models import ServiceConnection
from services.tests.factories import ServiceConnectionFactory
from users.models import User
from utils import keycloak

AUTHORIZATION_CODE = "code123"

DELETE_MY_PROFILE_MUTATION = Template(
    """
    mutation {
        deleteMyProfile(input: {authorizationCode: "${auth_code}"}) {
            clientMutationId
        }
    }
"""
).substitute(auth_code=AUTHORIZATION_CODE)


@pytest.mark.parametrize("with_serviceconnection", (True, False))
def test_user_can_delete_their_profile(
    user_gql_client,
    profile_service,
    service_1,
    gdpr_api_tokens,
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
            TunnistamoTokenExchange, "fetch_api_tokens", return_value=gdpr_api_tokens
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
    user_gql_client,
    service_1,
    service_2,
    gdpr_api_tokens,
    mocker,
    requests_mock,
    should_fail,
):
    query = Template(
        """
        mutation {
            deleteMyProfile(input: {authorizationCode: "${auth_code}", dryRun: true}) {
                clientMutationId
            }
        }
    """
    ).substitute(auth_code=AUTHORIZATION_CODE)
    mocker.patch.object(
        TunnistamoTokenExchange, "fetch_api_tokens", return_value=gdpr_api_tokens
    )
    profile = ProfileFactory(user=user_gql_client.user)
    service_connection_1 = ServiceConnectionFactory(profile=profile, service=service_1)
    service_connection_2 = ServiceConnectionFactory(profile=profile, service=service_2)

    def get_response(request, context):
        if should_fail:
            context.status_code = 403

    service1_mocker = requests_mock.delete(
        service_connection_1.get_gdpr_url(), status_code=204, text=get_response
    )
    service2_mocker = requests_mock.delete(
        service_connection_2.get_gdpr_url(), status_code=204, text=get_response
    )

    executed = user_gql_client.execute(query)

    assert service1_mocker.call_count == 1
    assert service2_mocker.call_count == 1
    assert service1_mocker.request_history[0].qs["dry_run"] == ["true"]
    assert service2_mocker.request_history[0].qs["dry_run"] == ["true"]
    assert Profile.objects.filter(pk=profile.pk).exists()
    assert ServiceConnection.objects.count() == 2

    if should_fail:
        assert_match_error_code(executed, CONNECTED_SERVICE_DELETION_NOT_ALLOWED_ERROR)
    else:
        assert "errors" not in executed


@pytest.mark.parametrize(
    "kc_delete_user_error,is_success",
    [
        (None, True),
        (keycloak.UserNotFoundError, True),
        (keycloak.CommunicationError, False),
    ],
)
def test_user_deletion_from_keycloak(
    user_gql_client, mocker, kc_delete_user_error, is_success, keycloak_setup
):
    user = user_gql_client.user
    profile = ProfileFactory(user=user)

    mocked_keycloak_delete_user = mocker.patch.object(
        keycloak.KeycloakAdminClient,
        "delete_user",
        side_effect=None if kc_delete_user_error is None else kc_delete_user_error(),
    )

    executed = user_gql_client.execute(DELETE_MY_PROFILE_MUTATION)

    if is_success:
        assert executed["data"] == {"deleteMyProfile": {"clientMutationId": None}}
        assert "errors" not in executed
    else:
        assert Profile.objects.filter(pk=profile.pk).exists()
        assert executed["data"]["deleteMyProfile"] is None
        assert_match_error_code(executed, "CONNECTED_SERVICE_DELETION_FAILED_ERROR")

    mocked_keycloak_delete_user.assert_called_once_with(user.uuid)


def test_user_tries_deleting_their_profile_but_it_fails_partially(
    user_gql_client, service_1, service_2, gdpr_api_tokens, mocker, requests_mock
):
    """Test an edge case where dry runs passes for all connected services, but the
    proper service connection delete fails for a single connected service. All other
    connected services should still get deleted.
    """
    mocker.patch.object(
        TunnistamoTokenExchange, "fetch_api_tokens", return_value=gdpr_api_tokens
    )
    profile = ProfileFactory(user=user_gql_client.user)
    service_connection_1 = ServiceConnectionFactory(profile=profile, service=service_1)
    service_connection_2 = ServiceConnectionFactory(profile=profile, service=service_2)

    def get_response(request, context):
        if request.qs.get("dry_run") != ["true"]:
            context.status_code = 403

    requests_mock.delete(service_connection_1.get_gdpr_url(), status_code=204)
    requests_mock.delete(
        service_connection_2.get_gdpr_url(), status_code=204, text=get_response
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
def test_user_cannot_delete_their_profile_if_service_doesnt_allow_it(
    user_gql_client,
    service_1,
    gdpr_api_tokens,
    requests_mock,
    gdpr_url,
    response_status,
    mocker,
):
    """Profile cannot be deleted if connected service doesn't have GDPR URL configured or if the service
    returns a failed status for the dry_run call.
    """
    mocker.patch.object(
        TunnistamoTokenExchange, "fetch_api_tokens", return_value=gdpr_api_tokens
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


def test_user_can_delete_their_profile_using_correct_api_tokens(
    user_gql_client,
    service_1,
    service_2,
    gdpr_api_tokens,
    api_token_1,
    api_token_2,
    mocker,
    requests_mock,
):
    profile = ProfileFactory(user=user_gql_client.user)
    service_connection_1 = ServiceConnectionFactory(profile=profile, service=service_1)
    service_connection_2 = ServiceConnectionFactory(profile=profile, service=service_2)

    service_1_gdpr_url = service_connection_1.get_gdpr_url()
    service_2_gdpr_url = service_connection_2.get_gdpr_url()

    def get_response(request, context):
        if (
            service_1_gdpr_url in request.url
            and request.headers["authorization"] == f"Bearer {api_token_1}"
        ):
            return

        if (
            service_2_gdpr_url in request.url
            and request.headers["authorization"] == f"Bearer {api_token_2}"
        ):
            return

        context.status_code = 401

    requests_mock.delete(service_1_gdpr_url, status_code=204, text=get_response)
    requests_mock.delete(service_2_gdpr_url, status_code=204, text=get_response)

    mocked_token_exchange = mocker.patch.object(
        TunnistamoTokenExchange, "fetch_api_tokens", return_value=gdpr_api_tokens
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


def test_service_doesnt_have_gdpr_delete_scope_set(
    user_gql_client, service_1, gdpr_api_tokens, mocker
):
    """Missing delete scope shouldn't allow deleting a connected profile."""
    service_1.gdpr_delete_scope = ""
    service_1.save()

    mocker.patch.object(
        TunnistamoTokenExchange, "fetch_api_tokens", return_value=gdpr_api_tokens
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
