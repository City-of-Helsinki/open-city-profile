from django.utils.translation import ugettext_lazy as _

GENDERS = (
    ("male", _("Male")),
    ("female", _("Female")),
    ("other", _("Other")),
    ("dont_know", _("Don't know")),
    ("rather_not_say", _("Rather not say")),
)

ILLNESSES = (
    ("diabetes", _("Diabetes")),
    ("epilepsy", _("Epilepsy")),
    ("heart_disease", _("Serious heart or circulatory disease")),
    ("serious_allergy", _("Serious allergy")),
)

LANGUAGES = (
    ("fi", _("Finnish")),
    ("en", _("English")),
    ("sv", _("Swedish")),
    ("so", _("Somali")),
    ("ar", _("Arabic")),
)
