from anymail.exceptions import AnymailError
from django.db.models.signals import post_save
from django.dispatch import receiver
from django_ilmoitin.utils import send_notification
from sentry_sdk import capture_exception

from .consts import REPRESENTATIVE_CONFIRMATION_DEGREE
from .enums import NotificationType
from .models import LegalRelationship


@receiver(post_save, sender=LegalRelationship)
def relationship_saved_handler(sender, instance, created, **kwargs):
    confirmed = instance.confirmation_degree != REPRESENTATIVE_CONFIRMATION_DEGREE[0][0]

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
