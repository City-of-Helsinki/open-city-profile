from pytest_factoryboy import register

from open_city_profile.tests.conftest import *  # noqa
from subscriptions.tests.factories import (
    SubscriptionFactory,
    SubscriptionTypeCategoryFactory,
    SubscriptionTypeFactory,
)

# Register factory fixtures
register(SubscriptionTypeCategoryFactory)
register(SubscriptionTypeFactory)
register(SubscriptionFactory)
