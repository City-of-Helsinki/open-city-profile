import json

import pytest
import requests

from open_city_profile.consts import (
    CONNECTED_SERVICE_DELETION_FAILED_ERROR,
    CONNECTED_SERVICE_DELETION_NOT_ALLOWED_ERROR,
    PROFILE_DOES_NOT_EXIST_ERROR,
)
from services.enums import ServiceType
from services.models import ServiceConnection
from services.tests.factories import ServiceConnectionFactory
from users.models import User

from ..models import Profile
from .factories import ProfileFactory, ProfileWithPrimaryEmailFactory

GDPR_URL = "https://example.com/"


DELETE_MY_PROFILE_MUTATION = """
    mutation {
        deleteMyProfile(input: {authorizationCode: "code123"}) {
            clientMutationId
        }
    }
"""


def test_user_can_download_profile(rf, user_gql_client):
    profile = ProfileWithPrimaryEmailFactory(user=user_gql_client.user)
    primary_email = profile.emails.first()
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    query = """
        {
            downloadMyProfile(authorizationCode: "code123")
        }
    """
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
                        {"key": "SERVICE_CONNECTIONS", "children": []},
                        {"key": "SUBSCRIPTIONS", "children": []},
                    ],
                }
            ],
        }
    )
    executed = user_gql_client.execute(query, context=request)
    assert expected_json == executed["data"]["downloadMyProfile"]


def test_user_can_delete_his_profile(
    rf, user_gql_client, service_factory, requests_mock
):
    """Deletion is allowed when GDPR URL is set, and service returns a successful status."""
    profile = ProfileFactory(user=user_gql_client.user)
    service = service_factory(gdpr_url=GDPR_URL)
    requests_mock.delete(f"{GDPR_URL}{profile.pk}", json={}, status_code=204)
    ServiceConnectionFactory(profile=profile, service=service)
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    executed = user_gql_client.execute(DELETE_MY_PROFILE_MUTATION, context=request)

    expected_data = {"deleteMyProfile": {"clientMutationId": None}}
    assert dict(executed["data"]) == expected_data
    with pytest.raises(Profile.DoesNotExist):
        profile.refresh_from_db()
    with pytest.raises(User.DoesNotExist):
        user_gql_client.user.refresh_from_db()


def test_user_tries_deleting_his_profile_but_it_fails_partially(
    rf, user_gql_client, service_factory, monkeypatch, requests_mock
):
    """Test an edge case where dry runs passes for all connected services, but the
    proper service connection delete fails for a single connected service. All other
    connected services should still get deleted.
    """

    def mock_gdpr_delete(self, dry_run=False):
        if self.service.service_type == ServiceType.BERTH and not dry_run:
            raise requests.HTTPError("Such big fail! :(")

    monkeypatch.setattr(ServiceConnection, "delete_gdpr_data", mock_gdpr_delete)

    profile = ProfileFactory(user=user_gql_client.user)
    requests_mock.delete(f"{GDPR_URL}{profile.pk}", json={}, status_code=204)
    for st in ServiceType:
        service = service_factory(service_type=st, title=st.label, gdpr_url=GDPR_URL)
        ServiceConnectionFactory(profile=profile, service=service)
    assert ServiceConnection.objects.count() > 1  # More than one connection was created

    request = rf.post("/graphql")
    request.user = user_gql_client.user
    executed = user_gql_client.execute(DELETE_MY_PROFILE_MUTATION, context=request)

    expected_data = {"deleteMyProfile": None}

    assert ServiceConnection.objects.count() == 1
    assert ServiceConnection.objects.first().service.service_type == ServiceType.BERTH
    assert dict(executed["data"]) == expected_data
    assert "code" in executed["errors"][0]["extensions"]
    assert (
        executed["errors"][0]["extensions"]["code"]
        == CONNECTED_SERVICE_DELETION_FAILED_ERROR
    )


@pytest.mark.parametrize(
    "gdpr_url, response_status", [("", 204), ("", 405), (GDPR_URL, 405)]
)
def test_user_cannot_delete_his_profile_if_service_doesnt_allow_it(
    rf, user_gql_client, service_factory, requests_mock, gdpr_url, response_status
):
    """Profile cannot be deleted if connected service doesn't have GDPR URL configured or if the service
    returns a failed status for the dry_run call.
    """
    profile = ProfileFactory(user=user_gql_client.user)
    service = service_factory(gdpr_url=gdpr_url)
    requests_mock.delete(
        f"{GDPR_URL}{profile.pk}", json={}, status_code=response_status
    )
    ServiceConnectionFactory(profile=profile, service=service)
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    executed = user_gql_client.execute(DELETE_MY_PROFILE_MUTATION, context=request)

    expected_data = {"deleteMyProfile": None}
    assert dict(executed["data"]) == expected_data
    assert "code" in executed["errors"][0]["extensions"]
    assert (
        executed["errors"][0]["extensions"]["code"]
        == CONNECTED_SERVICE_DELETION_NOT_ALLOWED_ERROR
    )


def test_user_gets_error_when_deleting_non_existent_profile(rf, user_gql_client):
    profile = ProfileFactory(user=user_gql_client.user)
    profile.delete()
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    executed = user_gql_client.execute(DELETE_MY_PROFILE_MUTATION, context=request)

    expected_data = {"deleteMyProfile": None}
    assert dict(executed["data"]) == expected_data
    assert "code" in executed["errors"][0]["extensions"]
    assert executed["errors"][0]["extensions"]["code"] == PROFILE_DOES_NOT_EXIST_ERROR
