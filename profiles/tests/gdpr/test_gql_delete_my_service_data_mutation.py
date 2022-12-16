import pytest

from open_city_profile.consts import (
    PROFILE_DOES_NOT_EXIST_ERROR,
    SERVICE_CONNECTION_DOES_NOT_EXIST_ERROR,
    SERVICE_GDPR_API_UNKNOWN_ERROR,
)
from open_city_profile.oidc import TunnistamoTokenExchange
from open_city_profile.tests.asserts import assert_match_error_code
from profiles.tests.factories import ProfileFactory
from services.models import ServiceConnection
from services.tests.factories import ServiceConnectionFactory

DELETE_MY_SERVICE_DATA_MUTATION = """
    mutation deleteMyServiceDataMutation($serviceName: String!, $dryRun: Boolean) {
        deleteMyServiceData(
            input: {
                authorizationCode: "code123",
                serviceName: $serviceName,
                dryRun: $dryRun
            }
        ) {
            result {
                service {
                    name
                    description
                }
                dryRun
                success
                errors {
                    code
                    message {
                        lang
                        text
                    }
                }
            }
        }
    }
"""


def assert_match_error_code_in_result(response, error_code):
    response_data = response["data"]

    errors = []
    for name, value in response_data.items():
        errors.extend(value["result"].get("errors", []))

    assert len(errors) > 0
    for error in errors:
        assert error.get("code") == error_code


@pytest.mark.parametrize("dry_run", [True, False])
def test_user_can_delete_data_from_a_service(
    user_gql_client,
    service_1,
    service_2,
    gdpr_api_tokens,
    mocker,
    requests_mock,
    dry_run,
):
    mocker.patch.object(
        TunnistamoTokenExchange, "fetch_api_tokens", return_value=gdpr_api_tokens
    )
    profile = ProfileFactory(user=user_gql_client.user)
    service_connection_1 = ServiceConnectionFactory(profile=profile, service=service_1)
    service_connection_2 = ServiceConnectionFactory(profile=profile, service=service_2)

    service_1_mocker = requests_mock.delete(
        service_connection_1.get_gdpr_url(), status_code=204
    )
    service_2_mocker = requests_mock.delete(
        service_connection_2.get_gdpr_url(), status_code=204
    )
    variables = {
        "serviceName": service_1.name,
        "dryRun": dry_run,
    }
    executed = user_gql_client.execute(
        DELETE_MY_SERVICE_DATA_MUTATION, variables=variables
    )

    assert "errors" not in executed

    if dry_run:
        assert service_1_mocker.call_count == 1
        assert service_2_mocker.call_count == 0
        assert service_1_mocker.request_history[0].qs["dry_run"] == ["true"]
        assert ServiceConnection.objects.count() == 2
    else:
        assert service_1_mocker.call_count == 2
        assert service_2_mocker.call_count == 0
        assert service_1_mocker.request_history[0].qs["dry_run"] == ["true"]
        assert not service_1_mocker.request_history[1].text
        assert ServiceConnection.objects.count() == 1
        assert ServiceConnection.objects.first().service == service_2


@pytest.mark.parametrize(
    "errors_from_service",
    [None, {"errors": [{"code": "ERROR_CODE", "message": {"en": "Error"}}]}],
)
def test_error_is_returned_when_service_returns_errors(
    user_gql_client,
    service_1,
    gdpr_api_tokens,
    mocker,
    requests_mock,
    errors_from_service,
):
    mocker.patch.object(
        TunnistamoTokenExchange, "fetch_api_tokens", return_value=gdpr_api_tokens
    )
    profile = ProfileFactory(user=user_gql_client.user)
    service_connection = ServiceConnectionFactory(profile=profile, service=service_1)

    service_1_mocker = requests_mock.delete(
        service_connection.get_gdpr_url(), status_code=403, json=errors_from_service,
    )
    executed = user_gql_client.execute(
        DELETE_MY_SERVICE_DATA_MUTATION, variables={"serviceName": service_1.name}
    )

    if errors_from_service is None:
        assert_match_error_code_in_result(executed, SERVICE_GDPR_API_UNKNOWN_ERROR)
    else:
        assert_match_error_code_in_result(
            executed, errors_from_service["errors"][0]["code"]
        )

    assert service_1_mocker.call_count == 1
    assert ServiceConnection.objects.count() == 1
    assert ServiceConnection.objects.first().service == service_1


def test_error_when_trying_to_delete_data_from_a_service_the_user_is_not_connected_to(
    user_gql_client, service_1, service_2
):
    profile = ProfileFactory(user=user_gql_client.user)
    ServiceConnectionFactory(profile=profile, service=service_1)

    variables = {
        "serviceName": service_2.name,
        "dryRun": False,
    }
    executed = user_gql_client.execute(
        DELETE_MY_SERVICE_DATA_MUTATION, variables=variables
    )

    assert_match_error_code(executed, SERVICE_CONNECTION_DOES_NOT_EXIST_ERROR)


def test_error_when_trying_to_delete_data_from_an_unknown_service(
    user_gql_client, service_1
):
    profile = ProfileFactory(user=user_gql_client.user)
    ServiceConnectionFactory(profile=profile, service=service_1)

    variables = {
        "serviceName": "unknown_service",
        "dryRun": False,
    }
    executed = user_gql_client.execute(
        DELETE_MY_SERVICE_DATA_MUTATION, variables=variables
    )

    assert_match_error_code(executed, SERVICE_CONNECTION_DOES_NOT_EXIST_ERROR)


def test_error_when_using_service_delete_with_non_existent_profile(user_gql_client):
    variables = {
        "serviceName": "n/a",
    }
    executed = user_gql_client.execute(
        DELETE_MY_SERVICE_DATA_MUTATION, variables=variables
    )

    expected_data = {"deleteMyServiceData": None}
    assert executed["data"] == expected_data
    assert_match_error_code(executed, PROFILE_DOES_NOT_EXIST_ERROR)
