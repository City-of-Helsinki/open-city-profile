from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import override_settings

from services.tests.factories import ServiceConnectionFactory

from ..models import Email, Profile, TemporaryReadAccessToken
from .factories import (
    AddressFactory,
    EmailFactory,
    PhoneFactory,
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


class UnorderedList(list):
    """Just like a regular list, except that this compares equal with
       another list even if the two lists' order of members differ."""

    def __eq__(self, other):
        if len(self) != len(other):
            return False

        other_copy = list(other)

        try:
            for item in self:
                other_copy.remove(item)
        except ValueError:
            return False

        return True


def children_lists_to_unordered(obj):
    """Recursively goes through an object tree and changes all list values
       of keys named "children" to UnorderedList type."""

    def handle(kv_tuple):
        key, value = kv_tuple
        if key == "children" and isinstance(value, list):
            value = map(children_lists_to_unordered, value)
            value = UnorderedList(value)
        return key, value

    return dict(map(handle, obj.items()))


def test_serialize_profile(profile):
    email_1 = EmailFactory(profile=profile, primary=True)
    email_2 = EmailFactory(profile=profile, primary=False)
    phone_1 = PhoneFactory(profile=profile, primary=True)
    phone_2 = PhoneFactory(profile=profile, primary=False)
    address_1 = AddressFactory(profile=profile, primary=True)
    address_2 = AddressFactory(profile=profile, primary=False)
    sensitive_data = SensitiveDataFactory(profile=profile)
    vpi = VerifiedPersonalInformationFactory(profile=profile)
    service_connection = ServiceConnectionFactory(profile=profile)
    service_connection_created_at_date = "2021-10-04"
    service_connection.created_at = f"{service_connection_created_at_date} 12:00:00Z"
    service_connection.save()

    serialized_profile = children_lists_to_unordered(profile.serialize())

    expected_serialized_profile = children_lists_to_unordered(
        {
            "key": "PROFILE",
            "children": [
                {"key": "FIRST_NAME", "value": profile.first_name},
                {"key": "LAST_NAME", "value": profile.last_name},
                {"key": "NICKNAME", "value": profile.nickname},
                {"key": "LANGUAGE", "value": profile.language},
                {"key": "CONTACT_METHOD", "value": profile.contact_method},
                {
                    "key": "SENSITIVEDATA",
                    "children": [{"key": "SSN", "value": sensitive_data.ssn}],
                },
                {
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
                },
                {
                    "key": "PHONES",
                    "children": [
                        {
                            "key": "PHONE",
                            "children": [
                                {"key": "PRIMARY", "value": phone_1.primary},
                                {"key": "PHONE_TYPE", "value": phone_1.phone_type.name},
                                {"key": "PHONE", "value": phone_1.phone},
                            ],
                        },
                        {
                            "key": "PHONE",
                            "children": [
                                {"key": "PRIMARY", "value": phone_2.primary},
                                {"key": "PHONE_TYPE", "value": phone_2.phone_type.name},
                                {"key": "PHONE", "value": phone_2.phone},
                            ],
                        },
                    ],
                },
                {
                    "key": "ADDRESSES",
                    "children": [
                        {
                            "key": "ADDRESS",
                            "children": [
                                {"key": "PRIMARY", "value": address_1.primary},
                                {
                                    "key": "ADDRESS_TYPE",
                                    "value": address_1.address_type.name,
                                },
                                {"key": "ADDRESS", "value": address_1.address},
                                {"key": "POSTAL_CODE", "value": address_1.postal_code},
                                {"key": "CITY", "value": address_1.city},
                                {
                                    "key": "COUNTRY_CODE",
                                    "value": address_1.country_code,
                                },
                            ],
                        },
                        {
                            "key": "ADDRESS",
                            "children": [
                                {"key": "PRIMARY", "value": address_2.primary},
                                {
                                    "key": "ADDRESS_TYPE",
                                    "value": address_2.address_type.name,
                                },
                                {"key": "ADDRESS", "value": address_2.address},
                                {"key": "POSTAL_CODE", "value": address_2.postal_code},
                                {"key": "CITY", "value": address_2.city},
                                {
                                    "key": "COUNTRY_CODE",
                                    "value": address_2.country_code,
                                },
                            ],
                        },
                    ],
                },
                {
                    "key": "VERIFIEDPERSONALINFORMATION",
                    "children": [
                        {"key": "FIRST_NAME", "value": vpi.first_name},
                        {"key": "LAST_NAME", "value": vpi.last_name},
                        {"key": "GIVEN_NAME", "value": vpi.given_name},
                        {
                            "key": "NATIONAL_IDENTIFICATION_NUMBER",
                            "value": vpi.national_identification_number,
                        },
                        {
                            "key": "MUNICIPALITY_OF_RESIDENCE",
                            "value": vpi.municipality_of_residence,
                        },
                        {
                            "key": "MUNICIPALITY_OF_RESIDENCE_NUMBER",
                            "value": vpi.municipality_of_residence_number,
                        },
                        {
                            "key": "VERIFIEDPERSONALINFORMATIONPERMANENTADDRESS",
                            "children": [
                                {
                                    "key": "STREET_ADDRESS",
                                    "value": vpi.permanent_address.street_address,
                                },
                                {
                                    "key": "POSTAL_CODE",
                                    "value": vpi.permanent_address.postal_code,
                                },
                                {
                                    "key": "POST_OFFICE",
                                    "value": vpi.permanent_address.post_office,
                                },
                            ],
                        },
                        {
                            "key": "VERIFIEDPERSONALINFORMATIONTEMPORARYADDRESS",
                            "children": [
                                {
                                    "key": "STREET_ADDRESS",
                                    "value": vpi.temporary_address.street_address,
                                },
                                {
                                    "key": "POSTAL_CODE",
                                    "value": vpi.temporary_address.postal_code,
                                },
                                {
                                    "key": "POST_OFFICE",
                                    "value": vpi.temporary_address.post_office,
                                },
                            ],
                        },
                        {
                            "key": "VERIFIEDPERSONALINFORMATIONPERMANENTFOREIGNADDRESS",
                            "children": [
                                {
                                    "key": "STREET_ADDRESS",
                                    "value": vpi.permanent_foreign_address.street_address,
                                },
                                {
                                    "key": "ADDITIONAL_ADDRESS",
                                    "value": vpi.permanent_foreign_address.additional_address,
                                },
                                {
                                    "key": "COUNTRY_CODE",
                                    "value": vpi.permanent_foreign_address.country_code,
                                },
                            ],
                        },
                    ],
                },
                {
                    "key": "SERVICE_CONNECTIONS",
                    "children": [
                        {
                            "key": "SERVICECONNECTION",
                            "children": [
                                {
                                    "key": "SERVICE",
                                    "value": service_connection.service.name,
                                },
                                {
                                    "key": "CREATED_AT",
                                    "value": service_connection_created_at_date,
                                },
                            ],
                        }
                    ],
                },
            ],
        }
    )

    assert serialized_profile == expected_serialized_profile


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


def test_should_allow_changing_fields_of_an_existing_primary_email():
    email = EmailFactory(primary=True)
    email.verified = True
    email.save()


class ValidationTestBase:
    def passes_validation(self, instance):
        try:
            instance.full_clean()
        except ValidationError as err:
            assert err is None

    def fails_validation(self, instance):
        with pytest.raises(ValidationError):
            instance.full_clean()

    def execute_string_field_max_length_validation_test(
        self, instance, field_name, max_length
    ):
        setattr(instance, field_name, "x" * max_length)
        self.passes_validation(instance)

        setattr(instance, field_name, "x" * (max_length + 1))
        self.fails_validation(instance)


class TestProfileValidation(ValidationTestBase):
    @pytest.mark.parametrize(
        "field_name,max_length",
        [("first_name", 255), ("last_name", 255), ("nickname", 32)],
    )
    def test_string_field_max_length(self, field_name, max_length, profile):
        self.execute_string_field_max_length_validation_test(
            profile, field_name, max_length
        )


class TestPhoneValidation(ValidationTestBase):
    def test_valid_phone_instance_passes_validation(self):
        instance = PhoneFactory()
        self.passes_validation(instance)

    @pytest.mark.parametrize("phone_number", [None, ""])
    def test_invalid_phone_number(self, phone_number):
        instance = PhoneFactory()
        instance.phone = phone_number
        self.fails_validation(instance)

    def test_phone_number_max_length(self):
        instance = PhoneFactory()

        self.execute_string_field_max_length_validation_test(instance, "phone", 255)


class TestAddressValidation(ValidationTestBase):
    def test_valid_address_instance_passes_validation(self):
        address = AddressFactory()
        self.passes_validation(address)

    @pytest.mark.parametrize(
        "field_name", ["address", "postal_code", "city", "country_code"]
    )
    def test_empty_address_field_passes_validation(
        self, field_name, empty_string_value
    ):
        address = AddressFactory()
        setattr(address, field_name, empty_string_value)
        self.passes_validation(address)

    @pytest.mark.parametrize(
        "field_name,max_length", [("address", 128), ("postal_code", 32), ("city", 64)]
    )
    def test_address_field_max_length(self, field_name, max_length):
        address = AddressFactory()

        self.execute_string_field_max_length_validation_test(
            address, field_name, max_length
        )

    @pytest.mark.parametrize("country_code", ["FI", "SE", "EE", "GB"])
    def test_iso_3166_alpha_2_country_code_passes_validation(self, country_code):
        address = AddressFactory(country_code=country_code)
        self.passes_validation(address)

    @pytest.mark.parametrize("country_code", ["FIN", "246"])
    def test_iso_3166_non_alpha_2_country_code_fails_validation(self, country_code):
        address = AddressFactory()
        address.country_code = country_code
        self.fails_validation(address)

    @pytest.mark.parametrize("country_code", ["Ax", "fi", "VR"])
    def test_invalid_country_code_fails_validation(self, country_code):
        address = AddressFactory()
        address.country_code = country_code
        self.fails_validation(address)


class TestSensitiveDataValidation(ValidationTestBase):
    def test_ssn(self):
        sensitive_data = SensitiveDataFactory()
        sensitive_data.ssn = "150977_5554"

        self.fails_validation(sensitive_data)


class TestVerifiedPersonalInformationValidation(ValidationTestBase):
    @pytest.mark.parametrize(
        "field_name,max_length",
        [
            ("first_name", 100),
            ("last_name", 100),
            ("given_name", 100),
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

        self.fails_validation(info)

    @pytest.mark.parametrize("invalid_value", ["150977_5554"])
    def test_national_identification_number(self, invalid_value):
        info = VerifiedPersonalInformationFactory()
        info.national_identification_number = invalid_value

        self.fails_validation(info)

    @pytest.mark.parametrize("invalid_value", ["12", "1234", "aaa"])
    def test_municipality_of_residence_number(self, invalid_value):
        info = VerifiedPersonalInformationFactory()
        info.municipality_of_residence_number = invalid_value

        self.fails_validation(info)


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

        self.fails_validation(address)

    @pytest.mark.parametrize("invalid_value", ["1234", "1234X", "123456"])
    def test_postal_code(self, address_type, invalid_value):
        address = getattr(VerifiedPersonalInformationFactory(), address_type)
        address.postal_code = invalid_value

        self.fails_validation(address)


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

        self.fails_validation(address)

    @pytest.mark.parametrize("invalid_country_code", ["Finland", "Suomi", "123"])
    def test_country_codes(self, invalid_country_code):
        address = VerifiedPersonalInformationFactory().permanent_foreign_address
        address.country_code = invalid_country_code

        self.fails_validation(address)


class TestTemporaryReadAccessTokenValidityDuration:
    def test_by_default_validity_duration_is_two_days(self):
        token = TemporaryReadAccessToken()
        assert token.validity_duration == timedelta(days=2)

    @override_settings(TEMPORARY_PROFILE_READ_ACCESS_TOKEN_VALIDITY_MINUTES=60)
    def test_validity_duration_can_be_controlled_with_a_setting(self):
        token = TemporaryReadAccessToken()
        assert token.validity_duration == timedelta(minutes=60)
