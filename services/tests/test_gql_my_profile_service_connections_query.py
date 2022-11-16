from string import Template

import pytest
from django.conf import settings

from open_city_profile.graphene import TranslationLanguage
from open_city_profile.tests.graphql_test_helpers import do_graphql_call_as_user
from services.enums import ServiceType
from services.tests.factories import ProfileFactory, ServiceConnectionFactory

SERVICE_CONNECTIONS_QUERY = """
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
    executed = user_gql_client.execute(SERVICE_CONNECTIONS_QUERY)
    assert executed["data"] == expected_data


def test_profile_service_is_not_returned_in_service_connections(
    profile_service, user_gql_client
):
    profile = ProfileFactory(user=user_gql_client.user)
    ServiceConnectionFactory(profile=profile, service=profile_service)

    expected_data = {"myProfile": {"serviceConnections": {"edges": []}}}

    executed = user_gql_client.execute(
        SERVICE_CONNECTIONS_QUERY, service=profile_service
    )
    assert executed["data"] == expected_data


def test_service_connections_of_service_always_returns_an_empty_result(
    user_gql_client, service
):
    profile = ProfileFactory(user=user_gql_client.user)
    ServiceConnectionFactory(profile=profile, service=service)

    for p in ProfileFactory.create_batch(3):
        ServiceConnectionFactory(profile=p, service=service)

    query = """
        {
            myProfile {
                serviceConnections {
                    edges {
                        node {
                            service {
                                serviceconnectionSet {
                                    edges {
                                        node {
                                            id
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
                    {"node": {"service": {"serviceconnectionSet": {"edges": []}}}}
                ]
            }
        }
    }
    executed = user_gql_client.execute(query)
    assert executed["data"] == expected_data


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


def _set_service_title_and_description(service):
    service.set_current_language("fi")
    service.title = "Service title in finnish"
    service.description = "Service description in finnish"
    service.save()

    service.set_current_language("en")
    service.title = "Service title in english"
    service.description = "Service description in english"
    service.save()


@pytest.mark.parametrize("language", ["EN", "FI"])
def test_service_title_translation(user_gql_client, service, language):
    profile = ProfileFactory(user=user_gql_client.user)
    _set_service_title_and_description(service)
    ServiceConnectionFactory(profile=profile, service=service)

    t = Template(
        """
        query TestQuery {
            myProfile {
                serviceConnections {
                    edges {
                        node {
                            service {
                                title_translated: title(language:${language})
                                description
                            }
                        }
                    }
                }
            }
        }
        """
    )

    query = t.substitute({"language": language})

    executed = user_gql_client.execute(query, service=service)

    expected_title = service.safe_translation_getter(
        "title", language_code=getattr(TranslationLanguage, language).value
    )
    expected_description = service.safe_translation_getter(
        "description", language_code=settings.LANGUAGE_CODE
    )

    expected_data = {
        "myProfile": {
            "serviceConnections": {
                "edges": [
                    {
                        "node": {
                            "service": {
                                "title_translated": expected_title,
                                "description": expected_description,
                            },
                        }
                    }
                ]
            }
        }
    }

    assert executed["data"] == expected_data


def test_language_argument_overrides_header_language(
    live_server, profile, service_client_id
):
    service = service_client_id.service
    _set_service_title_and_description(service)
    ServiceConnectionFactory(profile=profile, service=service)
    user = profile.user

    query = """
        {
            myProfile {
                serviceConnections {
                    edges {
                        node {
                            service {
                                title(language: EN)
                                description
                            }
                        }
                    }
                }
            }
        }
    """

    result_data, errors = do_graphql_call_as_user(
        live_server,
        user,
        service=service,
        query=query,
        extra_request_args={"headers": {"Accept-Language": "fi"}},
    )

    assert not errors, errors

    expected_title = service.safe_translation_getter("title", language_code="en")
    expected_description = service.safe_translation_getter(
        "description", language_code="fi"
    )

    expected_data = {
        "myProfile": {
            "serviceConnections": {
                "edges": [
                    {
                        "node": {
                            "service": {
                                "title": expected_title,
                                "description": expected_description,
                            },
                        }
                    }
                ]
            }
        }
    }

    assert result_data == expected_data
