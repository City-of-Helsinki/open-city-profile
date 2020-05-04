import pytest
from django.apps import apps

from subscriptions.models import (
    Subscription,
    SubscriptionType,
    SubscriptionTypeCategory,
)
from subscriptions.tests.factories import SubscriptionFactory
from subscriptions.utils import generate_subscription_types


@pytest.mark.parametrize("times", [1, 2])
def test_generate_subscription_types(times):
    SubscriptionTypeCategoryTranslation = apps.get_model(  # noqa: N806
        "subscriptions", "SubscriptionTypeCategoryTranslation"
    )
    SubscriptionTypeTranslation = apps.get_model(  # noqa: N806
        "subscriptions", "SubscriptionTypeTranslation"
    )

    for i in range(times):
        generate_subscription_types()
        st = SubscriptionType.objects.first()
        # subscription should not get deleted when types are re-generated
        SubscriptionFactory(subscription_type=st)

    assert Subscription.objects.count() == times
    assert SubscriptionType.objects.count() == 3
    assert SubscriptionTypeTranslation.objects.count() == 9
    assert SubscriptionTypeCategory.objects.count() == 2
    assert SubscriptionTypeCategoryTranslation.objects.count() == 6
