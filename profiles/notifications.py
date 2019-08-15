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
