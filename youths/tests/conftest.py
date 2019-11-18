import pytest

from open_city_profile.tests.conftest import *  # noqa
from profiles.tests.conftest import *  # noqa
from youths.tests.factories import YouthProfileFactory


@pytest.fixture
def youth_profile(profile):
    return YouthProfileFactory(profile=profile)
