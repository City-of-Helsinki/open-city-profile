from subscriptions.tests.factories import (
    SubscriptionTypeCategoryFactory,
    SubscriptionTypeFactory,
)


def test_normal_user_can_query_subscription_types_grouped_by_categories(
    rf, user_gql_client
):
    cat = SubscriptionTypeCategoryFactory(code="TEST-CATEGORY-1")
    type_1 = SubscriptionTypeFactory(subscription_type_category=cat, code="TEST-1")
    type_2 = SubscriptionTypeFactory(subscription_type_category=cat, code="TEST-2")
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    query = """
        query {
            subscriptionTypeCategories {
                edges {
                    node {
                        order
                        code
                        label
                        subscriptionTypes {
                            edges {
                                node {
                                    order
                                    code
                                    label
                                }
                            }
                        }
                    }
                }
            }
        }
    """
    expected_data = {
        "subscriptionTypeCategories": {
            "edges": [
                {
                    "node": {
                        "order": 1,
                        "code": cat.code,
                        "label": cat.label,
                        "subscriptionTypes": {
                            "edges": [
                                {
                                    "node": {
                                        "order": 1,
                                        "code": type_1.code,
                                        "label": type_1.label,
                                    }
                                },
                                {
                                    "node": {
                                        "order": 2,
                                        "code": type_2.code,
                                        "label": type_2.label,
                                    }
                                },
                            ]
                        },
                    }
                }
            ]
        }
    }
    executed = user_gql_client.execute(query, context=request)
    assert "errors" not in executed
    assert dict(executed["data"]) == expected_data
