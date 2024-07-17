from unittest.mock import MagicMock

import pytest

from profiles.keycloak_integration import (
    get_user_credential_types,
    get_user_identity_providers,
    get_user_login_methods,
)
from utils.keycloak import UserNotFoundError


@pytest.fixture
def mock_keycloak_admin_client(monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr("profiles.keycloak_integration._keycloak_admin_client", mock)
    return mock


# Tests for get_user_identity_providers
def test_get_user_identity_providers_no_client(monkeypatch):
    """Test the function when _keycloak_admin_client is None."""
    monkeypatch.setattr("profiles.keycloak_integration._keycloak_admin_client", None)

    assert get_user_identity_providers("dummy_user_id") == set()


@pytest.mark.parametrize(
    "mock_return_value, expected_result",
    [
        ([], set()),
        ([{"identityProvider": "helsinkiad"}], {"helsinkiad"}),
        (
            [{"identityProvider": "helsinkiad"}, {"identityProvider": "suomi_fi"}],
            {"helsinkiad", "suomi_fi"},
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

    assert get_user_identity_providers("dummy_user_id") == set()


def test_get_user_federated_identities_no_identities(mock_keycloak_admin_client):
    """Test the function when the user has no federated identities."""
    mock_keycloak_admin_client.get_user_federated_identities.return_value = set()

    assert get_user_identity_providers("dummy_user_id") == set()


def test_get_user_identity_providers_exception(mock_keycloak_admin_client):
    """Test the function when an exception is raised."""
    mock_keycloak_admin_client.get_user_federated_identities.side_effect = Exception

    with pytest.raises(Exception):
        get_user_identity_providers("dummy_user_id")


# Tests for get_user_credential_types
def test_get_user_credential_types_no_client(monkeypatch):
    monkeypatch.setattr("profiles.keycloak_integration._keycloak_admin_client", None)

    assert get_user_credential_types("dummy_user_id") == set()


@pytest.mark.parametrize(
    "mock_return_value, expected_result",
    [
        ([], set()),
        ([{"type": "password"}], {"password"}),
        ([{"type": "password"}, {"type": "otp"}], {"password", "otp"}),
    ],
)
def test_get_user_credential_types_with_data(
    mock_keycloak_admin_client, mock_return_value, expected_result
):
    mock_keycloak_admin_client.get_user_credentials.return_value = mock_return_value

    assert get_user_credential_types("dummy_user_id") == expected_result


def test_get_user_credential_types_user_not_found(mock_keycloak_admin_client):
    mock_keycloak_admin_client.get_user_credentials.side_effect = UserNotFoundError

    assert get_user_credential_types("dummy_user_id") == set()


def test_get_user_credential_types_exception(mock_keycloak_admin_client):
    mock_keycloak_admin_client.get_user_credentials.side_effect = Exception

    with pytest.raises(Exception):
        get_user_credential_types("dummy_user_id")


# Tests for get_user_login_methods
def test_get_user_login_methods(monkeypatch):
    monkeypatch.setattr(
        "profiles.keycloak_integration.get_user_credential_types",
        lambda _: {"password"},
    )
    monkeypatch.setattr(
        "profiles.keycloak_integration.get_user_identity_providers",
        lambda _: {"provider1"},
    )

    assert get_user_login_methods("dummy_user_id") == {"password", "provider1"}
