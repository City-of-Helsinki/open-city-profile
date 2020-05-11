import pytest

from open_city_profile.tests.conftest import *  # noqa
from profiles.tests.factories import (
    AddressDataDictFactory,
    ConceptFactory,
    EmailDataDictFactory,
    PhoneDataDictFactory,
    ProfileDataDictFactory,
    ProfileFactory,
    VocabularyFactory,
)


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
    return ProfileDataDictFactory()


@pytest.fixture
def email_data(primary=True):
    return EmailDataDictFactory(primary=primary)


@pytest.fixture
def phone_data(primary=False):
    return PhoneDataDictFactory(primary=primary)


@pytest.fixture
def address_data(primary=False):
    return AddressDataDictFactory(primary=primary)
