import datetime
import uuid

from graphql_relay import to_global_id

from open_city_profile.tests.asserts import assert_match_error_code

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


class TestErrorResults:
    def do_error_test(self, user_id, service_client_id, expected_error, gql_client):
        variables = {
            "userId": str(user_id),
            "serviceClientId": service_client_id,
        }

        executed = gql_client.execute(QUERY, variables=variables)

        assert executed["data"] == {"serviceConnectionWithUserId": None}
        assert_match_error_code(executed, expected_error)

    def test_user_is_not_found(self, service_client_id, user_gql_client):
        self.do_error_test(
            uuid.uuid4(),
            service_client_id.client_id,
            "PROFILE_DOES_NOT_EXIST_ERROR",
            user_gql_client,
        )

    def test_profile_is_not_found(self, service_client_id, user, user_gql_client):
        self.do_error_test(
            user.uuid,
            service_client_id.client_id,
            "PROFILE_DOES_NOT_EXIST_ERROR",
            user_gql_client,
        )

    def test_service_is_not_found(self, profile, user_gql_client):
        self.do_error_test(
            profile.user.uuid,
            "unknown-client-id",
            "SERVICE_DOES_NOT_EXIST_ERROR",
            user_gql_client,
        )

    def test_service_connection_is_not_found(
        self, profile, service_client_id, user_gql_client
    ):
        self.do_error_test(
            profile.user.uuid,
            service_client_id.client_id,
            "SERVICE_CONNECTION_DOES_NOT_EXIST_ERROR",
            user_gql_client,
        )
