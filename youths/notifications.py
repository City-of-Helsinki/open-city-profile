from django_ilmoitin.dummy_context import dummy_context
from django_ilmoitin.registry import notifications

from .enums import NotificationType

notifications.register(
    NotificationType.YOUTH_PROFILE_CONFIRMATION_NEEDED.value,
    NotificationType.YOUTH_PROFILE_CONFIRMATION_NEEDED.label,
)
notifications.register(
    NotificationType.YOUTH_PROFILE_CONFIRMED.value,
    NotificationType.YOUTH_PROFILE_CONFIRMED.label,
)

dummy_context.context.update({"youth_profile": None})
