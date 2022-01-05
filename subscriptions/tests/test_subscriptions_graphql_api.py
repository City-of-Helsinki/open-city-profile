def test_querying_subscription_type_categories_returns_an_empty_result(user_gql_client):
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
    expected_data = {"subscriptionTypeCategories": {"edges": []}}
    executed = user_gql_client.execute(query)
    assert "errors" not in executed
    assert dict(executed["data"]) == expected_data
