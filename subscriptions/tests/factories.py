import factory
from subscriptions.models import (
    Subscription,
    SubscriptionType,
    SubscriptionTypeCategory,
)

from profiles.tests.factories import ProfileFactory


class SubscriptionTypeCategoryFactory(factory.django.DjangoModelFactory):
    code = factory.Sequence(lambda n: "TEST_NOTIFICATION_CATEGORY_%d" % n)
    label = "Test notification category"

    class Meta:
        model = SubscriptionTypeCategory


class SubscriptionTypeFactory(factory.django.DjangoModelFactory):
    code = factory.Sequence(lambda n: "TEST_NOTIFICATION_%d" % n)
    label = "Test notification"
    subscription_type_category = factory.SubFactory(SubscriptionTypeCategoryFactory)

    class Meta:
        model = SubscriptionType


class SubscriptionFactory(factory.django.DjangoModelFactory):
    profile = factory.SubFactory(ProfileFactory)
    subscription_type = factory.SubFactory(SubscriptionTypeFactory)

    class Meta:
        model = Subscription
