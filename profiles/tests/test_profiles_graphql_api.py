import uuid
from datetime import datetime, timedelta
from string import Template

from django.utils import timezone
from graphql_relay.node.node import to_global_id

from open_city_profile.consts import (
    API_NOT_IMPLEMENTED_ERROR,
    PERMISSION_DENIED_ERROR,
    PROFILE_DOES_NOT_EXIST_ERROR,
    TOKEN_EXPIRED_ERROR,
)
from open_city_profile.tests.asserts import assert_almost_equal
from profiles.models import (
    _default_temporary_read_access_token_validity_duration,
    TemporaryReadAccessToken,
)

from .factories import (
    ClaimTokenFactory,
    ProfileFactory,
    ProfileWithPrimaryEmailFactory,
    TemporaryReadAccessTokenFactory,
)


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


def test_can_query_claimable_profile_with_token(rf, user_gql_client):
    profile = ProfileFactory(user=None, first_name="John", last_name="Doe")
    claim_token = ClaimTokenFactory(profile=profile)
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    t = Template(
        """
        {
            claimableProfile(token: "${claimToken}") {
                id
                firstName
                lastName
            }
        }
        """
    )
    query = t.substitute(claimToken=claim_token.token)
    expected_data = {
        "claimableProfile": {
            "id": to_global_id(type="ProfileNode", id=profile.id),
            "firstName": profile.first_name,
            "lastName": profile.last_name,
        }
    }
    executed = user_gql_client.execute(query, context=request)

    assert "errors" not in executed
    assert dict(executed["data"]) == expected_data


def test_cannot_query_claimable_profile_with_user_already_attached(
    rf, user_gql_client, profile
):
    claim_token = ClaimTokenFactory(profile=profile)
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    t = Template(
        """
        {
            claimableProfile(token: "${claimToken}") {
                id
            }
        }
        """
    )
    query = t.substitute(claimToken=claim_token.token)
    executed = user_gql_client.execute(query, context=request)

    assert "errors" in executed


def test_cannot_query_claimable_profile_with_expired_token(rf, user_gql_client):
    profile = ProfileFactory(user=None)
    claim_token = ClaimTokenFactory(
        profile=profile, expires_at=timezone.now() - timedelta(days=1)
    )
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    t = Template(
        """
        {
            claimableProfile(token: "${claimToken}") {
                id
            }
        }
        """
    )
    query = t.substitute(claimToken=claim_token.token)
    executed = user_gql_client.execute(query, context=request)

    assert "errors" in executed
    assert executed["errors"][0]["extensions"]["code"] == TOKEN_EXPIRED_ERROR


def test_user_can_claim_claimable_profile_without_existing_profile(rf, user_gql_client):
    profile = ProfileWithPrimaryEmailFactory(
        user=None, first_name="John", last_name="Doe"
    )
    claim_token = ClaimTokenFactory(profile=profile)
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    t = Template(
        """
        mutation {
            claimProfile(
                input: {
                    token: "${claimToken}",
                    profile: {
                        firstName: "Joe",
                        nickname: "Joey"
                    }
                }
            ) {
                profile {
                    id
                    firstName
                    lastName
                    nickname
                }
            }
        }
        """
    )
    query = t.substitute(claimToken=claim_token.token)
    expected_data = {
        "claimProfile": {
            "profile": {
                "id": to_global_id(type="ProfileNode", id=profile.id),
                "firstName": "Joe",
                "nickname": "Joey",
                "lastName": profile.last_name,
            }
        }
    }
    executed = user_gql_client.execute(query, context=request)

    assert "errors" not in executed
    assert dict(executed["data"]) == expected_data
    profile.refresh_from_db()
    assert profile.user == user_gql_client.user
    assert profile.claim_tokens.count() == 0


def test_user_cannot_claim_claimable_profile_if_token_expired(rf, user_gql_client):
    profile = ProfileWithPrimaryEmailFactory(
        user=None, first_name="John", last_name="Doe"
    )
    expired_claim_token = ClaimTokenFactory(
        profile=profile, expires_at=timezone.now() - timedelta(days=1)
    )
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    t = Template(
        """
        mutation {
            claimProfile(
                input: {
                    token: "${claimToken}",
                    profile: {
                        firstName: "Joe",
                        nickname: "Joey"
                    }
                }
            ) {
                profile {
                    id
                    firstName
                    lastName
                    nickname
                }
            }
        }
        """
    )
    query = t.substitute(claimToken=expired_claim_token.token)
    executed = user_gql_client.execute(query, context=request)

    assert "errors" in executed
    assert executed["errors"][0]["extensions"]["code"] == TOKEN_EXPIRED_ERROR


def test_user_cannot_claim_claimable_profile_with_existing_profile(rf, user_gql_client):
    ProfileWithPrimaryEmailFactory(user=user_gql_client.user)
    profile_to_claim = ProfileFactory(user=None, first_name="John", last_name="Doe")
    expired_claim_token = ClaimTokenFactory(profile=profile_to_claim)
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    t = Template(
        """
        mutation {
            claimProfile(
                input: {
                    token: "${claimToken}",
                    profile: {
                        firstName: "Joe",
                        nickname: "Joey"
                    }
                }
            ) {
                profile {
                    id
                    firstName
                    lastName
                    nickname
                }
            }
        }
        """
    )
    query = t.substitute(claimToken=expired_claim_token.token)
    executed = user_gql_client.execute(query, context=request)

    assert "errors" in executed
    assert executed["errors"][0]["extensions"]["code"] == API_NOT_IMPLEMENTED_ERROR


class TemporaryProfileReadAccessTokenTestBase:
    def create_expired_token(self, profile):
        over_default_validity_duration = _default_temporary_read_access_token_validity_duration() + timedelta(
            seconds=1
        )
        expired_token_creation_time = timezone.now() - over_default_validity_duration
        token = TemporaryReadAccessTokenFactory(
            profile=profile, created_at=expired_token_creation_time
        )
        return token


class TestTemporaryProfileReadAccessTokenCreation(
    TemporaryProfileReadAccessTokenTestBase
):
    query = """
        mutation {
            createMyProfileTemporaryReadAccessToken(input: { }) {
                temporaryReadAccessToken {
                    token
                    expiresAt
                }
            }
        }
    """

    def test_normal_user_can_create_temporary_read_access_token_for_profile(
        self, rf, user_gql_client
    ):
        ProfileFactory(user=user_gql_client.user)
        request = rf.post("/graphql")
        request.user = user_gql_client.user

        executed = user_gql_client.execute(self.query, context=request)

        token_data = executed["data"]["createMyProfileTemporaryReadAccessToken"][
            "temporaryReadAccessToken"
        ]

        # Check that an UUID can be parsed from the token
        uuid.UUID(token_data["token"])

        actual_expiration_time = datetime.fromisoformat(token_data["expiresAt"])
        expected_expiration_time = timezone.now() + timedelta(days=2)
        assert_almost_equal(
            actual_expiration_time, expected_expiration_time, timedelta(seconds=1)
        )

    def test_anonymous_user_cannot_create_any_temporary_read_access_token_for_profile(
        self, rf, anon_user_gql_client
    ):
        request = rf.post("/graphql")
        request.user = anon_user_gql_client.user

        executed = anon_user_gql_client.execute(self.query, context=request)

        assert executed["errors"][0]["extensions"]["code"] == PERMISSION_DENIED_ERROR

    def test_other_valid_tokens_are_deleted_when_a_new_token_is_created(
        self, rf, user_gql_client
    ):
        profile = ProfileFactory(user=user_gql_client.user)
        request = rf.post("/graphql")
        request.user = user_gql_client.user

        valid_token1 = TemporaryReadAccessTokenFactory(profile=profile)
        valid_token2 = TemporaryReadAccessTokenFactory(profile=profile)
        valid_token_for_another_profile = TemporaryReadAccessTokenFactory()
        expired_token = self.create_expired_token(profile)

        executed = user_gql_client.execute(self.query, context=request)
        token_data = executed["data"]["createMyProfileTemporaryReadAccessToken"][
            "temporaryReadAccessToken"
        ]
        new_token_uuid = uuid.UUID(token_data["token"])

        def token_exists(token):
            token = token if isinstance(token, uuid.UUID) else token.token
            return TemporaryReadAccessToken.objects.filter(token=token).exists()

        assert not token_exists(valid_token1)
        assert not token_exists(valid_token2)
        assert token_exists(expired_token)
        assert token_exists(new_token_uuid)
        assert token_exists(valid_token_for_another_profile)


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
