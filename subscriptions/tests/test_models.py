from subscriptions.models import (
    Subscription,
    SubscriptionType,
    SubscriptionTypeCategory,
)


def test_subscription_type_category(subscription_type_category_factory):
    subscription_type_category_factory()

    assert SubscriptionTypeCategory.objects.count() == 1


def test_subscription_type(subscription_type_factory):
    subscription_type_factory()

    assert SubscriptionTypeCategory.objects.count() == 1
    assert SubscriptionType.objects.count() == 1


def test_subscription(subscription_factory):
    subscription_factory()

    assert SubscriptionTypeCategory.objects.count() == 1
    assert SubscriptionType.objects.count() == 1
    assert Subscription.objects.count() == 1


def test_subscription_type_category_auto_orders(subscription_type_category_factory):
    cat_1 = subscription_type_category_factory()
    cat_2 = subscription_type_category_factory()
    assert cat_1.order == 1
    assert cat_2.order == 2


def test_subscription_type_auto_orders(
    subscription_type_category, subscription_type_factory
):
    type_1 = subscription_type_factory(
        subscription_type_category=subscription_type_category
    )
    type_2 = subscription_type_factory(
        subscription_type_category=subscription_type_category
    )
    assert type_1.order == 1
    assert type_2.order == 2
