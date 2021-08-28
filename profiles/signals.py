from anymail.exceptions import AnymailError
from django.conf import settings
from django.core.signals import setting_changed
from django.db.models.signals import post_save
from django.dispatch import receiver
from django_ilmoitin.utils import send_notification
from sentry_sdk import capture_exception

from utils.keycloak import KeycloakAdminClient

from .enums import NotificationType, RepresentativeConfirmationDegree
from .models import LegalRelationship
from .schema import profile_updated


def relationship_saved_handler(sender, instance, created, **kwargs):
    confirmed = instance.confirmation_degree != RepresentativeConfirmationDegree.NONE

    # Only notify person whose confirmation is needed
    if created and not confirmed:
        try:
            send_notification(
                instance.representative.email,
                NotificationType.RELATIONSHIP_CONFIRMATION_NEEDED.value,
                instance.get_notification_context(),
                instance.representative.language,
            )
        except (OSError, AnymailError) as e:
            capture_exception(e)

    # Notify both parties involved
    elif confirmed:
        try:
            send_notification(
                instance.representative.email,
                NotificationType.RELATIONSHIP_CONFIRMED.value,
                instance.get_notification_context(),
                instance.representative.language,
            )
        except (OSError, AnymailError) as e:
            capture_exception(e)

        try:
            send_notification(
                instance.representee.email,
                NotificationType.RELATIONSHIP_CONFIRMED.value,
                instance.get_notification_context(),
                instance.representee.language,
            )
        except (OSError, AnymailError) as e:
            capture_exception(e)


if settings.NOTIFICATIONS_ENABLED:
    post_save.connect(relationship_saved_handler, sender=LegalRelationship)


_keycloak_admin_client = None


def profile_changes_to_keycloak(sender, instance, **kwargs):
    user_id = instance.user.uuid

    user_data = _keycloak_admin_client.get_user(user_id)

    current_kc_data = {
        "firstName": user_data.get("firstName"),
        "lastName": user_data.get("lastName"),
        "email": user_data.get("email"),
    }

    updated_data = {
        "firstName": instance.first_name,
        "lastName": instance.last_name,
        "email": instance.get_primary_email_value(),
    }

    if current_kc_data == updated_data:
        return

    email_changed = current_kc_data["email"] != updated_data["email"]

    if email_changed:
        updated_data["emailVerified"] = False

    _keycloak_admin_client.update_user(user_id, updated_data)

    if email_changed:
        try:
            _keycloak_admin_client.send_verify_email(user_id)
        except Exception:
            pass


def _setup_profile_changes_to_keycloak():
    global _keycloak_admin_client

    if (
        settings.KEYCLOAK_BASE_URL
        and settings.KEYCLOAK_REALM
        and settings.KEYCLOAK_CLIENT_ID
        and settings.KEYCLOAK_CLIENT_SECRET
    ):
        _keycloak_admin_client = KeycloakAdminClient(
            settings.KEYCLOAK_BASE_URL,
            settings.KEYCLOAK_REALM,
            settings.KEYCLOAK_CLIENT_ID,
            settings.KEYCLOAK_CLIENT_SECRET,
        )

        profile_updated.connect(
            profile_changes_to_keycloak, dispatch_uid="changes_to_keycloak"
        )
    else:
        _keycloak_admin_client = None
        profile_updated.disconnect(dispatch_uid="changes_to_keycloak")


_setup_profile_changes_to_keycloak()


@receiver(setting_changed)
def _reload_settings(setting, **kwargs):
    if setting in [
        "KEYCLOAK_BASE_URL",
        "KEYCLOAK_REALM",
        "KEYCLOAK_CLIENT_ID",
        "KEYCLOAK_CLIENT_SECRET",
    ]:
        _setup_profile_changes_to_keycloak()
