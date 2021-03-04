import uuid
from string import Template

import pytest
from django.utils.translation import gettext_lazy as _
from guardian.shortcuts import assign_perm

from profiles.enums import AddressType, EmailType, PhoneType
from services.enums import ServiceType
from services.tests.factories import ServiceConnectionFactory
from subscriptions.models import Subscription
from subscriptions.tests.factories import (
    SubscriptionTypeCategoryFactory,
    SubscriptionTypeFactory,
)

from .factories import AddressFactory, EmailFactory, PhoneFactory, ProfileFactory


def test_normal_user_can_not_query_berth_profiles(rf, user_gql_client, service_factory):
    service_factory()
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    t = Template(
        """
        {
            profiles(serviceType: ${service_type}) {
                edges {
                    node {
                        firstName
                        lastName
                    }
                }
            }
        }
    """
    )
    query = t.substitute(service_type=ServiceType.BERTH.name)
    executed = user_gql_client.execute(query, context=request)
    assert "errors" in executed
    assert executed["errors"][0]["message"] == _(
        "You do not have permission to perform this action."
    )


def test_admin_user_can_query_berth_profiles(
    rf, superuser_gql_client, profile, service
):
    ServiceConnectionFactory(profile=profile, service=service)
    request = rf.post("/graphql")
    request.user = superuser_gql_client.user

    t = Template(
        """
        {
            profiles(serviceType: ${service_type}) {
                edges {
                    node {
                        firstName
                        lastName
                        nickname
                    }
                }
            }
        }
    """
    )
    query = t.substitute(service_type=ServiceType.BERTH.name)
    expected_data = {
        "profiles": {
            "edges": [
                {
                    "node": {
                        "firstName": profile.first_name,
                        "lastName": profile.last_name,
                        "nickname": profile.nickname,
                    }
                }
            ]
        }
    }
    executed = superuser_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data


def test_staff_user_with_group_access_can_query_berth_profiles(
    rf, user_gql_client, profile, group, service
):
    ServiceConnectionFactory(profile=profile, service=service)
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service)
    request = rf.post("/graphql")
    request.user = user

    t = Template(
        """
        {
            profiles(serviceType: ${service_type}) {
                edges {
                    node {
                        firstName
                    }
                }
            }
        }
    """
    )
    query = t.substitute(service_type=ServiceType.BERTH.name)
    expected_data = {
        "profiles": {"edges": [{"node": {"firstName": profile.first_name}}]}
    }
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data


def test_staff_user_can_filter_profiles_by_profile_ids(
    rf, user_gql_client, group, service
):
    profile_1, profile_2, profile_3 = ProfileFactory.create_batch(3)
    ServiceConnectionFactory(profile=profile_1, service=service)
    ServiceConnectionFactory(profile=profile_2, service=service)
    ServiceConnectionFactory(profile=profile_3, service=service)
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service)
    request = rf.post("/graphql")
    request.user = user

    query = """
        query getProfiles($serviceType: ServiceType!, $ids: [UUID!]!){
            profiles(serviceType: $serviceType, id: $ids) {
                count
                totalCount
            }
        }
    """

    expected_data = {"profiles": {"count": 2, "totalCount": 3}}

    executed = user_gql_client.execute(
        query,
        variables={
            "serviceType": ServiceType.BERTH.name,
            "ids": [str(profile_2.id), str(profile_1.id), str(uuid.uuid4())],
        },
        context=request,
    )
    assert "errors" not in executed
    assert dict(executed["data"]) == expected_data


def test_staff_user_can_filter_berth_profiles_by_first_name(
    rf, user_gql_client, group, service
):
    profile_1, profile_2 = ProfileFactory.create_batch(2)
    ServiceConnectionFactory(profile=profile_1, service=service)
    ServiceConnectionFactory(profile=profile_2, service=service)
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service)
    request = rf.post("/graphql")
    request.user = user

    query = """
        query getBerthProfiles($serviceType: ServiceType!, $firstName: String){
            profiles(serviceType: $serviceType, firstName: $firstName) {
                count
                totalCount
            }
        }
    """

    expected_data = {"profiles": {"count": 1, "totalCount": 2}}

    executed = user_gql_client.execute(
        query,
        variables={
            "serviceType": ServiceType.BERTH.name,
            "firstName": profile_2.first_name,
        },
        context=request,
    )
    assert "errors" not in executed
    assert dict(executed["data"]) == expected_data


def test_staff_user_can_sort_berth_profiles(rf, user_gql_client, group, service):
    profile_1, profile_2 = (
        ProfileFactory(first_name="Adam", last_name="Tester"),
        ProfileFactory(first_name="Bryan", last_name="Tester"),
    )
    ServiceConnectionFactory(profile=profile_1, service=service)
    ServiceConnectionFactory(profile=profile_2, service=service)
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service)
    request = rf.post("/graphql")
    request.user = user

    t = Template(
        """
        query getBerthProfiles {
            profiles(serviceType: ${service_type}, orderBy: "-firstName") {
                edges {
                    node {
                        firstName
                    }
                }
            }
        }
    """
    )
    query = t.substitute(service_type=ServiceType.BERTH.name)
    expected_data = {
        "profiles": {
            "edges": [{"node": {"firstName": "Bryan"}}, {"node": {"firstName": "Adam"}}]
        }
    }
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data


@pytest.mark.parametrize(
    "order_by",
    [
        "primaryAddress",
        "primaryCity",
        "primaryPostalCode",
        "primaryCountryCode",
        "primaryEmail",
    ],
)
def test_staff_user_can_sort_berth_profiles_by_custom_fields(
    rf, user_gql_client, group, service, order_by
):
    profile_1, profile_2 = (
        ProfileFactory(first_name="Adam", last_name="Tester"),
        ProfileFactory(first_name="Bryan", last_name="Tester"),
    )
    AddressFactory(
        profile=profile_1,
        city="Akaa",
        address="Autotie 1",
        postal_code="00100",
        country_code="FI",
        primary=True,
    ),
    AddressFactory(
        profile=profile_2,
        city="Ypäjä",
        address="Yrjönkatu 99",
        postal_code="99999",
        country_code="SE",
        primary=True,
    ),
    EmailFactory(profile=profile_1, email="adam.tester@example.com", primary=True,),
    EmailFactory(profile=profile_2, email="bryan.tester@example.com", primary=True,),
    ServiceConnectionFactory(profile=profile_1, service=service)
    ServiceConnectionFactory(profile=profile_2, service=service)
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service)
    request = rf.post("/graphql")
    request.user = user

    t = Template(
        """
        query getBerthProfiles {
            profiles(serviceType: ${service_type}, orderBy: \"${order_by}\") {
                edges {
                    node {
                        firstName
                    }
                }
            }
        }
    """
    )
    query = t.substitute(service_type=ServiceType.BERTH.name, order_by=order_by)
    expected_data = {
        "profiles": {
            "edges": [{"node": {"firstName": "Adam"}}, {"node": {"firstName": "Bryan"}}]
        }
    }
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data

    query = t.substitute(service_type=ServiceType.BERTH.name, order_by=f"-{order_by}")
    expected_data = {
        "profiles": {
            "edges": [{"node": {"firstName": "Bryan"}}, {"node": {"firstName": "Adam"}}]
        }
    }
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data


def test_staff_user_can_filter_berth_profiles_by_emails(
    rf, user_gql_client, group, service
):
    profile_1, profile_2, profile_3 = ProfileFactory.create_batch(3)
    EmailFactory(
        profile=profile_1, primary=True, email_type=EmailType.PERSONAL, verified=True
    )
    email = EmailFactory(profile=profile_2, primary=False, email_type=EmailType.WORK)
    EmailFactory(profile=profile_3, primary=False, email_type=EmailType.OTHER)
    ServiceConnectionFactory(profile=profile_1, service=service)
    ServiceConnectionFactory(profile=profile_2, service=service)
    ServiceConnectionFactory(profile=profile_3, service=service)
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service)
    request = rf.post("/graphql")
    request.user = user

    # filter by email

    query = """
        query getBerthProfiles($serviceType: ServiceType!, $email: String){
            profiles(serviceType: $serviceType, emails_Email: $email) {
                count
                totalCount
            }
        }
    """

    expected_data = {"profiles": {"count": 1, "totalCount": 3}}

    executed = user_gql_client.execute(
        query,
        variables={"serviceType": ServiceType.BERTH.name, "email": email.email},
        context=request,
    )
    assert dict(executed["data"]) == expected_data

    # filter by email_type

    query = """
        query getBerthProfiles($serviceType: ServiceType!, $emailType: String){
            profiles(serviceType: $serviceType, emails_EmailType: $emailType) {
                count
                totalCount
            }
        }
    """

    expected_data = {"profiles": {"count": 1, "totalCount": 3}}

    executed = user_gql_client.execute(
        query,
        variables={
            "serviceType": ServiceType.BERTH.name,
            "emailType": email.email_type.value,
        },
        context=request,
    )
    assert dict(executed["data"]) == expected_data

    # filter by primary

    query = """
        query getBerthProfiles($serviceType: ServiceType!, $primary: Boolean){
            profiles(serviceType: $serviceType, emails_Primary: $primary) {
                count
                totalCount
            }
        }
    """

    expected_data = {"profiles": {"count": 2, "totalCount": 3}}

    executed = user_gql_client.execute(
        query,
        variables={"serviceType": ServiceType.BERTH.name, "primary": False},
        context=request,
    )
    assert dict(executed["data"]) == expected_data

    # filter by verified

    query = """
        query getBerthProfiles($serviceType: ServiceType!, $verified: Boolean){
            profiles(serviceType: $serviceType, emails_Verified: $verified) {
                count
                totalCount
            }
        }
    """

    expected_data = {"profiles": {"count": 1, "totalCount": 3}}

    executed = user_gql_client.execute(
        query,
        variables={"serviceType": ServiceType.BERTH.name, "verified": True},
        context=request,
    )
    assert dict(executed["data"]) == expected_data


def test_staff_user_can_filter_berth_profiles_by_phones(
    rf, user_gql_client, group, service
):
    profile_1, profile_2, profile_3 = ProfileFactory.create_batch(3)
    PhoneFactory(profile=profile_1, primary=True, phone_type=PhoneType.HOME)
    phone = PhoneFactory(profile=profile_2, primary=False, phone_type=PhoneType.WORK)
    PhoneFactory(profile=profile_3, primary=False, phone_type=PhoneType.MOBILE)
    ServiceConnectionFactory(profile=profile_1, service=service)
    ServiceConnectionFactory(profile=profile_2, service=service)
    ServiceConnectionFactory(profile=profile_3, service=service)
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service)
    request = rf.post("/graphql")
    request.user = user

    # filter by phone

    query = """
        query getBerthProfiles($serviceType: ServiceType!, $phone: String){
            profiles(serviceType: $serviceType, phones_Phone: $phone) {
                count
                totalCount
            }
        }
    """

    expected_data = {"profiles": {"count": 1, "totalCount": 3}}

    executed = user_gql_client.execute(
        query,
        variables={"serviceType": ServiceType.BERTH.name, "phone": phone.phone},
        context=request,
    )
    assert dict(executed["data"]) == expected_data

    # filter by phone_type

    query = """
        query getBerthProfiles($serviceType: ServiceType!, $phoneType: String){
            profiles(serviceType: $serviceType, phones_PhoneType: $phoneType) {
                count
                totalCount
            }
        }
    """

    expected_data = {"profiles": {"count": 1, "totalCount": 3}}

    executed = user_gql_client.execute(
        query,
        variables={
            "serviceType": ServiceType.BERTH.name,
            "phoneType": phone.phone_type.value,
        },
        context=request,
    )
    assert dict(executed["data"]) == expected_data

    # filter by primary

    query = """
        query getBerthProfiles($serviceType: ServiceType!, $primary: Boolean){
            profiles(serviceType: $serviceType, phones_Primary: $primary) {
                count
                totalCount
            }
        }
    """

    expected_data = {"profiles": {"count": 2, "totalCount": 3}}

    executed = user_gql_client.execute(
        query,
        variables={"serviceType": ServiceType.BERTH.name, "primary": False},
        context=request,
    )
    assert dict(executed["data"]) == expected_data


def test_staff_user_can_filter_berth_profiles_by_addresses(
    rf, user_gql_client, group, service
):
    profile_1, profile_2, profile_3 = ProfileFactory.create_batch(3)
    AddressFactory(
        profile=profile_1,
        postal_code="00100",
        city="Helsinki",
        country_code="FI",
        primary=True,
        address_type=AddressType.HOME,
    )
    address = AddressFactory(
        profile=profile_2,
        postal_code="00100",
        city="Espoo",
        country_code="FI",
        primary=False,
        address_type=AddressType.WORK,
    )
    AddressFactory(
        profile=profile_3,
        postal_code="00200",
        city="Stockholm",
        country_code="SE",
        primary=False,
        address_type=AddressType.OTHER,
    )
    ServiceConnectionFactory(profile=profile_1, service=service)
    ServiceConnectionFactory(profile=profile_2, service=service)
    ServiceConnectionFactory(profile=profile_3, service=service)
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service)
    request = rf.post("/graphql")
    request.user = user

    # filter by address

    query = """
        query getBerthProfiles($serviceType: ServiceType!, $address: String){
            profiles(serviceType: $serviceType, addresses_Address: $address) {
                count
                totalCount
            }
        }
    """

    expected_data = {"profiles": {"count": 1, "totalCount": 3}}

    executed = user_gql_client.execute(
        query,
        variables={"serviceType": ServiceType.BERTH.name, "address": address.address},
        context=request,
    )
    assert dict(executed["data"]) == expected_data

    # filter by postal_code

    query = """
        query getBerthProfiles($serviceType: ServiceType!, $postalCode: String){
            profiles(serviceType: $serviceType, addresses_PostalCode: $postalCode) {
                count
                totalCount
            }
        }
    """

    expected_data = {"profiles": {"count": 2, "totalCount": 3}}

    executed = user_gql_client.execute(
        query,
        variables={
            "serviceType": ServiceType.BERTH.name,
            "postalCode": address.postal_code,
        },
        context=request,
    )
    assert dict(executed["data"]) == expected_data

    # filter by city

    query = """
        query getBerthProfiles($serviceType: ServiceType!, $city: String){
            profiles(serviceType: $serviceType, addresses_City: $city) {
                count
                totalCount
            }
        }
    """

    expected_data = {"profiles": {"count": 1, "totalCount": 3}}

    executed = user_gql_client.execute(
        query,
        variables={"serviceType": ServiceType.BERTH.name, "city": address.city},
        context=request,
    )
    assert dict(executed["data"]) == expected_data

    # filter by country code

    query = """
        query getBerthProfiles($serviceType: ServiceType!, $countryCode: String){
            profiles(serviceType: $serviceType, addresses_CountryCode: $countryCode) {
                count
                totalCount
            }
        }
    """

    expected_data = {"profiles": {"count": 2, "totalCount": 3}}

    executed = user_gql_client.execute(
        query,
        variables={
            "serviceType": ServiceType.BERTH.name,
            "countryCode": address.country_code,
        },
        context=request,
    )
    assert dict(executed["data"]) == expected_data

    # filter by address_type

    query = """
        query getBerthProfiles($serviceType: ServiceType!, $addressType: String){
            profiles(serviceType: $serviceType, addresses_AddressType: $addressType) {
                count
                totalCount
            }
        }
    """

    expected_data = {"profiles": {"count": 1, "totalCount": 3}}

    executed = user_gql_client.execute(
        query,
        variables={
            "serviceType": ServiceType.BERTH.name,
            "addressType": address.address_type.value,
        },
        context=request,
    )
    assert dict(executed["data"]) == expected_data

    # filter by primary

    query = """
        query getBerthProfiles($serviceType: ServiceType!, $primary: Boolean){
            profiles(serviceType: $serviceType, addresses_Primary: $primary) {
                count
                totalCount
            }
        }
    """

    expected_data = {"profiles": {"count": 2, "totalCount": 3}}

    executed = user_gql_client.execute(
        query,
        variables={"serviceType": ServiceType.BERTH.name, "primary": False},
        context=request,
    )
    assert dict(executed["data"]) == expected_data


def test_staff_user_can_filter_berth_profiles_by_subscriptions_and_postal_code(
    rf, user_gql_client, group, service
):
    def generate_expected_data(profiles):
        return {
            "profiles": {
                "edges": [
                    {
                        "node": {
                            "emails": {
                                "edges": [
                                    {"node": {"email": profile.emails.first().email}}
                                ]
                            },
                            "phones": {
                                "edges": [
                                    {"node": {"phone": profile.phones.first().phone}}
                                ]
                            },
                        }
                    }
                    for profile in profiles
                ]
            }
        }

    profile_1, profile_2, profile_3, profile_4 = ProfileFactory.create_batch(4)
    PhoneFactory(profile=profile_1, phone="0401234561", primary=True)
    PhoneFactory(profile=profile_2, phone="0401234562", primary=True)
    PhoneFactory(profile=profile_3, phone="0401234563", primary=True)
    PhoneFactory(profile=profile_4, phone="0401234564", primary=True)

    EmailFactory(profile=profile_1, email="first@example.com", primary=True)
    EmailFactory(profile=profile_2, email="second@example.com", primary=True)
    EmailFactory(profile=profile_3, email="third@example.com", primary=True)
    EmailFactory(profile=profile_4, email="fourth@example.com", primary=True)

    AddressFactory(profile=profile_1, primary=True, postal_code="00100")
    AddressFactory(profile=profile_2, postal_code="00100")
    AddressFactory(profile=profile_3, postal_code="00100")
    AddressFactory(profile=profile_4, postal_code="00200")

    cat = SubscriptionTypeCategoryFactory(code="TEST-CATEGORY-1")
    type_1 = SubscriptionTypeFactory(subscription_type_category=cat, code="TEST-1")
    type_2 = SubscriptionTypeFactory(subscription_type_category=cat, code="TEST-2")

    Subscription.objects.create(
        profile=profile_1, subscription_type=type_1, enabled=True
    )
    Subscription.objects.create(
        profile=profile_1, subscription_type=type_2, enabled=True
    )

    Subscription.objects.create(
        profile=profile_2, subscription_type=type_1, enabled=True
    )
    Subscription.objects.create(
        profile=profile_2, subscription_type=type_2, enabled=False
    )

    Subscription.objects.create(
        profile=profile_3, subscription_type=type_1, enabled=True
    )

    Subscription.objects.create(
        profile=profile_4, subscription_type=type_2, enabled=True
    )

    ServiceConnectionFactory(profile=profile_1, service=service)
    ServiceConnectionFactory(profile=profile_2, service=service)
    ServiceConnectionFactory(profile=profile_3, service=service)
    ServiceConnectionFactory(profile=profile_4, service=service)
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service)
    request = rf.post("/graphql")
    request.user = user

    query = """
        query getBerthProfiles($serviceType: ServiceType!, $subscriptionType: String, $postalCode: String){
            profiles(
                serviceType: $serviceType,
                enabledSubscriptions: $subscriptionType,
                addresses_PostalCode: $postalCode
            ) {
                edges {
                    node {
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
                    }
                }
            }
        }
    """

    # test for type 1 + postal code 00100

    executed = user_gql_client.execute(
        query,
        variables={
            "serviceType": ServiceType.BERTH.name,
            "subscriptionType": type_1.code,
            "postalCode": "00100",
        },
        context=request,
    )
    assert dict(executed["data"]) == generate_expected_data(
        [profile_1, profile_2, profile_3]
    )

    # test for type 2 + postal code 00100

    executed = user_gql_client.execute(
        query,
        variables={
            "serviceType": ServiceType.BERTH.name,
            "subscriptionType": type_2.code,
            "postalCode": "00100",
        },
        context=request,
    )
    assert dict(executed["data"]) == generate_expected_data([profile_1])


def test_staff_user_can_paginate_berth_profiles(rf, user_gql_client, group, service):
    profile_1, profile_2 = (
        ProfileFactory(first_name="Adam", last_name="Tester"),
        ProfileFactory(first_name="Bryan", last_name="Tester"),
    )
    ServiceConnectionFactory(profile=profile_1, service=service)
    ServiceConnectionFactory(profile=profile_2, service=service)
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service)
    request = rf.post("/graphql")
    request.user = user

    query = """
        query getBerthProfiles {
            profiles(serviceType: BERTH, orderBy: "firstName", first: 1) {
                pageInfo {
                    endCursor
                }
                edges {
                    node {
                        firstName
                    }
                }
            }
        }
    """

    expected_data = {"edges": [{"node": {"firstName": "Adam"}}]}
    executed = user_gql_client.execute(query, context=request)
    assert "data" in executed
    assert executed["data"]["profiles"]["edges"] == expected_data["edges"]
    assert "pageInfo" in executed["data"]["profiles"]
    assert "endCursor" in executed["data"]["profiles"]["pageInfo"]

    end_cursor = executed["data"]["profiles"]["pageInfo"]["endCursor"]

    query = """
        query getBerthProfiles($endCursor: String){
            profiles(serviceType: BERTH, first: 1, after: $endCursor) {
                edges {
                    node {
                        firstName
                    }
                }
            }
        }
    """
    expected_data = {"edges": [{"node": {"firstName": "Bryan"}}]}
    executed = user_gql_client.execute(
        query, variables={"endCursor": end_cursor}, context=request
    )
    assert "data" in executed
    assert executed["data"]["profiles"] == expected_data


def test_staff_user_with_group_access_can_query_only_profiles_he_has_access_to(
    rf, user_gql_client, group, service_factory
):
    profile_berth = ProfileFactory()
    profile_youth = ProfileFactory()
    service_berth = service_factory(service_type=ServiceType.BERTH)
    service_youth = service_factory(service_type=ServiceType.YOUTH_MEMBERSHIP)
    ServiceConnectionFactory(profile=profile_berth, service=service_berth)
    ServiceConnectionFactory(profile=profile_youth, service=service_youth)
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service_berth)
    request = rf.post("/graphql")
    request.user = user

    t = Template(
        """
        {
            profiles(serviceType: ${service_type}) {
                edges {
                    node {
                        firstName
                    }
                }
            }
        }
    """
    )
    query = t.substitute(service_type=ServiceType.BERTH.name)
    expected_data = {
        "profiles": {"edges": [{"node": {"firstName": profile_berth.first_name}}]}
    }
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data

    t = Template(
        """
        {
            profiles(serviceType: ${service_type}) {
                edges {
                    node {
                        firstName
                    }
                }
            }
        }
    """
    )
    query = t.substitute(service_type=ServiceType.YOUTH_MEMBERSHIP.name)
    executed = user_gql_client.execute(query, context=request)
    assert "errors" in executed
    assert executed["errors"][0]["message"] == _(
        "You do not have permission to perform this action."
    )
