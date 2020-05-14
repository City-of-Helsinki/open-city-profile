import pytest
from pytest_factoryboy import register

from open_city_profile.tests.conftest import *  # noqa
from profiles.tests.conftest import *  # noqa
from services.tests.factories import AllowedDataFieldFactory, ServiceFactory

# Register factory fixtures
register(ServiceFactory)
register(AllowedDataFieldFactory)


@pytest.fixture
def youth_profile_response():
    return {
        "key": "YOUTHPROFILE",
        "children": [
            {"key": "BIRTH_DATE", "value": "2004-12-08"},
            {"key": "SCHOOL_NAME", "value": "Testikoulu"},
            {"key": "SCHOOL_CLASS", "value": "2B"},
            {"key": "LANGUAGE_AT_HOME", "value": "fi"},
            {"key": "APPROVER_FIRST_NAME", "value": "Teppo"},
            {"key": "APPROVER_LAST_NAME", "value": "Testi"},
            {"key": "APPROVER_PHONE", "value": "0401234567"},
            {"key": "APPROVER_EMAIL", "value": "teppo.testi@example.com"},
            {"key": "EXPIRATION", "value": "2021-08-31 00:00"},
            {"key": "PHOTO_USAGE_APPROVED", "value": False},
        ],
    }
