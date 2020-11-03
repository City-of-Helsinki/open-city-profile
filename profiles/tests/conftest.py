import pytest
from pytest_factoryboy import register

from open_city_profile.tests.conftest import *  # noqa
from profiles.tests.factories import (
    AddressDataDictFactory,
    ConceptFactory,
    EmailDataDictFactory,
    PhoneDataDictFactory,
    ProfileDataDictFactory,
    ProfileFactory,
    VerifiedPersonalInformationFactory,
    VocabularyFactory,
)
from services.enums import ServiceType
from services.tests.factories import ServiceFactory


@pytest.fixture
def profile(user):
    return ProfileFactory(user=user)


@pytest.fixture
def profile_with_verified_personal_information():
    return VerifiedPersonalInformationFactory().profile


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


# Register factory fixtures
register(ServiceFactory)


@pytest.fixture
def service__service_type():
    """Service fixture has berth type by default."""
    return ServiceType.BERTH


@pytest.fixture(autouse=True)
def setup_audit_log(settings):
    settings.AUDIT_LOGGING_ENABLED = False


@pytest.fixture(autouse=True)
def setup_log_username(settings):
    settings.AUDIT_LOG_USERNAME = False
