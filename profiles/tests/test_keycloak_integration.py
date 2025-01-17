import datetime
from unittest.mock import MagicMock

import pytest

from profiles.keycloak_integration import (
    get_user_credential_types,
    get_user_identity_providers,
    get_user_login_methods,
)
from utils.keycloak import UserNotFoundError

RECOVERY_CODE_METHOD = {
    "id": "ed913eb9-6243-45bb-b3f0-66eff3e9235e",
    "type": "recovery-authn-codes",
    "userLabel": "Recovery codes",
    "createdDate": 1716894380239,
    "credentialData": '{"hashIterations":1,"algorithm":"RS512","totalCodes":12,"remainingCodes":12}',
}
OTP_METHOD = {
    "id": "d48ec74d-7c98-4810-b6ad-69022ce94bee",
    "type": "otp",
    "userLabel": "Phone",
    "createdDate": 1716891252633,
    "credentialData": '{"subType":"totp","digits":6,"counter":0,"period":30,"algorithm":"HmacSHA1"}',
}
PASSWORD_METHOD = {
    "id": "b437745e-d17d-415c-a749-637833e87ff0",
    "type": "password",
    "createdDate": 1733399661491,
    "credentialData": '{"hashIterations":100000,"algorithm":"pbkdf2-sha256","additionalParameters":{}}',
}
SUOMI_FI_PROVIDER = {
    "identityProvider": "suomi_fi",
    "userId": "e29a380628e06d3e0e903b8fb245f1910bceee063cda47c27df1f976dc60aa9b",
    "userName": "e29a380628e06d3e0e903b8fb245f1910bceee063cda47c27df1f976dc60aa9b",
}
HELSINKI_AD_PROVIDER = {
    "identityProvider": "helsinkiad",
    "userId": "df6c34b9-22e6-49e7-8c2b-211c5267a84e",
    "userName": "test@example.com",
}


@pytest.fixture
def mock_keycloak_admin_client(monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr("profiles.keycloak_integration._keycloak_admin_client", mock)
    return mock


# Tests for get_user_identity_providers
def test_get_user_identity_providers_no_client(monkeypatch):
    """Test the function when _keycloak_admin_client is None."""
    monkeypatch.setattr("profiles.keycloak_integration._keycloak_admin_client", None)

    assert get_user_identity_providers("dummy_user_id") == []


@pytest.mark.parametrize(
    "mock_return_value, expected_result",
    [
        ([], []),
        ([HELSINKI_AD_PROVIDER], [{"method": "helsinkiad"}]),
        (
            [HELSINKI_AD_PROVIDER, SUOMI_FI_PROVIDER],
            [{"method": "helsinkiad"}, {"method": "suomi_fi"}],
        ),
    ],
)
def test_get_user_identity_providers_with_data(
    mock_keycloak_admin_client, mock_return_value, expected_result
):
    mock_keycloak_admin_client.get_user_federated_identities.return_value = (
        mock_return_value
    )

    assert get_user_identity_providers("dummy_user_id") == expected_result


def test_get_user_identity_providers_user_not_found(mock_keycloak_admin_client):
    """Test the function when the user is not found."""
    mock_keycloak_admin_client.get_user_federated_identities.side_effect = (
        UserNotFoundError
    )

    assert get_user_identity_providers("dummy_user_id") == []


def test_get_user_federated_identities_no_identities(mock_keycloak_admin_client):
    """Test the function when the user has no federated identities."""
    mock_keycloak_admin_client.get_user_federated_identities.return_value = set()

    assert get_user_identity_providers("dummy_user_id") == []


def test_get_user_identity_providers_exception(mock_keycloak_admin_client):
    """Test the function when an exception is raised."""
    mock_keycloak_admin_client.get_user_federated_identities.side_effect = Exception

    with pytest.raises(Exception):  # noqa: B017
        get_user_identity_providers("dummy_user_id")


# Tests for get_user_credential_types
def test_get_user_credential_types_no_client(monkeypatch):
    monkeypatch.setattr("profiles.keycloak_integration._keycloak_admin_client", None)

    assert get_user_credential_types("dummy_user_id") == []


@pytest.mark.parametrize(
    "mock_return_value, expected_result",
    [
        ([], []),
        (
            [PASSWORD_METHOD],
            [
                {
                    "credential_id": PASSWORD_METHOD["id"],
                    "created_at": datetime.datetime(
                        2024, 12, 5, 11, 54, 21, 491000, tzinfo=datetime.UTC
                    ),
                    "method": "password",
                    "user_label": None,
                }
            ],
        ),
        (
            [PASSWORD_METHOD, OTP_METHOD],
            [
                {
                    "credential_id": PASSWORD_METHOD["id"],
                    "created_at": datetime.datetime(
                        2024, 12, 5, 11, 54, 21, 491000, tzinfo=datetime.UTC
                    ),
                    "method": "password",
                    "user_label": None,
                },
                {
                    "credential_id": OTP_METHOD["id"],
                    "created_at": datetime.datetime(
                        2024, 5, 28, 10, 14, 12, 633000, tzinfo=datetime.UTC
                    ),
                    "method": "otp",
                    "user_label": "Phone",
                },
            ],
        ),
    ],
)
def test_get_user_credential_types_with_data(
    mock_keycloak_admin_client, mock_return_value, expected_result
):
    mock_keycloak_admin_client.get_user_credentials.return_value = mock_return_value

    assert get_user_credential_types("dummy_user_id") == expected_result


def test_get_user_credential_types_user_not_found(mock_keycloak_admin_client):
    mock_keycloak_admin_client.get_user_credentials.side_effect = UserNotFoundError

    assert get_user_credential_types("dummy_user_id") == []


def test_get_user_credential_types_exception(mock_keycloak_admin_client):
    mock_keycloak_admin_client.get_user_credentials.side_effect = Exception

    with pytest.raises(Exception):  # noqa: B017
        get_user_credential_types("dummy_user_id")


# Tests for get_user_login_methods
def test_get_user_login_methods(monkeypatch):
    expected_credentials = [
        {
            "created_at": datetime.datetime(
                2024, 12, 5, 11, 54, 21, 491000, tzinfo=datetime.UTC
            ),
            "method": "password",
            "user_label": None,
        },
    ]
    expected_idps = [{"method": "suomi_fi"}]

    monkeypatch.setattr(
        "profiles.keycloak_integration.get_user_credential_types",
        lambda _: expected_credentials,
    )
    monkeypatch.setattr(
        "profiles.keycloak_integration.get_user_identity_providers",
        lambda _: expected_idps,
    )

    assert (
        get_user_login_methods("dummy_user_id") == expected_idps + expected_credentials
    )
