import pytest
from graphql import get_introspection_query

from open_city_profile.tests.graphql_test_helpers import (
    do_graphql_call,
    do_graphql_call_as_user,
)


@pytest.mark.parametrize(
    "enabled, expected_status",
    [pytest.param(True, 200, id="enabled"), pytest.param(False, 400, id="disabled")],
)
def test_graphql_schema_introspection_can_be_disabled(
    live_server, settings, enabled, expected_status
):
    settings.ENABLE_GRAPHQL_INTROSPECTION = enabled

    data, errors = do_graphql_call(
        live_server, query=get_introspection_query(), expected_status=expected_status
    )

    if enabled:
        assert errors is None
        assert "__schema" in data
    else:
        assert data is None
        error = errors[0]["message"]
        assert "__schema" in error
        assert "introspection is disabled" in error


@pytest.mark.parametrize(
    "depth_limit, expected_status, success",
    [
        pytest.param(4, 200, True, id="within-limit"),
        pytest.param(3, 400, False, id="over-limit"),
    ],
)
def test_graphql_query_depth_can_be_limited(
    live_server, settings, user, depth_limit, expected_status, success
):
    settings.GRAPHQL_QUERY_DEPTH_LIMIT = depth_limit
    query = """
        {
            myProfile {
                emails {
                    edges {
                        node {
                            id
                        }
                    }
                }
            }
        }
    """

    data, errors = do_graphql_call_as_user(
        live_server, user, query=query, expected_status=expected_status
    )

    if success:
        assert errors is None
        assert "myProfile" in data
    else:
        assert data is None
        error = errors[0]["message"]
        assert "exceeds maximum operation depth" in error
