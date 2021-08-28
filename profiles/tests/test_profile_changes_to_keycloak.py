import pytest

from profiles.schema import profile_updated
from utils.keycloak import KeycloakAdminClient

from .factories import ProfileFactory


@pytest.fixture(autouse=True)
def setup_profile_change_handling(settings):
    settings.KEYCLOAK_BASE_URL = "https://localhost/keycloak"
    settings.KEYCLOAK_REALM = "test-keycloak-realm"
    settings.KEYCLOAK_CLIENT_ID = "test-keycloak-client-id"
    settings.KEYCLOAK_CLIENT_SECRET = "test-keycloak-client-secret"


def test_changed_names_are_sent_to_keycloak(mocker):
    new_values = {
        "firstName": "New first name",
        "lastName": "New last name",
        "email": None,
    }

    mocker.patch.object(
        KeycloakAdminClient,
        "get_user",
        return_value={"firstName": "Old first name", "lastName": "Old last name"},
    )
    mocked_update_user = mocker.patch.object(KeycloakAdminClient, "update_user")

    profile = ProfileFactory(
        first_name=new_values["firstName"], last_name=new_values["lastName"]
    )
    user_id = profile.user.uuid
    profile_updated.send(sender=profile.__class__, instance=profile)

    mocked_update_user.assert_called_once_with(user_id, new_values)


def test_changing_email_causes_it_to_be_marked_unverified(mocker):
    new_values = {
        "firstName": "First name",
        "lastName": "Last name",
        "email": "new@email.example",
        "emailVerified": False,
    }

    mocker.patch.object(
        KeycloakAdminClient,
        "get_user",
        return_value={
            "firstName": new_values["firstName"],
            "lastName": new_values["lastName"],
            "email": "old@email.example",
        },
    )
    mocked_update_user = mocker.patch.object(KeycloakAdminClient, "update_user")

    profile = ProfileFactory(
        first_name=new_values["firstName"], last_name=new_values["lastName"]
    )
    profile.emails.create(email=new_values["email"], primary=True)
    user_id = profile.user.uuid
    profile_updated.send(sender=profile.__class__, instance=profile)

    mocked_update_user.assert_called_once_with(user_id, new_values)


def test_if_there_are_no_changes_then_nothing_is_sent_to_keycloak(mocker):
    values = {"firstName": "First name", "lastName": "Last name"}

    mocker.patch.object(
        KeycloakAdminClient, "get_user", return_value=values,
    )
    mocked_update_user = mocker.patch.object(KeycloakAdminClient, "update_user")

    profile = ProfileFactory(
        first_name=values["firstName"], last_name=values["lastName"]
    )
    profile_updated.send(sender=profile.__class__, instance=profile)

    mocked_update_user.assert_not_called()