from datetime import timedelta
from string import Template

from django.utils import timezone

from open_city_profile.consts import TOKEN_EXPIRED_ERROR
from open_city_profile.tests.asserts import assert_match_error_code

from ..helpers import to_global_id
from .factories import ClaimTokenFactory, ProfileFactory


def test_can_query_claimable_profile_with_token(user_gql_client):
    profile = ProfileFactory(user=None, first_name="John", last_name="Doe")
    claim_token = ClaimTokenFactory(profile=profile)

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
    executed = user_gql_client.execute(query, allowed_data_fields=["name"])

    assert "errors" not in executed
    assert dict(executed["data"]) == expected_data


def test_cannot_query_claimable_profile_with_user_already_attached(
    user_gql_client, profile
):
    claim_token = ClaimTokenFactory(profile=profile)

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
    executed = user_gql_client.execute(query)

    assert "errors" in executed


def test_cannot_query_claimable_profile_with_expired_token(user_gql_client):
    profile = ProfileFactory(user=None)
    claim_token = ClaimTokenFactory(
        profile=profile, expires_at=timezone.now() - timedelta(days=1)
    )

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
    executed = user_gql_client.execute(query)

    assert "errors" in executed
    assert executed["errors"][0]["extensions"]["code"] == TOKEN_EXPIRED_ERROR


def test_anon_user_can_not_query_claimable_profile_with_token(anon_user_gql_client):
    profile = ProfileFactory(user=None, first_name="John", last_name="Doe")
    claim_token = ClaimTokenFactory(profile=profile)

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

    executed = anon_user_gql_client.execute(query)
    assert_match_error_code(executed, "PERMISSION_DENIED_ERROR")
