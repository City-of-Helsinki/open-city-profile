from django.utils.translation import ugettext_lazy as _

REPRESENTATION_TYPE = (("custody", _("Custodianship")),)
REPRESENTATIVE_CONFIRMATION_DEGREE = (
    ("none", _("Not authenticated")),
    ("strong", _("Strong authentication (Suomi.fi)")),
    ("id_shown", _("Guardian present")),
    ("proxy", _("Approved via signed document")),
)

EMAIL_TYPES = (
    ("WORK", _("Work email")),
    ("PERSONAL", _("Personal email")),
    ("OTHER", _("Other email")),
)

PHONE_TYPES = (
    ("WORK", _("Work phone")),
    ("HOME", _("Home phone")),
    ("MOBILE", _("Mobile phone")),
    ("OTHER", _("Other phone")),
)

ADDRESS_TYPES = (
    ("WORK", _("Work address")),
    ("HOME", _("Home address")),
    ("OTHER", _("Other address")),
)
