import uuid
from datetime import datetime, timedelta

import pytest
from django.utils import timezone

from open_city_profile.consts import PERMISSION_DENIED_ERROR
from open_city_profile.tests.asserts import assert_almost_equal, assert_match_error_code
from profiles.models import TemporaryReadAccessToken
from services.tests.factories import ServiceConnectionFactory

from .conftest import TemporaryProfileReadAccessTokenTestBase
from .factories import ProfileFactory, TemporaryReadAccessTokenFactory


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

    @pytest.mark.parametrize("with_serviceconnection", (True, False))
    def test_normal_user_can_create_temporary_read_access_token_for_profile(
        self, user_gql_client, service, with_serviceconnection
    ):
        profile = ProfileFactory(user=user_gql_client.user)
        if with_serviceconnection:
            ServiceConnectionFactory(profile=profile, service=service)

        executed = user_gql_client.execute(self.query, service=service)

        if with_serviceconnection:
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
        else:
            assert_match_error_code(executed, "PERMISSION_DENIED_ERROR")
            assert executed["data"]["createMyProfileTemporaryReadAccessToken"] is None

    def test_anonymous_user_cannot_create_any_temporary_read_access_token_for_profile(
        self, anon_user_gql_client
    ):
        executed = anon_user_gql_client.execute(self.query)

        assert executed["errors"][0]["extensions"]["code"] == PERMISSION_DENIED_ERROR

    def test_other_valid_tokens_are_deleted_when_a_new_token_is_created(
        self, user_gql_client
    ):
        profile = ProfileFactory(user=user_gql_client.user)

        valid_token1 = TemporaryReadAccessTokenFactory(profile=profile)
        valid_token2 = TemporaryReadAccessTokenFactory(profile=profile)
        valid_token_for_another_profile = TemporaryReadAccessTokenFactory()
        expired_token = self.create_expired_token(profile)

        executed = user_gql_client.execute(self.query)
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
