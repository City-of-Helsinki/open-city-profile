import pytest
from django.core.exceptions import ValidationError

from profiles.validators import validate_visible_latin_characters_only


class TestValidateStringContainsOnlyVisibleLatinCharacters:
    @staticmethod
    def execute_denied_character_test(char):
        string = f"aa{char}bb"
        with pytest.raises(ValidationError):
            validate_visible_latin_characters_only(string)

    @pytest.mark.parametrize("string", ["", " !/09:@AZ[`az{~\u00a0¡¿ÀÖ×Øö÷øÿ"])
    def test_accept_valid_string(self, string):
        assert validate_visible_latin_characters_only(string) is None

    @pytest.mark.parametrize("char", ["\u0100", "\u017f"])
    def test_deny_latin_extended_a_characters(self, char):
        self.execute_denied_character_test(char)

    @pytest.mark.parametrize("char", ["\u0180", "\u024f"])
    def test_deny_latin_extended_b_characters(self, char):
        self.execute_denied_character_test(char)

    @pytest.mark.parametrize("char", ["\u0250", "\uffff", "\U00010000"])
    def test_deny_non_latin_characters(self, char):
        self.execute_denied_character_test(char)

    @pytest.mark.parametrize("char", ["\u0000", "\u001f", "\u007f", "\u0080", "\u009f"])
    def test_deny_control_characters(self, char):
        self.execute_denied_character_test(char)
