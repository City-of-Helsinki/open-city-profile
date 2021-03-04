from string import Template

from django.utils.translation import gettext_lazy as _
from guardian.shortcuts import assign_perm

from open_city_profile.tests.factories import GroupFactory
from services.enums import ServiceType


def test_staff_user_can_create_a_profile(
    rf, user_gql_client, email_data, phone_data, address_data, group, service
):
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_manage_profiles", group, service)
    request = rf.post("/graphql")
    request.user = user

    t = Template(
        """
        mutation {
            createProfile(
                input: {
                    serviceType: ${service_type},
                    profile: {
                        firstName: \"${first_name}\",
                        lastName: \"${last_name}\",
                        addEmails: [{
                            emailType: ${email_type},
                            email: \"${email}\",
                            primary: true,
                        }],
                        addPhones: [{
                            phoneType: ${phone_type},
                            phone: \"${phone}\",
                            primary: true
                        }]
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
                                }
                            }
                        }
                    }
                }
            }
        }
    """
    )
    query = t.substitute(
        service_type=ServiceType.BERTH.name,
        first_name="John",
        last_name="Doe",
        phone_type=phone_data["phone_type"],
        phone=phone_data["phone"],
        email_type=email_data["email_type"],
        email=email_data["email"],
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
                    "edges": [
                        {
                            "node": {
                                "emailType": email_data["email_type"],
                                "email": email_data["email"],
                                "primary": True,
                            }
                        }
                    ]
                },
                "serviceConnections": {
                    "edges": [{"node": {"service": {"type": ServiceType.BERTH.name}}}]
                },
            }
        }
    }
    executed = user_gql_client.execute(query, context=request)
    assert executed["data"] == expected_data


def test_normal_user_cannot_create_a_profile_using_create_profile_mutation(
    rf, user_gql_client, service_factory
):
    service_factory()
    user = user_gql_client.user
    request = rf.post("/graphql")
    request.user = user

    t = Template(
        """
        mutation {
            createProfile(
                input: {
                    serviceType: ${service_type},
                    profile: {
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
    query = t.substitute(service_type=ServiceType.BERTH.name, first_name="John")
    executed = user_gql_client.execute(query, context=request)
    assert "errors" in executed
    assert executed["errors"][0]["message"] == _(
        "You do not have permission to perform this action."
    )


def test_staff_user_cannot_create_a_profile_without_service_access(
    rf, user_gql_client, service_factory
):
    service_factory(service_type=ServiceType.BERTH)
    service = service_factory(service_type=ServiceType.YOUTH_MEMBERSHIP)
    group = GroupFactory(name="youth_membership")
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_manage_profiles", group, service)
    request = rf.post("/graphql")
    request.user = user

    t = Template(
        """
        mutation {
            createProfile(
                input: {
                    serviceType: ${service_type},
                    profile: {
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
    query = t.substitute(service_type=ServiceType.BERTH.name, first_name="John")
    executed = user_gql_client.execute(query, context=request)
    assert "errors" in executed
    assert executed["errors"][0]["message"] == _(
        "You do not have permission to perform this action."
    )


def test_staff_user_with_sensitive_data_service_accesss_can_create_a_profile_with_sensitive_data(
    rf, user_gql_client, email_data, group, service
):
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_manage_profiles", group, service)
    assign_perm("can_manage_sensitivedata", group, service)
    assign_perm("can_view_sensitivedata", group, service)
    request = rf.post("/graphql")
    request.user = user

    t = Template(
        """
        mutation {
            createProfile(
                input: {
                    serviceType: ${service_type},
                    profile: {
                        firstName: \"${first_name}\",
                        addEmails: [{
                            email: \"${email}\",
                            emailType: ${email_type},
                            primary: true
                        }],
                        sensitivedata: {
                            ssn: \"${ssn}\"
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
        service_type=ServiceType.BERTH.name,
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
    executed = user_gql_client.execute(query, context=request)
    assert executed["data"] == expected_data


def test_staff_user_cannot_create_a_profile_with_sensitive_data_without_sensitive_data_service_access(
    rf, user_gql_client, service_factory
):
    service_berth = service_factory(service_type=ServiceType.BERTH)
    service_youth = service_factory(service_type=ServiceType.YOUTH_MEMBERSHIP)
    group_berth = GroupFactory(name=ServiceType.BERTH.value)
    group_youth = GroupFactory(name="youth_membership")
    user = user_gql_client.user
    user.groups.add(group_berth)
    user.groups.add(group_youth)
    assign_perm("can_manage_profiles", group_berth, service_berth)
    assign_perm("can_manage_sensitivedata", group_youth, service_youth)
    assign_perm("can_view_sensitivedata", group_youth, service_youth)
    request = rf.post("/graphql")
    request.user = user

    t = Template(
        """
        mutation {
            createProfile(
                input: {
                    serviceType: ${service_type},
                    profile: {
                        firstName: \"${first_name}\",
                        sensitivedata: {
                            ssn: \"${ssn}\"
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
        service_type=ServiceType.BERTH.name, first_name="John", ssn="121282-123E"
    )

    executed = user_gql_client.execute(query, context=request)
    assert "errors" in executed
    assert executed["errors"][0]["message"] == _(
        "You do not have permission to perform this action."
    )
