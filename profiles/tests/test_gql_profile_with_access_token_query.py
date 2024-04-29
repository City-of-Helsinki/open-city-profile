import uuid
from string import Template

from open_city_profile.consts import PROFILE_DOES_NOT_EXIST_ERROR, TOKEN_EXPIRED_ERROR

from .conftest import TemporaryProfileReadAccessTokenTestBase
from .factories import ProfileFactory, TemporaryReadAccessTokenFactory


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
        self, anon_user_gql_client
    ):
        profile = ProfileFactory()
        token = TemporaryReadAccessTokenFactory(profile=profile)

        executed = anon_user_gql_client.execute(
            self.query(token.token), allowed_data_fields=["name"]
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
        query_type = gql_schema.query_type
        operation = query_type.fields["profileWithAccessToken"]
        return_type = operation.type
        return_fields = return_type.fields.keys()
        assert set(return_fields) == {
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
        }

    def test_using_non_existing_token_reports_profile_not_found_error(
        self, anon_user_gql_client
    ):
        executed = anon_user_gql_client.execute(self.query(uuid.uuid4()))

        assert (
            executed["errors"][0]["extensions"]["code"] == PROFILE_DOES_NOT_EXIST_ERROR
        )

    def test_using_an_expired_token_reports_token_expired_error(
        self, anon_user_gql_client
    ):
        profile = ProfileFactory()
        token = self.create_expired_token(profile)

        executed = anon_user_gql_client.execute(self.query(token.token))

        assert executed["errors"][0]["extensions"]["code"] == TOKEN_EXPIRED_ERROR
