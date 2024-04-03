import pytest
from guardian.shortcuts import assign_perm

from open_city_profile import settings
from open_city_profile.tests.asserts import assert_match_error_code
from services.models import Service

from .factories import ServiceFactory

QUERY = """
    query Services($clientId: String = "") {
        services(clientId: $clientId) {
            edges {
                node {
                    name
                }
            }
        }
    }
"""


def test_can_query_all_services(service_factory, user_gql_client):
    service_factory.create_batch(3)
    # Get services via the model so that they are in the default order
    services = Service.objects.all()

    assign_perm("services.view_service", user_gql_client.user)

    expected_service_edges = [{"node": {"name": s.name}} for s in services]

    executed = user_gql_client.execute(QUERY, service=None)

    assert "errors" not in executed
    assert executed["data"] == {"services": {"edges": expected_service_edges}}


def test_can_filter_according_to_exact_client_id_of_service(
    service_client_id_factory, user_gql_client
):
    service_client_id_factory(client_id="does-not-match")
    matching_service = service_client_id_factory(client_id="client-id-matches").service
    service_client_id_factory(client_id="also-does-not-match")

    assign_perm("services.view_service", user_gql_client.user)

    # Exact match returns a result
    variables = {"clientId": "client-id-matches"}
    executed = user_gql_client.execute(QUERY, variables=variables, service=None)

    assert "errors" not in executed
    assert executed["data"] == {
        "services": {"edges": [{"node": {"name": matching_service.name}}]}
    }

    # Partial match does not return anything
    variables = {"clientId": "does-not"}
    executed = user_gql_client.execute(QUERY, variables=variables, service=None)

    assert "errors" not in executed
    assert executed["data"] == {"services": {"edges": []}}


def test_services_require_service_connections_except_profile_service(user_gql_client):
    profile_service = ServiceFactory(name="profile-service", is_profile_service=True)
    ServiceFactory(name="regular-service", is_profile_service=False)

    query = """
        query {
            services {
                edges {
                    node {
                        name
                        requiresServiceConnection
                    }
                }
            }
        }
    """

    # Get services via the model so that they are in the default order
    services = Service.objects.all()

    assign_perm("services.view_service", user_gql_client.user)

    expected_service_edges = [
        {"node": {"name": s.name, "requiresServiceConnection": s != profile_service}}
        for s in services
    ]

    executed = user_gql_client.execute(query, service=None)

    assert "errors" not in executed
    assert executed["data"] == {"services": {"edges": expected_service_edges}}


def test_requires_view_service_permission(user_gql_client):
    executed = user_gql_client.execute(QUERY)

    assert executed["data"] == {"services": None}
    assert_match_error_code(executed, "PERMISSION_DENIED_ERROR")


@pytest.mark.parametrize("language", dict(settings.LANGUAGES).keys())
def test_query_service_terms_of_use_url(user_gql_client, language):
    terms_of_use_url = f"https://example.com/terms-of-use/{language}/"
    service = ServiceFactory()
    service.set_current_language(language)
    service.terms_of_use_url = terms_of_use_url
    service.save()
    service.set_current_language("fr")

    assign_perm("services.view_service", user_gql_client.user)
    query = (
        """
        query {
            services {
                edges {
                    node {
                        name
                        termsOfUseUrl(language: %s)
                    }
                }
            }
        }
    """
        % language.upper()
    )

    executed = user_gql_client.execute(query, service=None)

    assert executed["data"] == {
        "services": {
            "edges": [
                {
                    "node": {
                        "name": service.name,
                        "termsOfUseUrl": terms_of_use_url,
                    }
                }
            ]
        }
    }

    assert "errors" not in executed
