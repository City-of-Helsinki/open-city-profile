import pytest
from django.core.exceptions import ValidationError

from profiles.validators import (
    validate_finnish_national_identification_number,
    validate_iso_3166_country_code,
    validate_visible_latin_characters_only,
)


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


class TestValidateFinnishNationalIdentificationNumber:
    @staticmethod
    def execute_denied_number_test(number):
        with pytest.raises(ValidationError):
            validate_finnish_national_identification_number(number)

    @pytest.mark.parametrize("number", ["010101+1231", "241047-456A", "310912A789Y"])
    def test_accept_valid_string(self, number):
        assert validate_finnish_national_identification_number(number) is None

    @pytest.mark.parametrize("number", ["9101010-1111", "101010-11115"])
    def test_deny_extra_characters(self, number):
        self.execute_denied_number_test(number)

    @pytest.mark.parametrize(
        "number",
        ["1x1010-1111", "10①010-1111", "101 10-1111", "1010Ⅲ0-1111", "10101²-1111"],
    )
    def test_deny_non_digits_in_birthdate(self, number):
        self.execute_denied_number_test(number)

    @pytest.mark.parametrize("number", ["401010-1111", "102010-1111"])
    def test_deny_non_existing_birthdate(self, number):
        self.execute_denied_number_test(number)

    @pytest.mark.parametrize("number", ["101010_1111", "101010a1111", "10101051111"])
    def test_deny_invalid_century_character(self, number):
        self.execute_denied_number_test(number)

    @pytest.mark.parametrize("number", ["101010-i111", "101010-1a11", "101010-11.1"])
    def test_deny_non_digits_in_individual_number(self, number):
        self.execute_denied_number_test(number)

    @pytest.mark.parametrize("number", ["101010-111Z", "101010-111s", "101010-111Á"])
    def test_deny_not_allowed_characters_in_checksum(self, number):
        self.execute_denied_number_test(number)


class TestISO3166CountryCode:
    @staticmethod
    def execute_denied_code_test(code):
        with pytest.raises(ValidationError):
            validate_iso_3166_country_code(code)

    @pytest.mark.parametrize("code", ["AX", "FI", "ZW"])
    def test_accept_alpha_2_code(self, code):
        assert validate_iso_3166_country_code(code) is None

    @pytest.mark.parametrize("code", ["DEU", "NPL", "ZMB"])
    def test_accept_alpha_3_code(self, code):
        assert validate_iso_3166_country_code(code) is None

    @pytest.mark.parametrize("code", ["008", "010", "535"])
    def test_accept_numeric_3_code(self, code):
        assert validate_iso_3166_country_code(code) is None

    @pytest.mark.parametrize("code", ["Ax", "fi", "zW"])
    def test_deny_alpha_2_code_with_incorrect_capitalisation(self, code):
        self.execute_denied_code_test(code)

    @pytest.mark.parametrize("code", ["AA", "GJ", "VR"])
    def test_deny_non_existing_alpha_2_code(self, code):
        self.execute_denied_code_test(code)

    @pytest.mark.parametrize("code", ["Deu", "npl", "ZmB"])
    def test_deny_alpha_3_code_with_incorrect_capitalisation(self, code):
        self.execute_denied_code_test(code)

    @pytest.mark.parametrize("code", ["FOO", "BAR", "ZAP"])
    def test_deny_non_existing_alpha_3_code(self, code):
        self.execute_denied_code_test(code)

    @pytest.mark.parametrize("code", [8, 10, 535])
    def test_deny_integer_numeric_code(self, code):
        self.execute_denied_code_test(code)

    @pytest.mark.parametrize("code", ["002", "045", "777"])
    def test_deny_non_existing_numeric_3_code(self, code):
        self.execute_denied_code_test(code)

    @pytest.mark.parametrize("code", ["Albania", "BENIN"])
    def test_deny_country_names(self, code):
        self.execute_denied_code_test(code)
