from string import Template

import pytest

from open_city_profile.tests.asserts import assert_match_error_code

from .profile_input_validation import ProfileInputValidationBase


@pytest.mark.parametrize("email_is_primary", [True, False])
def test_normal_user_can_create_profile(
    user_gql_client, email_data, profile_data, email_is_primary
):
    ssn = "101085-1234"

    t = Template(
        """
            mutation {
                createMyProfile(
                    input: {
                        profile: {
                            language: FINNISH,
                            contactMethod: EMAIL,
                            nickname: "${nickname}",
                            addEmails: [
                                {emailType: ${email_type}, email:"${email}", primary: ${primary}}
                            ]
                            sensitivedata: {
                                ssn: "${ssn}"
                            }
                        }
                    }
                ) {
                    profile {
                        language,
                        contactMethod,
                        nickname,
                        emails {
                            edges {
                                node {
                                    email,
                                    emailType,
                                    primary,
                                    verified
                                }
                            }
                        }
                        sensitivedata {
                            ssn
                        }
                    }
                }
            }
        """
    )

    expected_data = {
        "createMyProfile": {
            "profile": {
                "language": "FINNISH",
                "contactMethod": "EMAIL",
                "nickname": profile_data["nickname"],
                "emails": {
                    "edges": [
                        {
                            "node": {
                                "email": email_data["email"],
                                "emailType": email_data["email_type"],
                                "primary": email_is_primary,
                                "verified": False,
                            }
                        }
                    ]
                },
                "sensitivedata": {"ssn": ssn},
            }
        }
    }

    mutation = t.substitute(
        nickname=profile_data["nickname"],
        email=email_data["email"],
        email_type=email_data["email_type"],
        primary=str(email_is_primary).lower(),
        ssn=ssn,
    )
    executed = user_gql_client.execute(
        mutation, allowed_data_fields=["email", "name", "personalidentitycode"]
    )
    assert "errors" not in executed
    assert executed["data"] == expected_data


def test_normal_user_can_create_profile_with_no_email(user_gql_client, email_data):
    mutation = """
            mutation {
                createMyProfile(
                    input: {
                        profile: {}
                    }
                ) {
                    profile {
                        emails {
                            edges {
                                node {
                                    email,
                                    emailType,
                                    primary,
                                    verified
                                }
                            }
                        }
                    }
                }
            }
        """

    expected_data = {"createMyProfile": {"profile": {"emails": {"edges": []}}}}

    executed = user_gql_client.execute(mutation, allowed_data_fields=["email"])
    assert executed["data"] == expected_data


def test_cant_query_fields_not_allowed_in_create_mutation(user_gql_client, email_data):
    mutation = """
            mutation {
                createMyProfile(
                    input: {
                        profile: {}
                    }
                ) {
                    profile {
                        firstName
                        emails {
                            edges {
                                node {
                                    email,
                                    emailType,
                                    primary,
                                    verified
                                }
                            }
                        }
                    }
                }
            }
        """

    expected_data = {
        "profile": {"firstName": user_gql_client.user.first_name, "emails": None}
    }

    executed = user_gql_client.execute(mutation, allowed_data_fields=["name"])

    assert "errors" in executed
    assert expected_data == executed["data"]["createMyProfile"]
    assert_match_error_code(executed, "FIELD_NOT_ALLOWED_ERROR")


class TestProfileInputValidation(ProfileInputValidationBase):
    def execute_query(self, user_gql_client, profile_input):
        mutation = """
            mutation createMyProfile($profileInput: ProfileInput!) {
                createMyProfile(
                    input: {
                        profile: $profileInput
                    }
                ) {
                    profile {
                        id
                    }
                }
            }
        """

        variables = {"profileInput": profile_input}

        return user_gql_client.execute(mutation, variables=variables)


def test_anon_user_can_not_create_profile(anon_user_gql_client):
    mutation = """
            mutation {
                createMyProfile(
                    input: {
                        profile: {}
                    }
                ) {
                    profile {
                        id
                    }
                }
            }
        """

    executed = anon_user_gql_client.execute(mutation)
    assert_match_error_code(executed, "PERMISSION_DENIED_ERROR")
