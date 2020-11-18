from django.utils.translation import ugettext_lazy as _
from enumfields import Enum


class YouthLanguage(Enum):
    FINNISH = "fi"
    ENGLISH = "en"
    SWEDISH = "sv"
    SOMALI = "so"
    ARABIC = "ar"
    ESTONIAN = "et"
    RUSSIAN = "ru"

    class Labels:
        FINNISH = _("Finnish")
        ENGLISH = _("English")
        SWEDISH = _("Swedish")
        SOMALI = _("Somali")
        ARABIC = _("Arabic")
        ESTONIAN = _("Estonian")
        RUSSIAN = _("Russian")

    # @classmethod
    # def to_graphene_enum(cls):
    #     items = [(item.name, item.label) for item in cls]
    #     return items
