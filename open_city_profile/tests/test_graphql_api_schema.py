import pytest
import requests
from graphql import get_introspection_query, print_schema


def test_graphql_schema_matches_the_reference(gql_schema, snapshot):
    actual_schema = print_schema(gql_schema)

    snapshot.assert_match(actual_schema)


@pytest.mark.parametrize("enabled", [True, False])
def test_graphql_schema_introspection_can_be_disabled(live_server, settings, enabled):
    settings.ENABLE_GRAPHQL_INTROSPECTION = enabled
    url = live_server.url + "/graphql/"
    payload = {
        "query": get_introspection_query(),
    }

    response = requests.post(url, json=payload)

    body = response.json()
    if enabled:
        assert response.status_code == 200
        assert "errors" not in body
        assert "__schema" in body["data"]
    else:
        assert response.status_code == 400
        assert "data" not in body
        error = body["errors"][0]["message"]
        assert "__schema" in error
        assert "introspection is disabled" in error
