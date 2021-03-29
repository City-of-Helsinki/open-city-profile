from datetime import timedelta

import pytest
from django.utils import timezone as django_timezone
from pytest_factoryboy import register

from open_city_profile.tests.conftest import *  # noqa
from profiles.models import _default_temporary_read_access_token_validity_duration
from profiles.tests.factories import (
    AddressDataDictFactory,
    ConceptFactory,
    EmailDataDictFactory,
    PhoneDataDictFactory,
    ProfileDataDictFactory,
    ProfileFactory,
    SensitiveDataFactory,
    TemporaryReadAccessTokenFactory,
    VerifiedPersonalInformationFactory,
    VocabularyFactory,
)
from services.enums import ServiceType
from services.tests.factories import (
    ServiceClientIdFactory,
    ServiceConnectionFactory,
    ServiceFactory,
)


@pytest.fixture
def profile():
    return ProfileFactory(
        user=UserFactory()  # noqa: F405 Name may be defined from star imports
    )


@pytest.fixture
def profile_with_sensitive_data():
    return SensitiveDataFactory().profile


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
register(ServiceConnectionFactory)
register(ServiceClientIdFactory)


@pytest.fixture
def service__service_type():
    """Service fixture has berth type by default."""
    return ServiceType.BERTH


@pytest.fixture
def service__implicit_connection():
    """Service fixture has implicit service connection enabled by default"""
    return True


@pytest.fixture(autouse=True)
def setup_audit_log(settings):
    settings.AUDIT_LOGGING_ENABLED = False


VERIFIED_PERSONAL_INFORMATION_ADDRESS_FIELD_NAMES = {
    "permanent_address": ["street_address", "postal_code", "post_office"],
    "temporary_address": ["street_address", "postal_code", "post_office"],
    "permanent_foreign_address": [
        "street_address",
        "additional_address",
        "country_code",
    ],
}
VERIFIED_PERSONAL_INFORMATION_ADDRESS_TYPES = (
    VERIFIED_PERSONAL_INFORMATION_ADDRESS_FIELD_NAMES.keys()
)


class TemporaryProfileReadAccessTokenTestBase:
    def create_expired_token(self, profile):
        over_default_validity_duration = _default_temporary_read_access_token_validity_duration() + timedelta(
            seconds=1
        )
        expired_token_creation_time = (
            django_timezone.now() - over_default_validity_duration
        )
        token = TemporaryReadAccessTokenFactory(
            profile=profile, created_at=expired_token_creation_time
        )
        return token
