from string import Template

import pytest
from django.utils.translation import gettext_lazy as _
from guardian.shortcuts import assign_perm

from open_city_profile.tests.factories import GroupFactory
from services.enums import ServiceType
from services.tests.factories import ServiceFactory

from .profile_input_validation import ProfileInputValidationBase


@pytest.mark.parametrize("with_email", [True, False])
@pytest.mark.parametrize("service__service_type", [ServiceType.BERTH])
def test_staff_user_can_create_a_profile(
    user_gql_client, email_data, phone_data, address_data, group, service, with_email
):
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_manage_profiles", group, service)

    # serviceType is included in query just to ensure that it has NO affect
    t = Template(
        """
        mutation {
            createProfile(
                input: {
                    serviceType: GODCHILDREN_OF_CULTURE,
                    profile: {
                        firstName: "${first_name}",
                        lastName: "${last_name}",
${email_input}
                        addPhones: [
                            {
                                phoneType: ${phone_type},
                                phone: "${phone}",
                                primary: true
                            }
                        ]
                    }
                }
            ) {
                profile {
                    firstName
                    lastName
                    phones {
                        edges {
                            node {
                                phoneType
                                phone
                                primary
                            }
                        }
                    }
                    emails {
                        edges {
                            node {
                                emailType
                                email
                                primary
                            }
                        }
                    }
                    serviceConnections {
                        edges {
                            node {
                                service {
                                    type
                                    name
                                }
                            }
                        }
                    }
                }
            }
        }
    """
    )
    email_input = f"""
                        addEmails: [
                            {{
                                emailType: {email_data["email_type"]},
                                email: "{email_data["email"]}",
                                primary: true,
                            }}
                        ],"""

    query = t.substitute(
        first_name="John",
        last_name="Doe",
        phone_type=phone_data["phone_type"],
        phone=phone_data["phone"],
        email_input=email_input if with_email else "",
    )

    expected_data = {
        "createProfile": {
            "profile": {
                "firstName": "John",
                "lastName": "Doe",
                "phones": {
                    "edges": [
                        {
                            "node": {
                                "phoneType": phone_data["phone_type"],
                                "phone": phone_data["phone"],
                                "primary": True,
                            }
                        }
                    ]
                },
                "emails": {
                    "edges": (
                        [
                            {
                                "node": {
                                    "emailType": email_data["email_type"],
                                    "email": email_data["email"],
                                    "primary": True,
                                }
                            }
                        ]
                        if with_email
                        else []
                    )
                },
                "serviceConnections": {
                    "edges": [
                        {
                            "node": {
                                "service": {
                                    "type": service.service_type.name,
                                    "name": service.name,
                                }
                            }
                        }
                    ]
                },
            }
        }
    }
    executed = user_gql_client.execute(query, service=service)
    assert executed["data"] == expected_data


def test_normal_user_cannot_create_a_profile_using_create_profile_mutation(
    user_gql_client, service
):
    t = Template(
        """
        mutation {
            createProfile(
                input: {
                    profile: {
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
    query = t.substitute(first_name="John")
    executed = user_gql_client.execute(query, service=service)
    assert "errors" in executed
    assert executed["errors"][0]["message"] == _(
        "You do not have permission to perform this action."
    )


def test_staff_user_with_sensitive_data_service_accesss_can_create_a_profile_with_sensitive_data(
    user_gql_client, email_data, group, service
):
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_manage_profiles", group, service)
    assign_perm("can_manage_sensitivedata", group, service)
    assign_perm("can_view_sensitivedata", group, service)

    t = Template(
        """
        mutation {
            createProfile(
                input: {
                    profile: {
                        firstName: "${first_name}",
                        addEmails: [
                            {
                                email: "${email}",
                                emailType: ${email_type},
                                primary: true
                            }
                        ],
                        sensitivedata: {
                            ssn: "${ssn}"
                        }
                    }
                }
            ) {
                profile {
                    firstName
                    sensitivedata {
                        ssn
                    }
                }
            }
        }
    """
    )
    query = t.substitute(
        first_name="John",
        ssn="121282-123E",
        email=email_data["email"],
        email_type=email_data["email_type"],
    )

    expected_data = {
        "createProfile": {
            "profile": {"firstName": "John", "sensitivedata": {"ssn": "121282-123E"}}
        }
    }
    executed = user_gql_client.execute(query, service=service)
    assert executed["data"] == expected_data


def test_staff_user_cannot_create_a_profile_with_sensitive_data_without_sensitive_data_service_access(
    user_gql_client, service_factory
):
    user = user_gql_client.user

    entitled_service = service_factory()
    entitled_group = GroupFactory(name="entitled_group")
    assign_perm("can_manage_profiles", entitled_group, entitled_service)
    assign_perm("can_manage_sensitivedata", entitled_group, entitled_service)
    assign_perm("can_view_sensitivedata", entitled_group, entitled_service)
    user.groups.add(entitled_group)

    unentitled_service = service_factory()
    unentitled_group = GroupFactory(name="unentitled_group")
    assign_perm("can_manage_profiles", unentitled_group, unentitled_service)
    user.groups.add(unentitled_group)

    t = Template(
        """
        mutation {
            createProfile(
                input: {
                    profile: {
                        firstName: "${first_name}",
                        sensitivedata: {
                            ssn: "${ssn}"
                        }
                    }
                }
            ) {
                profile {
                    firstName
                    sensitivedata {
                        ssn
                    }
                }
            }
        }
    """
    )
    query = t.substitute(first_name="John", ssn="121282-123E")

    executed = user_gql_client.execute(query, service=unentitled_service)
    assert "errors" in executed
    assert executed["errors"][0]["message"] == _(
        "You do not have permission to perform this action."
    )


class TestProfileInputValidation(ProfileInputValidationBase):
    def execute_query(self, user_gql_client, profile_input):
        user = user_gql_client.user
        group = GroupFactory()
        service = ServiceFactory()

        user.groups.add(group)
        assign_perm("can_manage_profiles", group, service)
        assign_perm("can_manage_sensitivedata", group, service)
        assign_perm("can_view_sensitivedata", group, service)

        mutation = """
            mutation createProfile($profileInput: CreateProfileInput!) {
                createProfile(
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

        return user_gql_client.execute(mutation, service=service, variables=variables)
