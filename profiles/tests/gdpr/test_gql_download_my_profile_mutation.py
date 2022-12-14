import json
from string import Template

import pytest
from django.utils.translation import gettext as _

from open_city_profile.consts import MISSING_GDPR_API_TOKEN_ERROR
from open_city_profile.oidc import TunnistamoTokenExchange
from open_city_profile.tests.asserts import assert_match_error_code
from profiles.tests.factories import (
    ProfileFactory,
    ProfileWithPrimaryEmailFactory,
    VerifiedPersonalInformationFactory,
)
from services.models import ServiceConnection
from services.tests.factories import ServiceConnectionFactory

AUTHORIZATION_CODE = "code123"

DOWNLOAD_MY_PROFILE_MUTATION = Template(
    """
    {
        downloadMyProfile(authorizationCode: "${auth_code}")
    }
"""
).substitute(auth_code=AUTHORIZATION_CODE)


@pytest.mark.parametrize("with_serviceconnection", (True, False))
def test_user_can_download_profile(
    user_gql_client, service, mocker, with_serviceconnection
):
    profile = ProfileWithPrimaryEmailFactory(user=user_gql_client.user)
    service_connection_created_at = None
    if with_serviceconnection:
        mocker.patch.object(
            TunnistamoTokenExchange, "fetch_api_tokens", return_value=None
        )
        service_connection = ServiceConnectionFactory(profile=profile, service=service)
        service_connection_created_at = service_connection.created_at.date().isoformat()

    primary_email = profile.emails.first()

    executed = user_gql_client.execute(DOWNLOAD_MY_PROFILE_MUTATION, service=service)

    if with_serviceconnection:
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
                                            {
                                                "key": "EMAIL",
                                                "value": primary_email.email,
                                            },
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
                                            {"key": "SERVICE", "value": service.name},
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
    else:
        assert_match_error_code(executed, "PERMISSION_DENIED_ERROR")
        assert executed["data"]["downloadMyProfile"] is None


def download_verified_personal_information_with_loa(
    loa, user_gql_client, service, mocker
):
    profile = VerifiedPersonalInformationFactory(
        profile__user=user_gql_client.user
    ).profile

    mocker.patch.object(TunnistamoTokenExchange, "fetch_api_tokens", return_value=None)
    ServiceConnectionFactory(profile=profile, service=service)

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
    loa, user_gql_client, service, mocker
):
    vpi_dump = download_verified_personal_information_with_loa(
        loa, user_gql_client, service, mocker
    )

    assert "error" not in vpi_dump
    assert len(vpi_dump["children"]) > 0


@pytest.mark.parametrize("loa", [None, "foo", "low"])
def test_verified_personal_information_is_replaced_with_an_error_when_loa_is_not_high_enough(
    loa, user_gql_client, service, mocker
):
    vpi_dump = download_verified_personal_information_with_loa(
        loa, user_gql_client, service, mocker
    )

    assert vpi_dump == {
        "key": "VERIFIEDPERSONALINFORMATION",
        "error": _("No permission to read verified personal information."),
    }


def test_downloading_non_existent_profile_doesnt_return_errors(user_gql_client):
    executed = user_gql_client.execute(DOWNLOAD_MY_PROFILE_MUTATION)

    assert executed["data"]["downloadMyProfile"] is None
    assert "errors" not in executed


def test_user_can_download_profile_with_connected_services(
    user_gql_client, service_1, service_2, gdpr_api_tokens, mocker
):
    expected = {"key": "SERVICE-1", "children": [{"key": "CUSTOMERID", "value": "123"}]}

    def mock_download_gdpr_data(self, api_token: str):
        if self.service.name == service_1.name:
            return expected
        else:
            return {}

    mocker.patch.object(
        ServiceConnection,
        "download_gdpr_data",
        autospec=True,
        side_effect=mock_download_gdpr_data,
    )
    mocker.patch.object(
        TunnistamoTokenExchange, "fetch_api_tokens", return_value=gdpr_api_tokens
    )
    profile = ProfileWithPrimaryEmailFactory(user=user_gql_client.user)
    ServiceConnectionFactory(profile=profile, service=service_1)
    ServiceConnectionFactory(profile=profile, service=service_2)

    executed = user_gql_client.execute(DOWNLOAD_MY_PROFILE_MUTATION)

    response_data = json.loads(executed["data"]["downloadMyProfile"])["children"]
    assert len(response_data) == 2
    assert expected in response_data

    # Data does not contain the empty response from service_2
    assert {} not in response_data


def test_user_can_download_profile_using_correct_api_tokens(
    user_gql_client,
    service_1,
    service_2,
    gdpr_api_tokens,
    api_token_1,
    api_token_2,
    mocker,
):
    def mock_download_gdpr_data(self, api_token: str):
        if (self.service.name == service_1.name and api_token == api_token_1) or (
            self.service.name == service_2.name and api_token == api_token_2
        ):
            return {}

        raise Exception("Wrong token used!")

    profile = ProfileFactory(user=user_gql_client.user)
    ServiceConnectionFactory(profile=profile, service=service_1)
    ServiceConnectionFactory(profile=profile, service=service_2)
    mocked_gdpr_download = mocker.patch.object(
        ServiceConnection,
        "download_gdpr_data",
        autospec=True,
        side_effect=mock_download_gdpr_data,
    )
    mocked_token_exchange = mocker.patch.object(
        TunnistamoTokenExchange, "fetch_api_tokens", return_value=gdpr_api_tokens
    )

    executed = user_gql_client.execute(DOWNLOAD_MY_PROFILE_MUTATION)

    mocked_token_exchange.assert_called_once()
    assert mocked_token_exchange.call_args == ((AUTHORIZATION_CODE,),)
    assert mocked_gdpr_download.call_count == 2
    assert executed["data"]["downloadMyProfile"]


def test_service_doesnt_have_gdpr_query_scope_set(
    user_gql_client, service_1, gdpr_api_tokens, mocker
):
    """Missing query scope should make the query skip the service for a given connected profile."""
    service_1.gdpr_query_scope = ""
    service_1.save()
    response = {
        "key": "SERVICE",
        "children": [{"key": "CUSTOMERID", "value": "123"}],
    }
    mocker.patch.object(ServiceConnection, "download_gdpr_data", return_value=response)
    mocker.patch.object(
        TunnistamoTokenExchange, "fetch_api_tokens", return_value=gdpr_api_tokens
    )
    profile = ProfileWithPrimaryEmailFactory(user=user_gql_client.user)
    ServiceConnectionFactory(profile=profile, service=service_1)

    executed = user_gql_client.execute(DOWNLOAD_MY_PROFILE_MUTATION)

    response_data = json.loads(executed["data"]["downloadMyProfile"])["children"]
    assert len(response_data) == 1
    assert response not in response_data


def test_api_tokens_missing(user_gql_client, service_1, mocker):
    """Missing API token for a service connection that has the query/delete scope set, should be an error."""
    mocker.patch.object(TunnistamoTokenExchange, "fetch_api_tokens", return_value={})
    profile = ProfileFactory(user=user_gql_client.user)
    ServiceConnectionFactory(profile=profile, service=service_1)

    executed = user_gql_client.execute(DOWNLOAD_MY_PROFILE_MUTATION)

    assert_match_error_code(executed, MISSING_GDPR_API_TOKEN_ERROR)
