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
    new_values = {"firstName": "New first name", "lastName": "New last name"}

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
