from pytest_factoryboy import register

from open_city_profile.tests.conftest import *  # noqa
from profiles.tests.conftest import *  # noqa
from services.tests.factories import AllowedDataFieldFactory, ServiceFactory

# Register factory fixtures
register(ServiceFactory)
register(AllowedDataFieldFactory)
