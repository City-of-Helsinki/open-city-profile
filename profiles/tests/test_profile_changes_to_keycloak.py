import pytest

from open_city_profile.exceptions import DataConflictError
from profiles.schema import profile_updated
from utils import keycloak

from .factories import ProfileFactory, ProfileWithPrimaryEmailFactory


@pytest.fixture(autouse=True)
def setup_profile_change_handling(keycloak_setup):
    return keycloak_setup


def test_do_nothing_if_profile_has_no_user(mocker):
    mocked_get_user = mocker.patch.object(keycloak.KeycloakAdminClient, "get_user")
    mocked_update_user = mocker.patch.object(
        keycloak.KeycloakAdminClient, "update_user"
    )
    profile = ProfileFactory(user=None)

    profile_updated.send(sender=profile.__class__, instance=profile)

    mocked_get_user.assert_not_called()
    mocked_update_user.assert_not_called()


def test_do_nothing_if_user_is_not_found_in_keycloak(mocker):
    mocker.patch.object(
        keycloak.KeycloakAdminClient,
        "get_user",
        side_effect=keycloak.UserNotFoundError(),
    )
    mocked_update_user = mocker.patch.object(
        keycloak.KeycloakAdminClient, "update_user"
    )

    profile = ProfileFactory()

    profile_updated.send(sender=profile.__class__, instance=profile)

    mocked_update_user.assert_not_called()


def test_changed_names_are_sent_to_keycloak(mocker):
    new_values = {
        "firstName": "New first name",
        "lastName": "New last name",
        "email": None,
    }

    mocker.patch.object(
        keycloak.KeycloakAdminClient,
        "get_user",
        return_value={"firstName": "Old first name", "lastName": "Old last name"},
    )
    mocked_update_user = mocker.patch.object(
        keycloak.KeycloakAdminClient, "update_user"
    )

    profile = ProfileFactory(
        first_name=new_values["firstName"], last_name=new_values["lastName"]
    )
    user_id = profile.user.uuid
    profile_updated.send(sender=profile.__class__, instance=profile)

    mocked_update_user.assert_called_once_with(user_id, new_values)


@pytest.mark.parametrize("send_verify_email_succeeds", (True, False))
def test_changing_email_causes_it_to_be_marked_unverified(
    mocker, send_verify_email_succeeds
):
    new_values = {
        "firstName": "First name",
        "lastName": "Last name",
        "email": "new@email.example",
        "emailVerified": False,
    }

    mocker.patch.object(
        keycloak.KeycloakAdminClient,
        "get_user",
        return_value={
            "firstName": new_values["firstName"],
            "lastName": new_values["lastName"],
            "email": "old@email.example",
        },
    )
    mocked_update_user = mocker.patch.object(
        keycloak.KeycloakAdminClient, "update_user"
    )
    mocked_send_verify_email = mocker.patch.object(
        keycloak.KeycloakAdminClient,
        "send_verify_email",
        side_effect=(
            None
            if send_verify_email_succeeds
            else Exception("send_verify_email failed")
        ),
    )

    profile = ProfileFactory(
        first_name=new_values["firstName"], last_name=new_values["lastName"]
    )
    profile.emails.create(email=new_values["email"], primary=True)
    user_id = profile.user.uuid
    profile_updated.send(sender=profile.__class__, instance=profile)

    mocked_update_user.assert_called_once_with(user_id, new_values)
    mocked_send_verify_email.assert_called_once_with(user_id)


def test_if_there_are_no_changes_then_nothing_is_sent_to_keycloak(mocker):
    values = {"firstName": "First name", "lastName": "Last name"}

    mocker.patch.object(keycloak.KeycloakAdminClient, "get_user", return_value=values)
    mocked_update_user = mocker.patch.object(
        keycloak.KeycloakAdminClient, "update_user"
    )

    profile = ProfileFactory(
        first_name=values["firstName"], last_name=values["lastName"]
    )
    profile_updated.send(sender=profile.__class__, instance=profile)

    mocked_update_user.assert_not_called()


def test_when_update_causes_a_conflict_then_data_conflict_error_is_raised(mocker):
    profile = ProfileWithPrimaryEmailFactory()

    mocker.patch.object(
        keycloak.KeycloakAdminClient,
        "get_user",
        return_value={
            "firstName": profile.first_name,
            "lastName": profile.last_name,
            "email": "old@email.example",
        },
    )

    mocker.patch.object(
        keycloak.KeycloakAdminClient,
        "update_user",
        side_effect=keycloak.ConflictError(),
    )

    with pytest.raises(DataConflictError):
        profile_updated.send(sender=profile.__class__, instance=profile)
