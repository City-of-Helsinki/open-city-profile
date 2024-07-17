from django.conf import settings
from django.core.signals import setting_changed
from django.dispatch import receiver

from open_city_profile.exceptions import (
    ConnectedServiceDeletionFailedError,
    DataConflictError,
)
from utils import keycloak

_keycloak_admin_client: keycloak.KeycloakAdminClient | None = None


def _setup_keycloak_client():
    global _keycloak_admin_client

    if (
        settings.KEYCLOAK_BASE_URL
        and settings.KEYCLOAK_REALM
        and settings.KEYCLOAK_CLIENT_ID
        and settings.KEYCLOAK_CLIENT_SECRET
    ):
        _keycloak_admin_client = keycloak.KeycloakAdminClient(
            settings.KEYCLOAK_BASE_URL,
            settings.KEYCLOAK_REALM,
            settings.KEYCLOAK_CLIENT_ID,
            settings.KEYCLOAK_CLIENT_SECRET,
        )
    else:
        _keycloak_admin_client = None


_setup_keycloak_client()


@receiver(setting_changed)
def _reload_settings(setting, **kwargs):
    if setting in [
        "KEYCLOAK_BASE_URL",
        "KEYCLOAK_REALM",
        "KEYCLOAK_CLIENT_ID",
        "KEYCLOAK_CLIENT_SECRET",
    ]:
        _setup_keycloak_client()


def delete_profile_from_keycloak(profile):
    if not _keycloak_admin_client or not profile.user:
        return

    user_id = profile.user.uuid

    try:
        _keycloak_admin_client.delete_user(user_id)
    except keycloak.UserNotFoundError:
        pass
    except Exception:
        raise ConnectedServiceDeletionFailedError("User deletion unsuccessful.")


def _get_user_data_from_keycloak(user_id):
    try:
        user_data = _keycloak_admin_client.get_user(user_id)

        return {
            "firstName": user_data.get("firstName"),
            "lastName": user_data.get("lastName"),
            "email": user_data.get("email"),
        }
    except keycloak.UserNotFoundError:
        return None


def send_profile_changes_to_keycloak(instance):
    if not instance.user or _keycloak_admin_client is None:
        return

    user_id = instance.user.uuid

    current_kc_data = _get_user_data_from_keycloak(user_id)

    updated_data = {
        "firstName": instance.first_name,
        "lastName": instance.last_name,
        "email": instance.get_primary_email_value(),
    }

    if not current_kc_data or current_kc_data == updated_data:
        return

    email_changed = current_kc_data["email"] != updated_data["email"]

    if email_changed:
        updated_data["emailVerified"] = False

    try:
        _keycloak_admin_client.update_user(user_id, updated_data)
    except keycloak.ConflictError as err:
        raise DataConflictError("Conflict in remote system") from err

    if email_changed:
        try:
            _keycloak_admin_client.send_verify_email(user_id)
        except Exception:
            pass


def get_user_identity_providers(user_id) -> set[str]:
    if not _keycloak_admin_client:
        return set()

    try:
        user_data = _keycloak_admin_client.get_user_federated_identities(user_id)
        return {ip["identityProvider"] for ip in user_data}
    except keycloak.UserNotFoundError:
        return set()


def get_user_credential_types(user_id) -> set[str]:
    if not _keycloak_admin_client:
        return set()

    try:
        user_data = _keycloak_admin_client.get_user_credentials(user_id)
        return {cred["type"] for cred in user_data}
    except keycloak.UserNotFoundError:
        return set()


def get_user_login_methods(user_id) -> set[str]:
    return get_user_identity_providers(user_id) | get_user_credential_types(user_id)
