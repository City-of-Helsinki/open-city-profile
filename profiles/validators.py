import re

from django.core.exceptions import ValidationError
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
