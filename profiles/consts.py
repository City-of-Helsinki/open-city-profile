from django.utils.translation import ugettext_lazy as _

REPRESENTATION_TYPE = (("custody", _("Custodianship")),)
REPRESENTATIVE_CONFIRMATION_DEGREE = (
    ("none", _("Not authenticated")),
    ("strong", _("Strong authentication (Suomi.fi)")),
    ("id_shown", _("Guardian present")),
    ("proxy", _("Approved via signed document")),
)
