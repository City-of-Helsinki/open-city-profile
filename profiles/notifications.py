from django_ilmoitin.dummy_context import dummy_context
from django_ilmoitin.registry import notifications

from .enums import NotificationType

notifications.register(
    NotificationType.RELATIONSHIP_CONFIRMATION_NEEDED.value,
    NotificationType.RELATIONSHIP_CONFIRMATION_NEEDED.label,
)
notifications.register(
    NotificationType.RELATIONSHIP_CONFIRMED.value,
    NotificationType.RELATIONSHIP_CONFIRMED.label,
)

dummy_context.context.update({"relationship": None})
