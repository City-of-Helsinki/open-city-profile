from django.utils.translation import gettext_lazy as _
from enumfields import Enum


class EmailType(Enum):
    NONE = "none"
    WORK = "work"
    PERSONAL = "personal"
    OTHER = "other"

    class Labels:
        NONE = ""
        WORK = _("Work email")
        PERSONAL = _("Personal email")
        OTHER = _("Other email")


class PhoneType(Enum):
    NONE = "none"
    WORK = "work"
    HOME = "home"
    MOBILE = "mobile"
    OTHER = "other"

    class Labels:
        NONE = ""
        WORK = _("Work phone")
        HOME = _("Home phone")
        MOBILE = _("Mobile phone")
        OTHER = _("Other phone")


class AddressType(Enum):
    NONE = "none"
    WORK = "work"
    HOME = "home"
    OTHER = "other"

    class Labels:
        NONE = ""
        WORK = _("Work address")
        HOME = _("Home address")
        OTHER = _("Other address")
