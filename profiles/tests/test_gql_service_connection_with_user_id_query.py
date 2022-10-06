import datetime

from graphql_relay import to_global_id

QUERY = """
    query ($userId: UUID!, $serviceClientId: String!)
    {
        serviceConnectionWithUserId(
            userId: $userId, serviceClientId: $serviceClientId
        ) {
            id
            createdAt
            enabled
            service {
                id
                name
                title
                description
                createdAt
                gdprUrl
                gdprQueryScope
                gdprDeleteScope
            }
        }
    }
"""


def assert_datetimes_equal(datetime_str, datetime_instance):
    assert datetime.datetime.fromisoformat(datetime_str) == datetime_instance


def test_existing_service_connection_is_returned(
    profile, service_client_id, service_connection_factory, user_gql_client
):
    service = service_client_id.service
    service_connection = service_connection_factory(profile=profile, service=service)

    variables = {
        "userId": str(profile.user.uuid),
        "serviceClientId": service_client_id.client_id,
    }

    executed = user_gql_client.execute(QUERY, variables=variables)

    assert "errors" not in executed

    returned_data = executed.get("data", {}).get("serviceConnectionWithUserId", {})
    returned_service_connection_created_at = returned_data.pop("createdAt", "")
    returned_service_created_at = returned_data.get("service", {}).pop("createdAt", "")

    assert executed["data"] == {
        "serviceConnectionWithUserId": {
            "id": to_global_id("ServiceConnectionType", service_connection.id),
            "enabled": True,
            "service": {
                "id": to_global_id("ServiceNode", service.id),
                "name": service.name,
                "title": service.title,
                "description": service.description,
                "gdprUrl": service.gdpr_url,
                "gdprQueryScope": service.gdpr_query_scope,
                "gdprDeleteScope": service.gdpr_delete_scope,
            },
        }
    }

    assert_datetimes_equal(
        returned_service_connection_created_at, service_connection.created_at
    )
    assert_datetimes_equal(returned_service_created_at, service.created_at)
