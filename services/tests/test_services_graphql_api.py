from string import Template

from django.utils.translation import ugettext_lazy as _

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
    service_connection = ServiceConnectionFactory(profile=profile, service=service)

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
                "edges": [
                    {
                        "node": {
                            "service": {"type": service_connection.service.service_type}
                        }
                    }
                ]
            }
        }
    }
    executed = user_gql_client.execute(query, context_value=request)
    assert dict(executed["data"]) == expected_data


def test_normal_user_can_add_service_mutation(rf, user_gql_client):
    request = rf.post("/graphql")
    request.user = user_gql_client.user
    ProfileFactory(user=user_gql_client.user)
    ServiceFactory()

    t = Template(
        """
        mutation {
            addServiceConnection(serviceConnection: { service: { type: ${serviceType} } }) {
                serviceConnection {
                    service {
                        type
                    }
                }
            }
        }
        """
    )
    creation_data = {"serviceType": "BERTH"}
    query = t.substitute(**creation_data)
    expected_data = {
        "addServiceConnection": {"serviceConnection": {"service": {"type": "BERTH"}}}
    }
    executed = user_gql_client.execute(query, context_value=request)
    assert dict(executed["data"]) == expected_data


def test_normal_user_cannot_add_service_multiple_times_mutation(rf, user_gql_client):
    request = rf.post("/graphql")
    request.user = user_gql_client.user
    ProfileFactory(user=user_gql_client.user)
    ServiceFactory()

    t = Template(
        """
        mutation {
            addServiceConnection(serviceConnection: { service: { type: ${serviceType} } }) {
                serviceConnection {
                    service {
                        type
                    }
                }
            }
        }
        """
    )
    creation_data = {"serviceType": "BERTH"}
    query = t.substitute(**creation_data)
    expected_data = {
        "addServiceConnection": {"serviceConnection": {"service": {"type": "BERTH"}}}
    }
    executed = user_gql_client.execute(query, context_value=request)
    assert dict(executed["data"]) == expected_data
    assert "errors" not in executed

    # do the mutation again
    executed = user_gql_client.execute(query, context_value=request)
    assert "errors" in executed
    assert executed["errors"][0]["message"] == _(
        "Service already exists for this profile!"
    )
