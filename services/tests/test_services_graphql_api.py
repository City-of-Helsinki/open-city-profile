from string import Template

from open_city_profile.consts import (
    SERVICE_CONNECTION_ALREADY_EXISTS_ERROR,
    SERVICE_NOT_IDENTIFIED_ERROR,
)
from open_city_profile.tests.asserts import assert_match_error_code
from services.enums import ServiceType
from services.tests.factories import ProfileFactory, ServiceConnectionFactory


def test_normal_user_can_query_own_services(
    rf, user_gql_client, service, allowed_data_field_factory
):
    request = rf.post("/graphql")
    request.user = user_gql_client.user
    profile = ProfileFactory(user=user_gql_client.user)
    first_field = allowed_data_field_factory()
    second_field = allowed_data_field_factory()
    allowed_data_field_factory()
    service.allowed_data_fields.add(first_field)
    service.allowed_data_fields.add(second_field)
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
                                                "fieldName": first_field.field_name,
                                                "label": first_field.label,
                                            }
                                        },
                                        {
                                            "node": {
                                                "fieldName": second_field.field_name,
                                                "label": second_field.label,
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


def test_normal_user_can_add_service(rf, user_gql_client, service):
    request = rf.post("/graphql")
    ProfileFactory(user=user_gql_client.user)
    request.user = user_gql_client.user
    request.service = service

    query = """
        mutation {
            addServiceConnection(input: {
                serviceConnection: {
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

    expected_data = {
        "addServiceConnection": {
            "serviceConnection": {
                "service": {"type": service.service_type.name},
                "enabled": False,
            }
        }
    }
    executed = user_gql_client.execute(query, context=request)
    assert executed["data"] == expected_data


def test_normal_user_can_add_service_using_service_type_input_field(
    rf, user_gql_client, service_factory
):
    request = rf.post("/graphql")
    request.user = user_gql_client.user
    ProfileFactory(user=user_gql_client.user)
    service_berth = service_factory(service_type=ServiceType.BERTH)
    service_youth = service_factory(service_type=ServiceType.YOUTH_MEMBERSHIP)
    request.service = service_factory(service_type=None)

    t = Template(
        """
        mutation {
            add1: addServiceConnection(input: {
                serviceConnection: {
                    service: {
                        type: ${service_type_1}
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

            add2: addServiceConnection(input: {
                serviceConnection: {
                    service: {
                        type: ${service_type_2}
                    }
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
    query = t.substitute(
        service_type_1=service_berth.service_type.name,
        service_type_2=service_youth.service_type.name,
    )
    expected_data = {
        "add1": {
            "serviceConnection": {
                "service": {"type": service_berth.service_type.name},
                "enabled": False,
            }
        },
        "add2": {
            "serviceConnection": {
                "service": {"type": service_youth.service_type.name},
                "enabled": True,
            }
        },
    }
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data


def test_normal_user_cannot_add_service_multiple_times_mutation(
    rf, user_gql_client, service
):
    request = rf.post("/graphql")
    request.user = user_gql_client.user
    ProfileFactory(user=user_gql_client.user)
    request.service = service

    query = """
        mutation {
            addServiceConnection(input: {
                serviceConnection: {
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


def test_not_identifying_service_for_add_service_connection_produces_service_not_identified_error(
    rf, user_gql_client
):
    ProfileFactory(user=user_gql_client.user)
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    query = """
        mutation {
            addServiceConnection(input: {
                serviceConnection: {
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

    executed = user_gql_client.execute(query, context=request)

    assert_match_error_code(executed, SERVICE_NOT_IDENTIFIED_ERROR)


def test_normal_user_can_query_own_services_gdpr_api_scopes(
    rf, user_gql_client, service_factory,
):
    query_scope = "query_scope"
    delete_scope = "delete_scope"
    service = service_factory(
        gdpr_query_scope=query_scope, gdpr_delete_scope=delete_scope
    )
    request = rf.post("/graphql")
    request.user = user_gql_client.user
    profile = ProfileFactory(user=user_gql_client.user)

    ServiceConnectionFactory(profile=profile, service=service)

    query = """
        {
            myProfile {
                serviceConnections {
                    edges {
                        node {
                            service {
                                type
                                gdprQueryScope
                                gdprDeleteScope
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
                                "type": service.service_type.name,
                                "gdprQueryScope": query_scope,
                                "gdprDeleteScope": delete_scope,
                            }
                        }
                    }
                ]
            }
        }
    }
    executed = user_gql_client.execute(query, context=request)

    assert dict(executed["data"]) == expected_data
