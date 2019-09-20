from django.utils.translation import ugettext_lazy as _
from enumfields import Enum


class NotificationType(Enum):
    YOUTH_PROFILE_CONFIRMATION_NEEDED = "youth_profile_confirmation_needed"
    YOUTH_PROFILE_CONFIRMED = "youth_profile_confirmed"

    class Labels:
        YOUTH_PROFILE_CONFIRMATION_NEEDED = _(
            "Youth profile created, confirmation needed"
        )
        YOUTH_PROFILE_CONFIRMED = _("Youth profile confirmed")
