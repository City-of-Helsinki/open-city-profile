from string import Template

import pytest
from django.utils.translation import gettext_lazy as _
from graphql_relay.node.node import to_global_id
from guardian.shortcuts import assign_perm

from profiles.enums import EmailType
from profiles.models import Profile
from services.enums import ServiceType

from .factories import AddressFactory, PhoneFactory, ProfileWithPrimaryEmailFactory


@pytest.mark.parametrize("service__service_type", [ServiceType.YOUTH_MEMBERSHIP])
def test_staff_user_can_update_a_profile(rf, user_gql_client, group, service):
    profile = ProfileWithPrimaryEmailFactory(first_name="Joe")
    phone = PhoneFactory(profile=profile)
    address = AddressFactory(profile=profile)
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_manage_profiles", group, service)
    assign_perm("can_view_sensitivedata", group, service)
    assign_perm("can_manage_sensitivedata", group, service)
    request = rf.post("/graphql")
    request.user = user
    request.service = service

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
                        id: \"${id}\",
                        firstName: \"${first_name}\",
                        addEmails: [{
                            email: \"${email}\"
                            emailType: ${email_type}
                            primary: ${primary}
                        }],
                        updatePhones: [{
                            id: \"${phone_id}\",
                            phone: \"${phone}\",
                        }],
                        removeAddresses: [\"${address_id}\"],
                        sensitivedata: {
                            ssn: \"${ssn}\"
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
    executed = user_gql_client.execute(query, context=request)
    assert executed["data"] == expected_data


@pytest.mark.parametrize("service__service_type", [ServiceType.YOUTH_MEMBERSHIP])
def test_staff_user_cannot_update_profile_sensitive_data_without_correct_permission(
    rf, user_gql_client, group, service
):
    """A staff user without can_manage_sensitivedata permission cannot update sensitive data."""
    profile = ProfileWithPrimaryEmailFactory()
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_manage_profiles", group, service)
    assign_perm("can_view_sensitivedata", group, service)

    request = rf.post("/graphql")
    request.user = user
    request.service = service

    t = Template(
        """
        mutation {
            updateProfile(
                input: {
                    profile: {
                        id: \"${id}\",
                        sensitivedata: {
                            ssn: \"${ssn}\"
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
    executed = user_gql_client.execute(query, context=request)

    assert "errors" in executed
    assert executed["errors"][0]["message"] == _(
        "You do not have permission to perform this action."
    )


def test_normal_user_cannot_update_a_profile_using_update_profile_mutation(
    rf, user_gql_client, service_factory
):
    profile = ProfileWithPrimaryEmailFactory(first_name="Joe")
    service = service_factory(service_type=ServiceType.YOUTH_MEMBERSHIP)
    request = rf.post("/graphql")
    request.user = user_gql_client.user
    request.service = service

    t = Template(
        """
        mutation {
            updateProfile(
                input: {
                    profile: {
                        id: \"${id}\",
                        firstName: \"${first_name}\",
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
    executed = user_gql_client.execute(query, context=request)
    assert "errors" in executed
    assert executed["errors"][0]["message"] == _(
        "You do not have permission to perform this action."
    )
    assert Profile.objects.get(pk=profile.pk).first_name == profile.first_name
