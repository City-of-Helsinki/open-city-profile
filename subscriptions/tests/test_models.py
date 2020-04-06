from subscriptions.tests.factories import (
    SubscriptionTypeCategoryFactory,
    SubscriptionTypeFactory,
)


def test_subscription_type_category_auto_orders():
    cat_1 = SubscriptionTypeCategoryFactory(code="TEST-CATEGORY-1")
    cat_2 = SubscriptionTypeCategoryFactory(code="TEST-CATEGORY-2")
    assert cat_1.order == 1
    assert cat_2.order == 2


def test_subscription_type_auto_orders():
    cat = SubscriptionTypeCategoryFactory(code="TEST-CATEGORY-1")
    type_1 = SubscriptionTypeFactory(subscription_type_category=cat, code="TEST-1")
    type_2 = SubscriptionTypeFactory(subscription_type_category=cat, code="TEST-2")
    assert type_1.order == 1
    assert type_2.order == 2
