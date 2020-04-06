import factory
from subscriptions.models import SubscriptionType, SubscriptionTypeCategory


class SubscriptionTypeCategoryFactory(factory.django.DjangoModelFactory):
    code = "TEST_NOTIFICATION_CATEGORY"
    label = "Test notification category"

    class Meta:
        model = SubscriptionTypeCategory


class SubscriptionTypeFactory(factory.django.DjangoModelFactory):
    code = "TEST_NOTIFICATION"
    label = "Test notification"

    class Meta:
        model = SubscriptionType
