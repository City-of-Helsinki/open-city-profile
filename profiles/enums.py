from django.utils.translation import ugettext_lazy as _
from enumfields import Enum


class RepresentationType(Enum):
    CUSTODY = "custody"

    class Labels:
        CUSTODY = _("Custodianship")


class RepresentativeConfirmationDegree(Enum):
    NONE = "none"
    STRONG = "strong"
    ID_SHOWN = "id_shown"
    PROXY = "proxy"

    class Labels:
        NONE = _("Not authenticated")
        STRONG = _("Strong authentication (Suomi.fi)")
        ID_SHOWN = _("Guardian present")
        PROXY = _("Approved via signed document")


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
