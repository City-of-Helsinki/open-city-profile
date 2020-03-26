from string import Template

from open_city_profile.consts import SERVICE_CONNECTION_ALREADY_EXISTS_ERROR
from services.enums import ServiceType
from services.tests.factories import (
    AllowedDataFieldFactory,
    ProfileFactory,
    ServiceConnectionFactory,
    ServiceFactory,
)


def test_normal_user_can_query_own_services(rf, user_gql_client):
    request = rf.post("/graphql")
    request.user = user_gql_client.user
    profile = ProfileFactory(user=user_gql_client.user)
    name_field = AllowedDataFieldFactory(field_name="name", label="Name")
    address_field = AllowedDataFieldFactory(field_name="address", label="Address")
    AllowedDataFieldFactory(field_name="ssn", label="SSN")
    service = ServiceFactory()
    service.allowed_data_fields.add(name_field)
    service.allowed_data_fields.add(address_field)
    ServiceConnectionFactory(profile=profile, service=service)

    query = """
        {
            myProfile {
                serviceConnections {
                    edges {
                        node {
                            service {
                                type
                                title
                                description
                                allowedDataFields {
                                    edges {
                                        node {
                                            fieldName
                                            label
                                        }
                                    }
                                }
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
                            "service": {
                                "type": ServiceType.BERTH.name,
                                "title": service.title,
                                "description": service.description,
                                "allowedDataFields": {
                                    "edges": [
                                        {
                                            "node": {
                                                "fieldName": name_field.field_name,
                                                "label": name_field.label,
                                            }
                                        },
                                        {
                                            "node": {
                                                "fieldName": address_field.field_name,
                                                "label": address_field.label,
                                            }
                                        },
                                    ]
                                },
                            }
                        }
                    }
                ]
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
            addServiceConnection(input: {
                serviceConnection: {
                    service: {
                        type: ${service_type}
                    }
                    enabled: false
                }
            }) {
                serviceConnection {
                    service {
                        type
                    }
                    enabled
                }
            }
        }
    """
    )
    query = t.substitute(service_type=ServiceType.BERTH.name)
    expected_data = {
        "addServiceConnection": {
            "serviceConnection": {
                "service": {"type": ServiceType.BERTH.name},
                "enabled": False,
            }
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
            addServiceConnection(input: {
                serviceConnection: {
                    service: {
                        type: ${service_type}
                    }
                }
            }) {
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
