import pytest

from open_city_profile.tests.conftest import *  # noqa
from profiles.tests.conftest import *  # noqa
from youths.tests.factories import YouthProfileFactory


@pytest.fixture
def youth_profile(profile):
    return YouthProfileFactory(profile=profile)


@pytest.fixture(autouse=True)
def setup_youth_membership_dates(settings):
    settings.YOUTH_MEMBERSHIP_SEASON_END_DATE = 31, 8
    settings.YOUTH_MEMBERSHIP_FULL_SEASON_START_MONTH = 5
