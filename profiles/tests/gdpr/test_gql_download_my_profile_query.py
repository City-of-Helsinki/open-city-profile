import json
from string import Template
from unittest.mock import call

import pytest

from open_city_profile.consts import MISSING_GDPR_API_TOKEN_ERROR
from open_city_profile.oidc import KeycloakTokenExchange
from open_city_profile.tests.asserts import assert_match_error_code
from profiles.tests.factories import (
    ProfileFactory,
    ProfileWithPrimaryEmailFactory,
    VerifiedPersonalInformationFactory,
)
from profiles.tests.gdpr.utils import patch_keycloak_token_exchange
from services.tests.factories import ServiceConnectionFactory

AUTHORIZATION_CODE = "code123"
ACCESS_TOKEN = "access123"
API_TOKEN = "token123"

DOWNLOAD_MY_PROFILE_MUTATION = Template(
    """
    {
        downloadMyProfile(authorizationCode: "${auth_code}")
    }
"""
).substitute(auth_code=AUTHORIZATION_CODE)

SERVICE_DATA_1 = {
    "key": "SERVICE-1",
    "children": [{"key": "CUSTOMERID", "value": "123"}],
}

SERVICE_DATA_2 = {
    "key": "SERVICE-2",
    "children": [{"key": "STATUS", "value": "PENDING"}],
}


def test_user_can_download_profile(user_gql_client, profile_service):
    profile = ProfileWithPrimaryEmailFactory(user=user_gql_client.user)
    service_connection = ServiceConnectionFactory(
        profile=profile, service=profile_service
    )
    service_connection_created_at = service_connection.created_at.date().isoformat()

    primary_email = profile.emails.first()

    executed = user_gql_client.execute(
        DOWNLOAD_MY_PROFILE_MUTATION, service=profile_service
    )

    expected_json = json.dumps(
        {
            "key": "DATA",
            "children": [
                {
                    "key": "PROFILE",
                    "children": [
                        {"key": "FIRST_NAME", "value": profile.first_name},
                        {"key": "LAST_NAME", "value": profile.last_name},
                        {"key": "NICKNAME", "value": profile.nickname},
                        {"key": "LANGUAGE", "value": profile.language},
                        {"key": "CONTACT_METHOD", "value": profile.contact_method},
                        {
                            "key": "EMAILS",
                            "children": [
                                {
                                    "key": "EMAIL",
                                    "children": [
                                        {
                                            "key": "PRIMARY",
                                            "value": primary_email.primary,
                                        },
                                        {
                                            "key": "EMAIL_TYPE",
                                            "value": primary_email.email_type.name,
                                        },
                                        {"key": "EMAIL", "value": primary_email.email},
                                    ],
                                }
                            ],
                        },
                        {"key": "PHONES", "children": []},
                        {"key": "ADDRESSES", "children": []},
                        {
                            "key": "SERVICE_CONNECTIONS",
                            "children": [
                                {
                                    "key": "SERVICECONNECTION",
                                    "children": [
                                        {
                                            "key": "SERVICE",
                                            "value": profile_service.name,
                                        },
                                        {
                                            "key": "CREATED_AT",
                                            "value": service_connection_created_at,
                                        },
                                    ],
                                },
                            ],
                        },
                    ],
                }
            ],
        }
    )
    assert executed["data"]["downloadMyProfile"] == expected_json, executed


def test_user_can_not_download_profile_without_service_connection(
    service_1, user_gql_client
):
    ProfileFactory(user=user_gql_client.user)

    executed = user_gql_client.execute(DOWNLOAD_MY_PROFILE_MUTATION, service=service_1)
    assert_match_error_code(executed, "PERMISSION_DENIED_ERROR")
    assert executed["data"]["downloadMyProfile"] is None


def download_verified_personal_information_with_loa(loa, user_gql_client, service):
    VerifiedPersonalInformationFactory(profile__user=user_gql_client.user)

    token_payload = {
        "loa": loa,
    }
    executed = user_gql_client.execute(
        DOWNLOAD_MY_PROFILE_MUTATION, service=service, auth_token_payload=token_payload
    )

    full_dump = json.loads(executed["data"]["downloadMyProfile"])

    profile_dump = next(
        child for child in full_dump["children"] if child["key"] == "PROFILE"
    )
    vpi_dump = next(
        child
        for child in profile_dump["children"]
        if child["key"] == "VERIFIEDPERSONALINFORMATION"
    )

    return vpi_dump


@pytest.mark.parametrize("loa", ["substantial", "high"])
def test_verified_personal_information_is_included_in_the_downloaded_profile_when_loa_is_high_enough(
    loa, user_gql_client, profile_service
):
    vpi_dump = download_verified_personal_information_with_loa(
        loa, user_gql_client, profile_service
    )

    assert "error" not in vpi_dump
    assert len(vpi_dump["children"]) > 0


@pytest.mark.parametrize("loa", [None, "foo", "low"])
def test_verified_personal_information_is_replaced_with_an_error_when_loa_is_not_high_enough(
    loa, user_gql_client, profile_service, service
):
    profile = ProfileFactory(user=user_gql_client.user)
    ServiceConnectionFactory(profile=profile, service=service)
    VerifiedPersonalInformationFactory(profile=profile)
    token_payload = {
        "loa": loa,
    }
    executed = user_gql_client.execute(
        DOWNLOAD_MY_PROFILE_MUTATION, service=service, auth_token_payload=token_payload
    )
    assert executed["data"]["downloadMyProfile"] is None
    assert len(executed["errors"]) == 1
    assert executed["errors"][0]["extensions"]["code"] == "INSUFFICIENT_LOA_ERROR"


def test_downloading_non_existent_profile_doesnt_return_errors(user_gql_client):
    executed = user_gql_client.execute(DOWNLOAD_MY_PROFILE_MUTATION)

    assert executed["data"]["downloadMyProfile"] is None
    assert "errors" not in executed


def test_user_can_download_profile_with_connected_services_using_correct_api_tokens(
    user_gql_client, service_1, service_2, mocker, requests_mock
):
    def get_api_token(audience, scope):
        if audience == service_1.gdpr_audience:
            return "service_1_api_token"
        if audience == service_2.gdpr_audience:
            return "service_2_api_token"
        raise RuntimeError("Unexpected GDPR API call")

    def get_response(request, context):
        if (
            request.url == service_1_gdpr_url
            and request.headers["authorization"] == "Bearer service_1_api_token"
        ):
            return SERVICE_DATA_1

        if (
            request.url == service_2_gdpr_url
            and request.headers["authorization"] == "Bearer service_2_api_token"
        ):
            return SERVICE_DATA_2

        raise RuntimeError("Unexpected GDPR API call")

    mocked_access_token_exchange = mocker.patch.object(
        KeycloakTokenExchange, "fetch_access_token", return_value=ACCESS_TOKEN
    )
    mocked_api_token_exchange = mocker.patch.object(
        KeycloakTokenExchange, "fetch_api_token", side_effect=get_api_token
    )
    profile = ProfileFactory(user=user_gql_client.user)
    service_connection_1 = ServiceConnectionFactory(profile=profile, service=service_1)
    service_connection_2 = ServiceConnectionFactory(profile=profile, service=service_2)

    service_1_gdpr_url = service_connection_1.get_gdpr_url()
    service_2_gdpr_url = service_connection_2.get_gdpr_url()

    requests_mock.get(service_1_gdpr_url, json=get_response)
    requests_mock.get(service_2_gdpr_url, json=get_response)

    executed = user_gql_client.execute(DOWNLOAD_MY_PROFILE_MUTATION)

    mocked_access_token_exchange.assert_called_once()
    assert mocked_api_token_exchange.call_count == 2
    assert mocked_access_token_exchange.mock_calls == [call(AUTHORIZATION_CODE)]
    assert mocked_api_token_exchange.mock_calls == [
        call(service_1.gdpr_audience, service_1.gdpr_query_scope),
        call(service_2.gdpr_audience, service_2.gdpr_query_scope),
    ]
    response_data = json.loads(executed["data"]["downloadMyProfile"])["children"]
    assert SERVICE_DATA_1 in response_data
    assert SERVICE_DATA_2 in response_data


@pytest.mark.parametrize("service_response", ({"json": {}}, {"status_code": 204}))
def test_empty_data_from_connected_service_is_not_included_in_response(
    service_response, user_gql_client, service_1, mocker, requests_mock
):
    patch_keycloak_token_exchange(mocker)
    profile = ProfileFactory(user=user_gql_client.user)
    service_connection = ServiceConnectionFactory(profile=profile, service=service_1)

    requests_mock.get(service_connection.get_gdpr_url(), **service_response)

    executed = user_gql_client.execute(DOWNLOAD_MY_PROFILE_MUTATION)

    response_data = json.loads(executed["data"]["downloadMyProfile"])["children"]
    assert len(response_data) == 1
    # Data does not contain the empty response from service
    assert {} not in response_data


def test_when_service_does_not_have_gdpr_url_set_then_error_is_returned(
    user_gql_client, service_1
):
    service_1.gdpr_url = ""
    service_1.save()

    profile = ProfileFactory(user=user_gql_client.user)
    ServiceConnectionFactory(profile=profile, service=service_1)

    executed = user_gql_client.execute(DOWNLOAD_MY_PROFILE_MUTATION)

    assert executed["data"]["downloadMyProfile"] is None
    assert_match_error_code(executed, "CONNECTED_SERVICE_DATA_QUERY_FAILED_ERROR")


def test_when_service_does_not_have_gdpr_query_scope_set_then_error_is_returned(
    user_gql_client, service_1
):
    service_1.gdpr_query_scope = ""
    service_1.save()

    profile = ProfileFactory(user=user_gql_client.user)
    ServiceConnectionFactory(profile=profile, service=service_1)

    executed = user_gql_client.execute(DOWNLOAD_MY_PROFILE_MUTATION)

    assert executed["data"]["downloadMyProfile"] is None
    assert_match_error_code(executed, "CONNECTED_SERVICE_DATA_QUERY_FAILED_ERROR")


def test_api_tokens_missing(user_gql_client, service_1, mocker):
    """Missing API token for a service connection that has the query/delete scope set, should be an error."""
    mocker.patch.object(
        KeycloakTokenExchange, "fetch_access_token", return_value=ACCESS_TOKEN
    )
    mocker.patch.object(KeycloakTokenExchange, "fetch_api_token", return_value=None)
    profile = ProfileFactory(user=user_gql_client.user)
    ServiceConnectionFactory(profile=profile, service=service_1)

    executed = user_gql_client.execute(DOWNLOAD_MY_PROFILE_MUTATION)

    assert_match_error_code(executed, MISSING_GDPR_API_TOKEN_ERROR)


@pytest.mark.parametrize("service_status_code", (401, 403, 404, 500))
def test_when_service_fails_to_return_data_then_error_is_returned(
    service_status_code, user_gql_client, service_1, mocker, requests_mock
):
    patch_keycloak_token_exchange(mocker)
    profile = ProfileFactory(user=user_gql_client.user)
    service_connection = ServiceConnectionFactory(profile=profile, service=service_1)
    requests_mock.get(
        service_connection.get_gdpr_url(), status_code=service_status_code
    )

    executed = user_gql_client.execute(DOWNLOAD_MY_PROFILE_MUTATION)

    assert executed["data"]["downloadMyProfile"] is None
    assert_match_error_code(executed, "CONNECTED_SERVICE_DATA_QUERY_FAILED_ERROR")
