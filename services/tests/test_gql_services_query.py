from services.models import Service

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


def test_can_query_all_services(service_factory, anon_user_gql_client):
    service_factory.create_batch(3)
    # Get services via the model so that they are in the default order
    services = Service.objects.all()

    expected_service_edges = [{"node": {"name": s.name}} for s in services]

    executed = anon_user_gql_client.execute(QUERY, service=None)

    assert "errors" not in executed
    assert executed["data"] == {"services": {"edges": expected_service_edges}}


def test_can_filter_according_to_exact_client_id_of_service(
    service_client_id_factory, anon_user_gql_client
):
    service_client_id_factory(client_id="does-not-match")
    matching_service = service_client_id_factory(client_id="client-id-matches").service
    service_client_id_factory(client_id="also-does-not-match")

    # Exact match returns a result
    variables = {"clientId": "client-id-matches"}
    executed = anon_user_gql_client.execute(QUERY, variables=variables, service=None)

    assert "errors" not in executed
    assert executed["data"] == {
        "services": {"edges": [{"node": {"name": matching_service.name}}]}
    }

    # Partial match does not return anything
    variables = {"clientId": "does-not"}
    executed = anon_user_gql_client.execute(QUERY, variables=variables, service=None)

    assert "errors" not in executed
    assert executed["data"] == {"services": {"edges": []}}