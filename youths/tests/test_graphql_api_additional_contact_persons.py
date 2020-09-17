from string import Template

from graphql_relay import to_global_id

from profiles.tests.factories import EmailFactory, ProfileFactory
from youths.models import AdditionalContactPerson
from youths.tests.factories import (
    AdditionalContactPersonDictFactory,
    AdditionalContactPersonFactory,
    YouthProfileFactory,
)

ADDITIONAL_CONTACT_PERSONS_QUERY = """
{
    youthProfile {
        additionalContactPersons {
            edges {
                node {
                    id
                    firstName
                    lastName
                    phone
                    email
                }
            }
        }
    }
}
"""


UPDATE_MUTATION = Template(
    """
    mutation UpdateMyYouthProfile($$input: UpdateMyYouthProfileMutationInput!) {
        updateMyYouthProfile(input: $$input) ${query}
    }
    """
).substitute(query=ADDITIONAL_CONTACT_PERSONS_QUERY)


APPROVAL_MUTATION = Template(
    """
    mutation UpdateMyYouthProfile($$input: ApproveYouthProfileMutationInput!) {
        approveYouthProfile(input: $$input) ${query}
    }
    """
).substitute(query=ADDITIONAL_CONTACT_PERSONS_QUERY)


def test_normal_user_can_add_additional_contact_persons(
    rf, user_gql_client, phone_data
):
    profile = ProfileFactory(user=user_gql_client.user)
    YouthProfileFactory(profile=profile)
    acpd = AdditionalContactPersonDictFactory()
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    variables = {"input": {"youthProfile": {"addAdditionalContactPersons": [acpd]}}}
    executed = user_gql_client.execute(
        UPDATE_MUTATION, context=request, variables=variables
    )

    acp = AdditionalContactPerson.objects.first()
    expected_data = {
        "updateMyYouthProfile": {
            "youthProfile": {
                "additionalContactPersons": {
                    "edges": [
                        {
                            "node": {
                                "id": to_global_id(
                                    type="AdditionalContactPersonNode", id=acp.pk
                                ),
                                **acpd,
                            }
                        }
                    ]
                }
            }
        }
    }
    assert dict(executed["data"]) == expected_data


def test_normal_user_can_remove_additional_contact_persons(
    rf, user_gql_client, phone_data
):
    profile = ProfileFactory(user=user_gql_client.user)
    youth_profile = YouthProfileFactory(profile=profile)
    acp = AdditionalContactPersonFactory(youth_profile=youth_profile)
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    variables = {
        "input": {
            "youthProfile": {
                "removeAdditionalContactPersons": [
                    to_global_id(type="AdditionalContactPersonNode", id=acp.pk)
                ]
            }
        }
    }
    executed = user_gql_client.execute(
        UPDATE_MUTATION, context=request, variables=variables
    )

    expected_data = {
        "updateMyYouthProfile": {
            "youthProfile": {"additionalContactPersons": {"edges": []}}
        }
    }
    assert dict(executed["data"]) == expected_data


def test_normal_user_can_update_additional_contact_persons(
    rf, user_gql_client, phone_data
):
    profile = ProfileFactory(user=user_gql_client.user)
    youth_profile = YouthProfileFactory(profile=profile)
    acp = AdditionalContactPersonFactory(youth_profile=youth_profile)
    new_values = AdditionalContactPersonDictFactory()
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    variables = {
        "input": {
            "youthProfile": {
                "updateAdditionalContactPersons": [
                    {
                        "id": to_global_id(
                            type="AdditionalContactPersonNode", id=acp.pk
                        ),
                        **new_values,
                    }
                ],
            }
        }
    }
    executed = user_gql_client.execute(
        UPDATE_MUTATION, context=request, variables=variables
    )

    expected_data = {
        "updateMyYouthProfile": {
            "youthProfile": {
                "additionalContactPersons": {
                    "edges": [
                        {
                            "node": {
                                "id": to_global_id(
                                    type="AdditionalContactPersonNode", id=acp.pk
                                ),
                                **new_values,
                            }
                        }
                    ]
                }
            }
        }
    }
    assert dict(executed["data"]) == expected_data


def test_normal_user_can_query_additional_contact_persons(
    rf, user_gql_client, snapshot
):
    profile = ProfileFactory(user=user_gql_client.user)
    youth_profile = YouthProfileFactory(profile=profile)
    acp = AdditionalContactPersonFactory(youth_profile=youth_profile)
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    executed = user_gql_client.execute(
        ADDITIONAL_CONTACT_PERSONS_QUERY, context=request
    )

    expected_data = {
        "youthProfile": {
            "additionalContactPersons": {
                "edges": [
                    {
                        "node": {
                            "id": to_global_id(
                                type="AdditionalContactPersonNode", id=acp.pk
                            ),
                            "firstName": acp.first_name,
                            "lastName": acp.last_name,
                            "phone": acp.phone,
                            "email": acp.email,
                        }
                    }
                ]
            }
        }
    }
    assert dict(executed["data"]) == expected_data


def test_profile_approval_allows_changing_contact_persons(
    rf, anon_user_gql_client, youth_profile
):
    EmailFactory(primary=True, profile=youth_profile.profile)

    request = rf.post("/graphql")
    request.user = anon_user_gql_client.user

    acp_new_data = AdditionalContactPersonDictFactory()
    acp_update = AdditionalContactPersonFactory(youth_profile=youth_profile)
    acp_update_values = AdditionalContactPersonDictFactory()
    acp_remove = AdditionalContactPersonFactory(youth_profile=youth_profile)

    variables = {
        "input": {
            "approvalToken": youth_profile.approval_token,
            "approvalData": {
                "addAdditionalContactPersons": [acp_new_data],
                "updateAdditionalContactPersons": [
                    {
                        "id": to_global_id(
                            type="AdditionalContactPersonNode", id=acp_update.pk
                        ),
                        **acp_update_values,
                    }
                ],
                "removeAdditionalContactPersons": [
                    to_global_id(type="AdditionalContactPersonNode", id=acp_remove.pk)
                ],
            },
        }
    }

    anon_user_gql_client.execute(
        APPROVAL_MUTATION, context=request, variables=variables
    )

    assert not youth_profile.additional_contact_persons.filter(
        pk=acp_remove.pk
    ).exists()
    assert youth_profile.additional_contact_persons.filter(
        pk=acp_update.pk, first_name=acp_update_values["firstName"]
    ).exists()
    assert youth_profile.additional_contact_persons.exclude(
        pk__in=[acp_update.pk, acp_remove.pk]
    ).exists()
