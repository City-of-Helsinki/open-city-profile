from django.utils.translation import ugettext_lazy as _
from enumfields import Enum


class NotificationType(Enum):
    RELATIONSHIP_CONFIRMATION_NEEDED = "relationship_confirmation_needed"
    RELATIONSHIP_CONFIRMED = "relationship_confirmed"

    class Labels:
        RELATIONSHIP_CONFIRMATION_NEEDED = _(
            "Legal relationship created, confirmation needed"
        )
        RELATIONSHIP_CONFIRMED = _("Legal relationship confirmed")
