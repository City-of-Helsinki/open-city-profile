from pytest_factoryboy import register

from open_city_profile.tests.conftest import *  # noqa
from services.tests.factories import ServiceFactory

# Register factory fixtures
register(ServiceFactory)
