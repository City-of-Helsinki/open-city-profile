from string import Template

from open_city_profile.consts import SERVICE_CONNECTION_ALREADY_EXISTS_ERROR
from services.enums import ServiceType
from services.tests.factories import (
    ProfileFactory,
    ServiceConnectionFactory,
    ServiceFactory,
)


def test_normal_user_can_query_own_services(rf, user_gql_client):
    request = rf.post("/graphql")
    request.user = user_gql_client.user
    profile = ProfileFactory(user=user_gql_client.user)
    service = ServiceFactory()
    ServiceConnectionFactory(profile=profile, service=service)

    query = """
        {
            myProfile {
                serviceConnections {
                    edges {
                        node {
                            service {
                                type
                            }
                        }
                    }
                }
            }
        }
    """
    expected_data = {
        "myProfile": {
            "serviceConnections": {
                "edges": [{"node": {"service": {"type": ServiceType.BERTH.name}}}]
            }
        }
    }
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data


def test_normal_user_can_add_service_mutation(rf, user_gql_client):
    request = rf.post("/graphql")
    request.user = user_gql_client.user
    ProfileFactory(user=user_gql_client.user)
    ServiceFactory()

    t = Template(
        """
        mutation {
            addServiceConnection(serviceConnection: { service: { type: ${service_type} } }) {
                serviceConnection {
                    service {
                        type
                    }
                }
            }
        }
    """
    )
    query = t.substitute(service_type=ServiceType.BERTH.name)
    expected_data = {
        "addServiceConnection": {
            "serviceConnection": {"service": {"type": ServiceType.BERTH.name}}
        }
    }
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data


def test_normal_user_cannot_add_service_multiple_times_mutation(rf, user_gql_client):
    request = rf.post("/graphql")
    request.user = user_gql_client.user
    ProfileFactory(user=user_gql_client.user)
    ServiceFactory()

    t = Template(
        """
        mutation {
            addServiceConnection(serviceConnection: { service: { type: ${service_type} } }) {
                serviceConnection {
                    service {
                        type
                    }
                }
            }
        }
    """
    )
    query = t.substitute(service_type=ServiceType.BERTH.name)
    expected_data = {
        "addServiceConnection": {
            "serviceConnection": {"service": {"type": ServiceType.BERTH.name}}
        }
    }
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data
    assert "errors" not in executed

    # do the mutation again
    executed = user_gql_client.execute(query, context=request)
    assert "errors" in executed
    assert "code" in executed["errors"][0]["extensions"]
    assert (
        executed["errors"][0]["extensions"]["code"]
        == SERVICE_CONNECTION_ALREADY_EXISTS_ERROR
    )
