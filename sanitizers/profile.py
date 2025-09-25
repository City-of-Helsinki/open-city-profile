import os
from random import randint

from encrypted_fields.fields import EncryptedFieldMixin
from faker import Faker

SANITIZED_DUMP_FIELD_ENCRYPTION_KEYS = [
    i.strip()
    for i in os.environ.get("SANITIZED_DUMP_FIELD_ENCRYPTION_KEYS", "").split(",")
]


class DummyField(EncryptedFieldMixin):
    keys = SANITIZED_DUMP_FIELD_ENCRYPTION_KEYS


dummy_field = DummyField()
fake = Faker("fi_FI")


def as_encrypted_hex_string(value):
    if not dummy_field.keys[0]:
        raise RuntimeError(
            "Please set the SANITIZED_DUMP_FIELD_ENCRYPTION_KEYS environment variable."
        )

    encrypted_value = dummy_field.encrypt(value)

    return r"\x" + encrypted_value.hex()


def sanitize_encrypted_national_identification_number(value):
    return as_encrypted_hex_string(fake.ssn())


def sanitize_encrypted_email(value):
    return as_encrypted_hex_string(fake.email())


def sanitize_email(value):
    return fake.email()


def sanitize_encrypted_city(value):
    return as_encrypted_hex_string(fake.city())


def sanitize_city(value):
    return fake.city()


def sanitize_encrypted_municipality_number(value):
    return as_encrypted_hex_string(f"{randint(1, 999):03}")


def sanitize_encrypted_first_name(value):
    return as_encrypted_hex_string(fake.first_name())


def sanitize_first_name(value):
    return fake.first_name()


def sanitize_last_name(value):
    return fake.last_name()


def sanitize_encrypted_street_address(value):
    return as_encrypted_hex_string(fake.street_address())


def sanitize_street_address(value):
    return fake.street_address()


def sanitize_encrypted_country_code(value):
    return as_encrypted_hex_string(fake.country_code())


def sanitize_country_code(value):
    return fake.country_code()


def sanitize_encrypted_postal_code(value):
    return as_encrypted_hex_string(fake.postcode())


def sanitize_postal_code(value):
    return fake.postcode()


def sanitize_phone(value):
    return fake.phone_number()
