from .factories import EmailFactory, ProfileFactory


def test_emails_are_ordered_first_by_primary_then_by_id(user_gql_client):
    profile = ProfileFactory(user=user_gql_client.user)
    first_email = EmailFactory(profile=profile, primary=False)
    primary_email = EmailFactory(profile=profile, primary=True)
    second_email = EmailFactory(profile=profile, primary=False)

    query = """
        {
            myProfile {
                emails {
                    edges {
                        node {
                            email
                        }
                    }
                }
            }
        }
    """

    expected_edges = list(
        map(
            lambda email: {"node": {"email": email.email}},
            (primary_email, first_email, second_email),
        )
    )

    executed = user_gql_client.execute(query)
    assert executed["data"]["myProfile"]["emails"]["edges"] == expected_edges
