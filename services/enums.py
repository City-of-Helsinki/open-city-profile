import enumfields
from django.utils.translation import gettext_lazy as _


class ServiceType(enumfields.Enum):
    HKI_MY_DATA = "hki_my_data"
    BERTH = "berth"
    YOUTH_MEMBERSHIP = "youth_membership"
    GODCHILDREN_OF_CULTURE = "godchildren_of_culture"

    class Labels:
        HKI_MY_DATA = _("Helsinki My Data")
        BERTH = _("Berth")
        YOUTH_MEMBERSHIP = _("Youth Membership")
        GODCHILDREN_OF_CULTURE = _("Godchildren of Culture")
