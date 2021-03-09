from string import Template

from open_city_profile.consts import PROFILE_MUST_HAVE_ONE_PRIMARY_EMAIL


def test_normal_user_can_create_profile(rf, user_gql_client, email_data, profile_data):
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    t = Template(
        """
            mutation {
                createMyProfile(
                    input: {
                        profile: {
                            nickname: "${nickname}",
                            addEmails:[
                                {emailType: ${email_type}, email:"${email}", primary: ${primary}}
                            ]
                        }
                    }
                ) {
                profile{
                    nickname,
                    emails{
                        edges{
                        node{
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
                                "primary": email_data["primary"],
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
        primary=str(email_data["primary"]).lower(),
    )
    executed = user_gql_client.execute(mutation, context=request)
    assert dict(executed["data"]) == expected_data


def test_normal_user_cannot_create_profile_with_no_primary_email(
    rf, user_gql_client, email_data
):
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    t = Template(
        """
            mutation {
                createMyProfile(
                    input: {
                        profile: {
                            addEmails:[
                                {emailType: ${email_type}, email:"${email}", primary: ${primary}}
                            ]
                        }
                    }
                ) {
                profile{
                    id
                }
            }
            }
        """
    )

    mutation = t.substitute(
        email=email_data["email"],
        email_type=email_data["email_type"],
        primary=str(not email_data["primary"]).lower(),
    )
    executed = user_gql_client.execute(mutation, context=request)
    assert "code" in executed["errors"][0]["extensions"]
    assert (
        executed["errors"][0]["extensions"]["code"]
        == PROFILE_MUST_HAVE_ONE_PRIMARY_EMAIL
    )
