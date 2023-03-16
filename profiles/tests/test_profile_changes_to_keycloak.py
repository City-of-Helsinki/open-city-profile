import pytest

from open_city_profile.exceptions import DataConflictError
from profiles.keycloak_integration import send_profile_changes_to_keycloak
from utils import keycloak


@pytest.fixture(autouse=True)
def setup_profile_change_handling(keycloak_setup):
    return keycloak_setup


USER_ID = "user id"
FIRST_NAME = "First name"
LAST_NAME = "Last name"
EMAIL = "email@email.example"


def test_do_nothing_if_user_id_is_not_provided(mocker):
    mocked_get_user = mocker.patch.object(keycloak.KeycloakAdminClient, "get_user")
    mocked_update_user = mocker.patch.object(
        keycloak.KeycloakAdminClient, "update_user"
    )

    send_profile_changes_to_keycloak(
        None, FIRST_NAME, LAST_NAME, EMAIL,
    )

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

    send_profile_changes_to_keycloak(
        "not found user id", FIRST_NAME, LAST_NAME, EMAIL,
    )

    mocked_update_user.assert_not_called()


def test_changed_names_are_sent_to_keycloak(mocker):
    new_values = {
        "firstName": FIRST_NAME,
        "lastName": LAST_NAME,
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

    send_profile_changes_to_keycloak(
        USER_ID, new_values["firstName"], new_values["lastName"], None,
    )

    mocked_update_user.assert_called_once_with(USER_ID, new_values)


@pytest.mark.parametrize("send_verify_email_succeeds", (True, False))
def test_changing_email_causes_it_to_be_marked_unverified(
    mocker, send_verify_email_succeeds
):
    new_values = {
        "firstName": FIRST_NAME,
        "lastName": LAST_NAME,
        "email": EMAIL,
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
        side_effect=None
        if send_verify_email_succeeds
        else Exception("send_verify_email failed"),
    )

    send_profile_changes_to_keycloak(
        USER_ID, new_values["firstName"], new_values["lastName"], new_values["email"],
    )

    mocked_update_user.assert_called_once_with(USER_ID, new_values)
    mocked_send_verify_email.assert_called_once_with(USER_ID)


def test_if_there_are_no_changes_then_nothing_is_sent_to_keycloak(mocker):
    values = {"firstName": FIRST_NAME, "lastName": LAST_NAME}

    mocker.patch.object(
        keycloak.KeycloakAdminClient, "get_user", return_value=values,
    )
    mocked_update_user = mocker.patch.object(
        keycloak.KeycloakAdminClient, "update_user"
    )

    send_profile_changes_to_keycloak(
        USER_ID, values["firstName"], values["lastName"], None,
    )

    mocked_update_user.assert_not_called()


def test_when_update_causes_a_conflict_then_data_conflict_error_is_raised(mocker):
    mocker.patch.object(
        keycloak.KeycloakAdminClient,
        "get_user",
        return_value={
            "firstName": FIRST_NAME,
            "lastName": LAST_NAME,
            "email": "old@email.example",
        },
    )

    mocker.patch.object(
        keycloak.KeycloakAdminClient,
        "update_user",
        side_effect=keycloak.ConflictError(),
    )

    with pytest.raises(DataConflictError):
        send_profile_changes_to_keycloak(
            USER_ID, FIRST_NAME, LAST_NAME, EMAIL,
        )
