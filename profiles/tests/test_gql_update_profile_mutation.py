from string import Template

import pytest
from django.utils.translation import gettext_lazy as _
from graphql_relay.node.node import to_global_id
from guardian.shortcuts import assign_perm

from open_city_profile.tests.asserts import assert_match_error_code
from open_city_profile.tests.factories import GroupFactory
from profiles.enums import EmailType
from profiles.models import Profile
from services.tests.factories import ServiceConnectionFactory

from .factories import (
    AddressFactory,
    EmailFactory,
    PhoneFactory,
    ProfileWithPrimaryEmailFactory,
)


def setup_profile_and_staff_user_to_service(
    profile, user, service, can_view_sensitivedata=False, can_manage_sensitivedata=False
):
    if profile:
        ServiceConnectionFactory(profile=profile, service=service)

    group = GroupFactory()

    assign_perm("can_manage_profiles", group, service)
    if can_view_sensitivedata:
        assign_perm("can_view_sensitivedata", group, service)
    if can_manage_sensitivedata:
        assign_perm("can_manage_sensitivedata", group, service)

    user.groups.add(group)


@pytest.mark.parametrize("with_serviceconnection", (True, False))
@pytest.mark.parametrize("implicit_serviceconnection", (True, False))
def test_staff_user_can_update_a_profile(
    user_gql_client, service, with_serviceconnection, implicit_serviceconnection
):
    if implicit_serviceconnection:
        service.implicit_connection = True
        service.save()

    profile = ProfileWithPrimaryEmailFactory(first_name="Joe")
    phone = PhoneFactory(profile=profile)
    address = AddressFactory(profile=profile)

    setup_profile_and_staff_user_to_service(
        profile if with_serviceconnection else None,
        user_gql_client.user,
        service,
        can_view_sensitivedata=True,
        can_manage_sensitivedata=True,
    )

    data = {
        "first_name": "John",
        "email": {
            "email": "another@example.com",
            "email_type": EmailType.WORK.name,
            "primary": False,
        },
        "phone": "0407654321",
        "school_class": "5F",
        "ssn": "010199-1234",
    }

    t = Template(
        """
        mutation {
            updateProfile(
                input: {
                    profile: {
                        id: "${id}",
                        firstName: "${first_name}",
                        addEmails: [
                            {
                                email: "${email}"
                                emailType: ${email_type}
                                primary: ${primary}
                            }
                        ],
                        updatePhones: [
                            {
                                id: "${phone_id}",
                                phone: "${phone}",
                            }
                        ],
                        removeAddresses: ["${address_id}"],
                        sensitivedata: {
                            ssn: "${ssn}"
                        }
                    }
                }
            ) {
                profile {
                    firstName
                    emails {
                        edges {
                            node {
                                email
                            }
                        }
                    }
                    phones {
                        edges {
                            node {
                                phone
                            }
                        }
                    }
                    addresses {
                        edges {
                            node {
                                address
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
    query = t.substitute(
        id=to_global_id("ProfileNode", profile.pk),
        first_name=data["first_name"],
        phone_id=to_global_id("PhoneNode", phone.pk),
        email=data["email"]["email"],
        email_type=data["email"]["email_type"],
        primary=str(data["email"]["primary"]).lower(),
        phone=data["phone"],
        address_id=to_global_id(type="AddressNode", id=address.pk),
        ssn=data["ssn"],
    )
    expected_data = {
        "updateProfile": {
            "profile": {
                "firstName": data["first_name"],
                "emails": {
                    "edges": [
                        {"node": {"email": profile.emails.first().email}},
                        {"node": {"email": data["email"]["email"]}},
                    ]
                },
                "phones": {"edges": [{"node": {"phone": data["phone"]}}]},
                "addresses": {"edges": []},
                "sensitivedata": {"ssn": data["ssn"]},
            }
        }
    }
    executed = user_gql_client.execute(query, service=service)
    if with_serviceconnection:
        assert executed["data"] == expected_data
    else:
        assert_match_error_code(executed, "PERMISSION_DENIED_ERROR")
        assert executed["data"]["updateProfile"] is None


EMAILS_MUTATION = """
    mutation updateEmails($profileInput: UpdateProfileInput!) {
        updateProfile(
            input: {
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


def test_changing_an_email_address_marks_it_unverified(user_gql_client, service):
    email = EmailFactory(email="old@email.example", verified=True)
    profile = email.profile

    setup_profile_and_staff_user_to_service(profile, user_gql_client.user, service)

    new_email_value = "new@email.example"

    expected_data = {
        "updateProfile": {
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
        "profileInput": {
            "id": to_global_id("ProfileNode", profile.id),
            "updateEmails": [
                {"id": to_global_id("EmailNode", email.id), "email": new_email_value}
            ],
        }
    }

    executed = user_gql_client.execute(
        EMAILS_MUTATION, service=service, variables=variables,
    )
    assert executed["data"] == expected_data


def test_staff_user_cannot_update_profile_sensitive_data_without_correct_permission(
    user_gql_client, service
):
    """A staff user without can_manage_sensitivedata permission cannot update sensitive data."""
    profile = ProfileWithPrimaryEmailFactory()

    setup_profile_and_staff_user_to_service(
        profile, user_gql_client.user, service, can_view_sensitivedata=True
    )

    t = Template(
        """
        mutation {
            updateProfile(
                input: {
                    profile: {
                        id: "${id}",
                        sensitivedata: {
                            ssn: "${ssn}"
                        }
                    }
                }
            ) {
                profile {
                    sensitivedata {
                        ssn
                    }
                }
            }
        }
    """
    )
    query = t.substitute(id=to_global_id("ProfileNode", profile.pk), ssn="010199-1234",)
    executed = user_gql_client.execute(query, service=service)

    assert "errors" in executed
    assert executed["errors"][0]["message"] == _(
        "You do not have permission to perform this action."
    )


def test_normal_user_cannot_update_a_profile_using_update_profile_mutation(
    user_gql_client, service
):
    profile = ProfileWithPrimaryEmailFactory(first_name="Joe")
    ServiceConnectionFactory(profile=profile, service=service)

    t = Template(
        """
        mutation {
            updateProfile(
                input: {
                    profile: {
                        id: "${id}",
                        firstName: "${first_name}",
                    }
                }
            ) {
                profile {
                    firstName
                }
            }
        }
    """
    )
    query = t.substitute(id=to_global_id("ProfileNode", profile.pk), first_name="John",)
    executed = user_gql_client.execute(query, service=service)
    assert "errors" in executed
    assert executed["errors"][0]["message"] == _(
        "You do not have permission to perform this action."
    )
    assert Profile.objects.get(pk=profile.pk).first_name == profile.first_name
