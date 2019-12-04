import pytest
from faker import Faker

from open_city_profile.tests.conftest import *  # noqa
from profiles.enums import AddressType, EmailType, PhoneType
from profiles.tests.factories import ConceptFactory, ProfileFactory, VocabularyFactory

fake = Faker()


@pytest.fixture
def profile(user):
    return ProfileFactory(user=user)


@pytest.fixture
def vocabulary():
    return VocabularyFactory()


@pytest.fixture
def concept(vocabulary):
    return ConceptFactory(vocabulary=vocabulary)


@pytest.fixture
def profile_data():
    return {"nickname": fake.name()}


@pytest.fixture
def email_data(primary=False):
    return {
        "email": fake.email(),
        "email_type": EmailType.PERSONAL.name,
        "primary": primary,
    }


@pytest.fixture
def phone_data(primary=False):
    return {
        "phone": fake.phone_number(),
        "phone_type": PhoneType.WORK.name,
        "primary": primary,
    }


@pytest.fixture
def address_data(primary=False):
    return {
        "address": fake.street_address(),
        "postal_code": fake.postalcode(),
        "city": fake.city(),
        "country_code": fake.country_code(representation="alpha-2"),
        "address_type": AddressType.WORK.name,
        "primary": primary,
    }
