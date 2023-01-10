from django.dispatch import receiver

from .keycloak_integration import send_profile_changes_to_keycloak
from .schema import profile_updated


@receiver(profile_updated)
def _profile_updated_handler(sender, instance, **kwargs):
    send_profile_changes_to_keycloak(instance)
