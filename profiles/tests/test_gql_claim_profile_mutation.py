from datetime import timedelta
from string import Template

from django.utils import timezone

from open_city_profile.consts import (
    PROFILE_ALREADY_EXISTS_FOR_USER_ERROR,
    TOKEN_EXPIRED_ERROR,
)
from open_city_profile.tests.asserts import assert_match_error_code
from profiles.models import Profile

from ..helpers import to_global_id
from .factories import (
    ClaimTokenFactory,
    EmailFactory,
    ProfileFactory,
    ProfileWithPrimaryEmailFactory,
)
from .profile_input_validation import ExistingProfileInputValidationBase


def test_user_can_claim_claimable_profile_without_existing_profile(
    user_gql_client, profile_updated_listener
):
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
    executed = user_gql_client.execute(query, allowed_data_fields=["name"])

    assert "errors" not in executed
    assert dict(executed["data"]) == expected_data
    profile.refresh_from_db()
    assert profile.user == user_gql_client.user
    assert profile.claim_tokens.count() == 0

    profile_updated_listener.assert_called_once()
    assert profile_updated_listener.call_args[1]["sender"] == Profile
    assert profile_updated_listener.call_args[1]["instance"] == profile


CLAIM_PROFILE_MUTATION = """
    mutation claimProfileWithEmailUpdates($token: UUID!, $profileInput: ProfileInput) {
        claimProfile(
            input: {
                token: $token,
                profile: $profileInput
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


def test_user_cant_get_fields_not_allowed_when_claiming_a_profile(user_gql_client):
    profile = ProfileWithPrimaryEmailFactory(user=None)
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
                    sensitivedata {
                        ssn
                    }
                }
            }
        }
        """
    )
    query = t.substitute(claimToken=claim_token.token)
    executed = user_gql_client.execute(query, allowed_data_fields=["name"])

    assert "errors" in executed
    assert_match_error_code(executed, "FIELD_NOT_ALLOWED_ERROR")


def test_can_not_change_primary_email_to_non_primary(user_gql_client):
    profile = ProfileFactory(user=None)
    email = EmailFactory(profile=profile, primary=True)
    claim_token = ClaimTokenFactory(profile=profile)

    variables = {
        "token": str(claim_token.token),
        "profileInput": {
            "updateEmails": [
                {"id": to_global_id(type="EmailNode", id=email.id), "primary": False}
            ],
        },
    }

    executed = user_gql_client.execute(
        CLAIM_PROFILE_MUTATION, variables=variables, allowed_data_fields=["email"]
    )
    assert_match_error_code(executed, "PROFILE_MUST_HAVE_PRIMARY_EMAIL")


def test_can_not_delete_primary_email(user_gql_client):
    profile = ProfileFactory(user=None)
    email = EmailFactory(profile=profile, primary=True)
    claim_token = ClaimTokenFactory(profile=profile)

    email_deletes = [to_global_id(type="EmailNode", id=email.id)]
    executed = user_gql_client.execute(
        CLAIM_PROFILE_MUTATION,
        variables={
            "token": str(claim_token.token),
            "profileInput": {"removeEmails": email_deletes},
        },
        allowed_data_fields=["email"],
    )
    assert_match_error_code(executed, "PROFILE_MUST_HAVE_PRIMARY_EMAIL")


def test_changing_an_email_address_marks_it_unverified(
    user_gql_client, execution_context_class
):
    profile = ProfileFactory(user=None)
    email = EmailFactory(profile=profile, verified=True)
    claim_token = ClaimTokenFactory(profile=profile)

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
        "profileInput": {
            "updateEmails": [
                {"id": to_global_id("EmailNode", email.id), "email": new_email_value}
            ]
        },
    }

    executed = user_gql_client.execute(
        CLAIM_PROFILE_MUTATION,
        variables=variables,
        execution_context_class=execution_context_class,
        allowed_data_fields=["email"],
    )
    assert "errors" not in executed
    assert executed["data"] == expected_data


class TestProfileInputValidation(ExistingProfileInputValidationBase):
    def create_profile(self, user):
        return ProfileFactory(user=None)

    def execute_query(self, user_gql_client, profile_input):
        claim_token = ClaimTokenFactory(profile=self.profile)

        variables = {
            "token": str(claim_token.token),
            "profileInput": profile_input,
        }

        return user_gql_client.execute(
            CLAIM_PROFILE_MUTATION, variables=variables, allowed_data_fields=["email"]
        )


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
    executed = user_gql_client.execute(query, allowed_data_fields=["name"])

    assert "errors" in executed
    assert executed["errors"][0]["extensions"]["code"] == TOKEN_EXPIRED_ERROR


def test_using_non_existing_token_produces_an_object_does_not_exist_error(
    user_gql_client,
):
    non_existing_token = "e5d47102-a29b-441d-adbc-c6e4e762ffe1"

    variables = {
        "token": non_existing_token,
    }
    executed = user_gql_client.execute(
        CLAIM_PROFILE_MUTATION, variables=variables, allowed_data_fields=["email"]
    )

    assert_match_error_code(executed, "OBJECT_DOES_NOT_EXIST_ERROR")


def test_user_cannot_claim_claimable_profile_with_existing_profile(user_gql_client):
    ProfileWithPrimaryEmailFactory(user=user_gql_client.user)
    profile_to_claim = ProfileFactory(user=None, first_name="John", last_name="Doe")
    claim_token = ClaimTokenFactory(profile=profile_to_claim)

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
    executed = user_gql_client.execute(query, allowed_data_fields=["name"])

    assert "errors" in executed
    assert (
        executed["errors"][0]["extensions"]["code"]
        == PROFILE_ALREADY_EXISTS_FOR_USER_ERROR
    )


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
