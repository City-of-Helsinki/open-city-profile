from datetime import timedelta
from unittest import TestCase

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import override_settings

from ..models import Email, Profile, TemporaryReadAccessToken
from .factories import (
    EmailFactory,
    SensitiveDataFactory,
    VerifiedPersonalInformationFactory,
)

User = get_user_model()

GDPR_URL = "https://example.com/"


def test_new_profile_with_default_name(user):
    profile = Profile.objects.create(user=user)
    assert profile.first_name == user.first_name
    assert profile.last_name == user.last_name


def test_new_profile_without_default_name():
    user = User.objects.create(email="test@user.com", username="user")
    profile = Profile.objects.create(user=user)
    assert profile.first_name == ""
    assert profile.last_name == ""


def test_new_profile_with_existing_name_and_default_name(user):
    profile = Profile.objects.create(
        first_name="Existingfirstname", last_name="Existinglastname", user=user
    )
    assert profile.first_name == "Existingfirstname"
    assert profile.last_name == "Existinglastname"


def test_new_profile_with_non_existing_name_and_default_name(user):
    profile = Profile.objects.create(first_name="", last_name="", user=user)
    assert profile.first_name
    assert profile.last_name


def test_serialize_profile(profile):
    email_2 = EmailFactory(profile=profile)
    email_1 = EmailFactory(profile=profile, primary=False)
    sensitive_data = SensitiveDataFactory(profile=profile)
    serialized_profile = profile.serialize()
    expected_firstname = {"key": "FIRST_NAME", "value": profile.first_name}
    expected_email = {
        "key": "EMAILS",
        "children": [
            {
                "key": "EMAIL",
                "children": [
                    {"key": "PRIMARY", "value": email_1.primary},
                    {"key": "EMAIL_TYPE", "value": email_1.email_type.name},
                    {"key": "EMAIL", "value": email_1.email},
                ],
            },
            {
                "key": "EMAIL",
                "children": [
                    {"key": "PRIMARY", "value": email_2.primary},
                    {"key": "EMAIL_TYPE", "value": email_2.email_type.name},
                    {"key": "EMAIL", "value": email_2.email},
                ],
            },
        ],
    }
    expected_sensitive_data = {
        "key": "SENSITIVEDATA",
        "children": [{"key": "SSN", "value": sensitive_data.ssn}],
    }
    assert "key" in serialized_profile
    assert "children" in serialized_profile
    assert serialized_profile.get("key") == "PROFILE"
    assert expected_firstname in serialized_profile.get("children")
    serialized_email = list(
        filter(lambda x: x["key"] == "EMAILS", serialized_profile.get("children"))
    )[0]
    TestCase().assertCountEqual(
        serialized_email.get("children"), expected_email.get("children")
    )
    assert expected_sensitive_data in serialized_profile.get("children")


def test_import_customer_data_with_valid_data_set(service):
    data = [
        {
            "customer_id": "321456",
            "first_name": "Jukka",
            "last_name": "Virtanen",
            "ssn": "010190-001A",
            "email": "jukka.virtanen@example.com",
            "address": {
                "address": "Mannerheimintie 1 A 11",
                "postal_code": "00100",
                "city": "Helsinki",
            },
            "phones": ["0412345678", "358 503334411", "755 1122 K"],
        },
        {
            "customer_id": "321457",
            "first_name": "",
            "last_name": "",
            "ssn": "101086-1234",
            "email": "mirja.korhonen@example.com",
            "address": None,
            "phones": [],
        },
    ]
    assert Profile.objects.count() == 0
    result = Profile.import_customer_data(data, service)
    assert len(result.keys()) == 2
    profiles = Profile.objects.all()
    assert len(profiles) == 2
    for profile in profiles:
        assert profile.service_connections.first().service == service


def test_import_customer_data_with_missing_customer_id():
    data = [
        {
            "first_name": "Jukka",
            "last_name": "Virtanen",
            "ssn": "010190-001A",
            "email": "jukka.virtanen@example.com",
            "address": {
                "address": "Mannerheimintie 1 A 11",
                "postal_code": "00100",
                "city": "Helsinki",
            },
            "phones": ["0412345678", "358 503334411", "755 1122 K"],
        },
        {
            "customer_id": "321457",
            "first_name": "",
            "last_name": "",
            "ssn": "101086-1234",
            "email": "mirja.korhonen@example.com",
            "address": None,
            "phones": [],
        },
    ]
    assert Profile.objects.count() == 0
    with pytest.raises(Exception) as e:
        Profile.import_customer_data(data, "")
    assert str(e.value) == "Could not import unknown customer, index: 0"
    assert Profile.objects.count() == 0


def test_import_customer_data_with_missing_email():
    data = [
        {
            "customer_id": "321457",
            "first_name": "Jukka",
            "last_name": "Virtanen",
            "ssn": "010190-001A",
            "address": {
                "address": "Mannerheimintie 1 A 11",
                "postal_code": "00100",
                "city": "Helsinki",
            },
            "phones": ["0412345678", "358 503334411", "755 1122 K"],
        }
    ]
    assert Profile.objects.count() == 0
    Profile.import_customer_data(data, "")
    assert Profile.objects.count() == 1


def test_validation_should_fail_with_invalid_email():
    e = Email("!dsdsd{}{}{}{}{}{")
    with pytest.raises(ValidationError):
        e.save()


def test_should_not_allow_two_primary_emails(profile):
    EmailFactory(profile=profile, primary=True)
    with pytest.raises(ValidationError):
        EmailFactory(profile=profile, primary=True)


class ValidationTestBase:
    @staticmethod
    def passes_validation(instance):
        try:
            instance.full_clean()
        except ValidationError as err:
            assert err is None

    @staticmethod
    def fails_validation(instance):
        with pytest.raises(ValidationError):
            instance.full_clean()

    @staticmethod
    def execute_string_field_max_length_validation_test(
        instance, field_name, max_length
    ):
        setattr(instance, field_name, "x" * max_length)
        ValidationTestBase.passes_validation(instance)

        setattr(instance, field_name, "x" * (max_length + 1))
        ValidationTestBase.fails_validation(instance)


class TestVerifiedPersonalInformationValidation(ValidationTestBase):
    @pytest.mark.parametrize(
        "field_name,max_length",
        [
            ("first_name", 100),
            ("last_name", 100),
            ("given_name", 100),
            ("email", 1024),
            ("municipality_of_residence", 100),
        ],
    )
    def test_string_field_max_length(self, field_name, max_length):
        info = VerifiedPersonalInformationFactory()

        self.execute_string_field_max_length_validation_test(
            info, field_name, max_length
        )

    @pytest.mark.parametrize(
        "field_name,invalid_value",
        [
            ("first_name", "Jiří"),
            ("last_name", "Šlégr"),
            ("given_name", "Ávži"),
            ("municipality_of_residence", "Hurtteváárááš"),
        ],
    )
    def test_string_field_accepted_characters(self, field_name, invalid_value):
        info = VerifiedPersonalInformationFactory()
        setattr(info, field_name, invalid_value)

        ValidationTestBase.fails_validation(info)

    @pytest.mark.parametrize("invalid_value", ["150977_5554"])
    def test_national_identification_number(self, invalid_value):
        info = VerifiedPersonalInformationFactory()
        info.national_identification_number = invalid_value

        ValidationTestBase.fails_validation(info)

    @pytest.mark.parametrize("invalid_value", ["12", "1234", "aaa"])
    def test_municipality_of_residence_number(self, invalid_value):
        info = VerifiedPersonalInformationFactory()
        info.municipality_of_residence_number = invalid_value

        ValidationTestBase.fails_validation(info)


@pytest.mark.parametrize("address_type", ["permanent_address", "temporary_address"])
class TestVerifiedPersonalInformationAddressValidation(ValidationTestBase):
    @pytest.mark.parametrize(
        "field_name,max_length", [("street_address", 100), ("post_office", 100)],
    )
    def test_string_field_max_length(self, address_type, field_name, max_length):
        address = getattr(VerifiedPersonalInformationFactory(), address_type)

        self.execute_string_field_max_length_validation_test(
            address, field_name, max_length
        )

    @pytest.mark.parametrize(
        "field_name,invalid_value",
        [("street_address", "Kuldīgas iela 1"), ("post_office", "Čuđevuáčču")],
    )
    def test_string_field_accepted_characters(
        self, address_type, field_name, invalid_value
    ):
        address = getattr(VerifiedPersonalInformationFactory(), address_type)
        setattr(address, field_name, invalid_value)

        ValidationTestBase.fails_validation(address)

    @pytest.mark.parametrize("invalid_value", ["1234", "1234X", "123456"])
    def test_postal_code(self, address_type, invalid_value):
        address = getattr(VerifiedPersonalInformationFactory(), address_type)
        address.postal_code = invalid_value

        ValidationTestBase.fails_validation(address)


class TestVerifiedPersonalInformationPermanentForeignAddressValidation(
    ValidationTestBase
):
    @pytest.mark.parametrize(
        "field_name,max_length", [("street_address", 100), ("additional_address", 100)],
    )
    def test_string_field_max_length(self, field_name, max_length):
        address = VerifiedPersonalInformationFactory().permanent_foreign_address

        self.execute_string_field_max_length_validation_test(
            address, field_name, max_length
        )

    @pytest.mark.parametrize(
        "field_name,invalid_value",
        [("street_address", "368 Nad Zámečkem"), ("additional_address", "Košiře")],
    )
    def test_string_field_accepted_characters(self, field_name, invalid_value):
        address = VerifiedPersonalInformationFactory().permanent_foreign_address
        setattr(address, field_name, invalid_value)

        ValidationTestBase.fails_validation(address)

    @pytest.mark.parametrize("invalid_country_code", ["Finland", "Suomi", "123"])
    def test_country_codes(self, invalid_country_code):
        address = VerifiedPersonalInformationFactory().permanent_foreign_address
        address.country_code = invalid_country_code

        ValidationTestBase.fails_validation(address)


class TestTemporaryReadAccessTokenValidityDuration:
    def test_by_default_validity_duration_is_two_days(self):
        token = TemporaryReadAccessToken()
        assert token.validity_duration == timedelta(days=2)

    @override_settings(TEMPORARY_PROFILE_READ_ACCESS_TOKEN_VALIDITY_MINUTES=60)
    def test_validity_duration_can_be_controlled_with_a_setting(self):
        token = TemporaryReadAccessToken()
        assert token.validity_duration == timedelta(minutes=60)
