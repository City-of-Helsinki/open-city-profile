from services.models import Service

QUERY = """
    query {
        services {
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
