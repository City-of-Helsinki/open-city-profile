from string import Template

import pytest


@pytest.mark.parametrize("email_is_primary", [True, False])
def test_normal_user_can_create_profile(
    user_gql_client, email_data, profile_data, email_is_primary
):
    t = Template(
        """
            mutation {
                createMyProfile(
                    input: {
                        profile: {
                            nickname: "${nickname}",
                            addEmails: [
                                {emailType: ${email_type}, email:"${email}", primary: ${primary}}
                            ]
                        }
                    }
                ) {
                    profile {
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
                    }
                }
            }
        """
    )

    expected_data = {
        "createMyProfile": {
            "profile": {
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
            }
        }
    }

    mutation = t.substitute(
        nickname=profile_data["nickname"],
        email=email_data["email"],
        email_type=email_data["email_type"],
        primary=str(email_is_primary).lower(),
    )
    executed = user_gql_client.execute(mutation)
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

    executed = user_gql_client.execute(mutation)
    assert executed["data"] == expected_data
