from datetime import timedelta
from string import Template

from django.utils import timezone
from graphql_relay.node.node import to_global_id

from open_city_profile.consts import API_NOT_IMPLEMENTED_ERROR, TOKEN_EXPIRED_ERROR
from open_city_profile.tests.asserts import assert_match_error_code

from .factories import (
    ClaimTokenFactory,
    EmailFactory,
    ProfileFactory,
    ProfileWithPrimaryEmailFactory,
)


def test_user_can_claim_claimable_profile_without_existing_profile(user_gql_client):
    profile = ProfileWithPrimaryEmailFactory(
        user=None, first_name="John", last_name="Doe"
    )
    claim_token = ClaimTokenFactory(profile=profile)

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
    executed = user_gql_client.execute(query)

    assert "errors" not in executed
    assert dict(executed["data"]) == expected_data
    profile.refresh_from_db()
    assert profile.user == user_gql_client.user
    assert profile.claim_tokens.count() == 0


def test_changing_an_email_address_marks_it_unverified(user_gql_client):
    profile = ProfileFactory(user=None)
    email = EmailFactory(profile=profile, verified=True)
    claim_token = ClaimTokenFactory(profile=profile)

    claim_profile_mutation = """
        mutation claimProfileWithEmailUpdates($token: UUID!, $emailUpdates: [UpdateEmailInput]) {
            claimProfile(
                input: {
                    token: $token,
                    profile: {
                        updateEmails: $emailUpdates
                    }
                }
            ) {
                profile {
                    emails {
                        edges {
                            node {
                                id
                                email
                                verified
                            }
                        }
                    }
                }
            }
        }
    """

    new_email_value = "new@email.example"

    expected_data = {
        "claimProfile": {
            "profile": {
                "emails": {
                    "edges": [
                        {
                            "node": {
                                "id": to_global_id("EmailNode", email.id),
                                "email": new_email_value,
                                "verified": False,
                            }
                        },
                    ]
                }
            }
        }
    }

    variables = {
        "token": str(claim_token.token),
        "emailUpdates": [
            {"id": to_global_id("EmailNode", email.id), "email": new_email_value}
        ],
    }

    executed = user_gql_client.execute(claim_profile_mutation, variables=variables,)
    assert executed["data"] == expected_data


def test_user_cannot_claim_claimable_profile_if_token_expired(user_gql_client):
    profile = ProfileWithPrimaryEmailFactory(
        user=None, first_name="John", last_name="Doe"
    )
    expired_claim_token = ClaimTokenFactory(
        profile=profile, expires_at=timezone.now() - timedelta(days=1)
    )

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
    executed = user_gql_client.execute(query)

    assert "errors" in executed
    assert executed["errors"][0]["extensions"]["code"] == TOKEN_EXPIRED_ERROR


def test_user_cannot_claim_claimable_profile_with_existing_profile(user_gql_client):
    ProfileWithPrimaryEmailFactory(user=user_gql_client.user)
    profile_to_claim = ProfileFactory(user=None, first_name="John", last_name="Doe")
    expired_claim_token = ClaimTokenFactory(profile=profile_to_claim)

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
    executed = user_gql_client.execute(query)

    assert "errors" in executed
    assert executed["errors"][0]["extensions"]["code"] == API_NOT_IMPLEMENTED_ERROR


def test_anon_user_can_not_claim_claimable_profile(anon_user_gql_client):
    profile = ProfileWithPrimaryEmailFactory(
        user=None, first_name="John", last_name="Doe"
    )
    claim_token = ClaimTokenFactory(profile=profile)

    t = Template(
        """
        mutation {
            claimProfile(
                input: {
                    token: "${claimToken}"
                }
            ) {
                profile {
                    id
                }
            }
        }
        """
    )
    query = t.substitute(claimToken=claim_token.token)

    executed = anon_user_gql_client.execute(query)
    assert_match_error_code(executed, "PERMISSION_DENIED_ERROR")
