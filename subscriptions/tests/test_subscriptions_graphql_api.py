def test_normal_user_can_query_subscription_types_grouped_by_categories(  # noqa: E302
    user_gql_client, subscription_type_factory, subscription_type_category
):
    type_1 = subscription_type_factory(
        subscription_type_category=subscription_type_category
    )
    type_2 = subscription_type_factory(
        subscription_type_category=subscription_type_category
    )

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
                        "code": subscription_type_category.code,
                        "label": subscription_type_category.label,
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
    executed = user_gql_client.execute(query)
    assert "errors" not in executed
    assert dict(executed["data"]) == expected_data
