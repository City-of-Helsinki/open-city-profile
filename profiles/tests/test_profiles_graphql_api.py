import uuid
from string import Template

from open_city_profile.consts import PROFILE_DOES_NOT_EXIST_ERROR, TOKEN_EXPIRED_ERROR

from .conftest import TemporaryProfileReadAccessTokenTestBase
from .factories import ProfileFactory, TemporaryReadAccessTokenFactory


def test_profile_node_exposes_key_for_federation_gateway(rf, anon_user_gql_client):
    request = rf.post("/graphql")

    query = """
        query {
            _service {
                sdl
            }
        }
    """

    executed = anon_user_gql_client.execute(query, context=request)
    assert (
        'type ProfileNode implements Node  @key(fields: "id")'
        in executed["data"]["_service"]["sdl"]
    )


def test_profile_connection_schema_matches_federated_schema(rf, anon_user_gql_client):
    request = rf.post("/graphql")

    query = """
        query {
            _service {
                sdl
            }
        }
    """

    executed = anon_user_gql_client.execute(query, context=request)
    assert (
        "type ProfileNodeConnection {   pageInfo: PageInfo!   "
        "edges: [ProfileNodeEdge]!   count: Int!   totalCount: Int! }"
        in executed["data"]["_service"]["sdl"]
    )


class TestTemporaryProfileReadAccessToken(TemporaryProfileReadAccessTokenTestBase):
    def query(self, token):
        return Template(
            """
            {
                profileWithAccessToken(token: "${token}") {
                    firstName
                    lastName
                }
            }
        """
        ).substitute(token=token)

    def test_anonymous_user_can_retrieve_a_profile_with_temporary_read_access_token(
        self, rf, user_gql_client, anon_user_gql_client
    ):
        profile = ProfileFactory(user=user_gql_client.user)
        token = TemporaryReadAccessTokenFactory(profile=profile)

        request = rf.post("/graphql")
        request.user = anon_user_gql_client.user

        executed = anon_user_gql_client.execute(
            self.query(token.token), context=request
        )

        assert "errors" not in executed
        actual_profile = executed["data"]["profileWithAccessToken"]
        assert actual_profile == {
            "firstName": profile.first_name,
            "lastName": profile.last_name,
        }

    def test_only_a_limited_set_of_fields_is_returned_from_the_profile(
        self, gql_schema
    ):
        query_type = gql_schema.get_query_type()
        operation = query_type.fields["profileWithAccessToken"]
        return_type = operation.type
        return_fields = return_type.fields.keys()
        assert set(return_fields) == set(
            [
                "firstName",
                "lastName",
                "nickname",
                "image",
                "language",
                "id",
                "primaryEmail",
                "primaryPhone",
                "primaryAddress",
                "emails",
                "phones",
                "addresses",
                "contactMethod",
            ]
        )

    def test_using_non_existing_token_reports_profile_not_found_error(
        self, rf, user_gql_client, anon_user_gql_client
    ):
        request = rf.post("/graphql")
        request.user = anon_user_gql_client.user

        executed = anon_user_gql_client.execute(
            self.query(uuid.uuid4()), context=request
        )

        assert (
            executed["errors"][0]["extensions"]["code"] == PROFILE_DOES_NOT_EXIST_ERROR
        )

    def test_using_an_expired_token_reports_token_expired_error(
        self, rf, user_gql_client, anon_user_gql_client
    ):
        profile = ProfileFactory(user=user_gql_client.user)
        token = self.create_expired_token(profile)

        request = rf.post("/graphql")
        request.user = anon_user_gql_client.user

        executed = anon_user_gql_client.execute(
            self.query(token.token), context=request
        )

        assert executed["errors"][0]["extensions"]["code"] == TOKEN_EXPIRED_ERROR
