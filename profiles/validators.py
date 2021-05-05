import re

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _

# Unicode blocks:
#   Basic Latin:        U+0000-U+007F
#   Latin-1 Supplement: U+0080-U+00FF
# C0 Control codes:     U+0000-U+001F, U+007F
# C1 Control codes:     U+0080-U+009F
#
# This RE matches characters in Basic Latin and Latin-1 Supplement
# Unicode blocks, excluding the C0 and C1 Control codes.
_visible_latin_characters_re = re.compile("[\u0020-\u007e\u00a0-\u00ff]*")


def validate_visible_latin_characters_only(value: str) -> None:
    if not _visible_latin_characters_re.fullmatch(value):
        raise ValidationError(
            _("String contains unaccepted characters"),
            code="unaccepted_characters",
            params={"value": value},
        )


# This is not a perfect Finnish personal identity code validator.
# It checks the allowed characters, but e.g. doesn't notice
# non-existing dates or calculate the checksum.
_finnish_national_identification_number_validator = RegexValidator(
    regex="^[0-3][0-9][0-1][0-9]{3}[A+-][0-9]{3}[0-9A-Y]$",
    message=_("Invalid Finnish personal identity code"),
)


def validate_finnish_national_identification_number(value: str) -> None:
    _finnish_national_identification_number_validator(value)


_finnish_municipality_of_residence_number_validator = RegexValidator(
    regex="^[0-9]{3}$", message=_("Must be exactly three digits")
)


def validate_finnish_municipality_of_residence_number(value: str) -> None:
    _finnish_municipality_of_residence_number_validator(value)
