import pytest
from pytest_factoryboy import register

from open_city_profile.tests.conftest import *  # noqa
from profiles.tests.conftest import *  # noqa
from services.enums import ServiceType
from services.tests.factories import ServiceFactory
from youths.tests.factories import YouthProfileFactory


@pytest.fixture
def youth_profile(profile):
    return YouthProfileFactory(profile=profile)


@pytest.fixture(autouse=True)
def setup_youth_membership_dates(settings):
    settings.YOUTH_MEMBERSHIP_SEASON_END_DATE = 31, 8
    settings.YOUTH_MEMBERSHIP_FULL_SEASON_START_MONTH = 5


# Register factory fixtures
register(ServiceFactory)


@pytest.fixture
def service__service_type():
    """Service fixture has youth membership type by default."""
    return ServiceType.YOUTH_MEMBERSHIP
