import pytest

from open_city_profile.consts import (
    SERVICE_CONNECTION_ALREADY_EXISTS_ERROR,
    SERVICE_NOT_IDENTIFIED_ERROR,
)
from open_city_profile.tests.asserts import assert_match_error_code
from services.enums import ServiceType
from services.tests.factories import ProfileFactory, ServiceConnectionFactory


@pytest.mark.parametrize("service__service_type", [ServiceType.BERTH])
def test_normal_user_can_query_own_services(
    user_gql_client, service, allowed_data_field_factory
):
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
                                name
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
                                "type": service.service_type.name,
                                "name": service.name,
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
    executed = user_gql_client.execute(query)
    assert executed["data"] == expected_data


@pytest.mark.parametrize("service__service_type", [ServiceType.BERTH])
def test_normal_user_can_add_service(user_gql_client, service):
    ProfileFactory(user=user_gql_client.user)

    # service object with type is included in query just to ensure that it has NO affect
    query = """
        mutation {
            addServiceConnection(input: {
                serviceConnection: {
                    service: {
                        type: GODCHILDREN_OF_CULTURE
                    }
                    enabled: false
                }
            }) {
                serviceConnection {
                    service {
                        type
                        name
                    }
                    enabled
                }
            }
        }
    """

    expected_data = {
        "addServiceConnection": {
            "serviceConnection": {
                "service": {"type": service.service_type.name, "name": service.name},
                "enabled": False,
            }
        }
    }
    executed = user_gql_client.execute(query, service=service)
    assert executed["data"] == expected_data


@pytest.mark.parametrize("service__service_type", [ServiceType.BERTH])
def test_normal_user_cannot_add_service_multiple_times_mutation(
    user_gql_client, service
):
    ProfileFactory(user=user_gql_client.user)

    query = """
        mutation {
            addServiceConnection(input: {
                serviceConnection: {
                }
            }) {
                serviceConnection {
                    service {
                        type
                        name
                    }
                }
            }
        }
    """

    expected_data = {
        "addServiceConnection": {
            "serviceConnection": {
                "service": {"type": service.service_type.name, "name": service.name}
            }
        }
    }
    executed = user_gql_client.execute(query, service=service)
    assert dict(executed["data"]) == expected_data
    assert "errors" not in executed

    # do the mutation again
    executed = user_gql_client.execute(query, service=service)
    assert "errors" in executed
    assert "code" in executed["errors"][0]["extensions"]
    assert (
        executed["errors"][0]["extensions"]["code"]
        == SERVICE_CONNECTION_ALREADY_EXISTS_ERROR
    )


def test_not_identifying_service_for_add_service_connection_produces_service_not_identified_error(
    user_gql_client,
):
    ProfileFactory(user=user_gql_client.user)

    query = """
        mutation {
            addServiceConnection(input: {
                serviceConnection: {
                }
            }) {
                serviceConnection {
                    service {
                        type
                        name
                    }
                }
            }
        }
    """

    executed = user_gql_client.execute(query, service=None)

    assert_match_error_code(executed, SERVICE_NOT_IDENTIFIED_ERROR)


def test_normal_user_can_query_own_services_gdpr_api_scopes(
    user_gql_client, service_factory,
):
    query_scope = "query_scope"
    delete_scope = "delete_scope"
    service = service_factory(
        service_type=ServiceType.BERTH,
        gdpr_query_scope=query_scope,
        gdpr_delete_scope=delete_scope,
    )
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
                                name
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
                                "name": service.name,
                                "gdprQueryScope": query_scope,
                                "gdprDeleteScope": delete_scope,
                            }
                        }
                    }
                ]
            }
        }
    }
    executed = user_gql_client.execute(query)

    assert dict(executed["data"]) == expected_data
