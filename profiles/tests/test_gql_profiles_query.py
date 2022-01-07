import uuid
from string import Template

import pytest
from django.utils.translation import gettext_lazy as _
from guardian.shortcuts import assign_perm

from open_city_profile.tests import to_graphql_name
from open_city_profile.tests.asserts import assert_match_error_code
from profiles.enums import AddressType, EmailType, PhoneType
from services.tests.factories import ServiceConnectionFactory

from .factories import (
    AddressFactory,
    EmailFactory,
    PhoneFactory,
    ProfileFactory,
    VerifiedPersonalInformationFactory,
)


def test_normal_user_can_not_query_profiles(user_gql_client, service):
    query = """
        {
            profiles {
                edges {
                    node {
                        firstName
                        lastName
                    }
                }
            }
        }
    """
    executed = user_gql_client.execute(query, service=service)
    assert "errors" in executed
    assert executed["errors"][0]["message"] == _(
        "You do not have permission to perform this action."
    )


def test_admin_user_can_query_profiles(superuser_gql_client, profile, service):
    ServiceConnectionFactory(profile=profile, service=service)

    query = """
        {
            profiles {
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
    executed = superuser_gql_client.execute(query, service=service)
    assert executed["data"] == expected_data


def test_staff_user_with_group_access_can_query_profiles(
    user_gql_client, profile, group, service
):
    ServiceConnectionFactory(profile=profile, service=service)
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service)

    # serviceType is included in query just to ensure that it has NO affect
    query = """
        {
            profiles(serviceType: GODCHILDREN_OF_CULTURE) {
                edges {
                    node {
                        firstName
                    }
                }
            }
        }
    """

    expected_data = {
        "profiles": {"edges": [{"node": {"firstName": profile.first_name}}]}
    }
    executed = user_gql_client.execute(query, service=service)
    assert executed["data"] == expected_data


def test_staff_user_can_filter_profiles_by_profile_ids(user_gql_client, group, service):
    profile_1, profile_2, profile_3 = ProfileFactory.create_batch(3)
    ServiceConnectionFactory(profile=profile_1, service=service)
    ServiceConnectionFactory(profile=profile_2, service=service)
    ServiceConnectionFactory(profile=profile_3, service=service)
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service)

    query = """
        query getProfiles($ids: [UUID!]!) {
            profiles(id: $ids) {
                count
                totalCount
            }
        }
    """

    expected_data = {"profiles": {"count": 2, "totalCount": 3}}

    executed = user_gql_client.execute(
        query,
        variables={"ids": [str(profile_2.id), str(profile_1.id), str(uuid.uuid4())]},
        service=service,
    )
    assert "errors" not in executed
    assert executed["data"] == expected_data


query_template = Template(
    """
        query getProfiles($$searchString: String) {
            profiles(${search_arg_name}: $$searchString) {
                count
                totalCount
                edges {
                    node {
                        firstName
                    }
                }
            }
        }
    """
)


@pytest.mark.parametrize("field_name", ["first_name", "last_name"])
def test_staff_user_can_filter_profiles_by_a_field(
    field_name, user_gql_client, group, service
):
    profile_1, profile_2 = ProfileFactory.create_batch(2)
    ServiceConnectionFactory(profile=profile_1, service=service)
    ServiceConnectionFactory(profile=profile_2, service=service)
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service)

    gql_field_name = to_graphql_name(field_name)
    query = query_template.substitute(search_arg_name=gql_field_name)

    expected_data = {
        "profiles": {
            "count": 1,
            "totalCount": 2,
            "edges": [{"node": {"firstName": profile_2.first_name}}],
        }
    }

    search_term = getattr(profile_2, field_name)[1:].upper()
    executed = user_gql_client.execute(
        query, variables={"searchString": search_term}, service=service,
    )
    assert "errors" not in executed
    assert executed["data"] == expected_data


@pytest.mark.parametrize("amr_claim_value", [None, 0, "authmethod1", "foo"])
@pytest.mark.parametrize("has_needed_permission", [True, False])
def test_staff_user_filter_profiles_by_verified_personal_information_permissions(
    has_needed_permission, amr_claim_value, settings, user_gql_client, group, service
):
    settings.VERIFIED_PERSONAL_INFORMATION_ACCESS_AMR_LIST = [
        "authmethod1",
        "authmethod2",
    ]

    vpi = VerifiedPersonalInformationFactory()
    ServiceConnectionFactory(profile=vpi.profile, service=service)

    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service)
    if has_needed_permission:
        assign_perm("can_view_verified_personal_information", group, service)

    gql_field_name = to_graphql_name("national_identification_number")
    query = query_template.substitute(search_arg_name=gql_field_name)

    expected_data_no_permission = {
        "profiles": {"count": 0, "totalCount": 1, "edges": []}
    }
    expected_data_with_permission = {
        "profiles": {
            "count": 1,
            "totalCount": 1,
            "edges": [{"node": {"firstName": vpi.profile.first_name}}],
        }
    }

    token_payload = {"amr": amr_claim_value}
    executed = user_gql_client.execute(
        query,
        variables={"searchString": vpi.national_identification_number},
        auth_token_payload=token_payload,
        service=service,
    )

    assert "errors" not in executed
    if (
        has_needed_permission
        and amr_claim_value in settings.VERIFIED_PERSONAL_INFORMATION_ACCESS_AMR_LIST
    ):
        assert executed["data"] == expected_data_with_permission
    else:
        assert executed["data"] == expected_data_no_permission


def test_staff_user_can_sort_profiles(user_gql_client, group, service):
    profile_1, profile_2 = (
        ProfileFactory(first_name="Adam", last_name="Tester"),
        ProfileFactory(first_name="Bryan", last_name="Tester"),
    )
    ServiceConnectionFactory(profile=profile_1, service=service)
    ServiceConnectionFactory(profile=profile_2, service=service)
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service)

    query = """
        query getProfiles {
            profiles(orderBy: "-firstName") {
                edges {
                    node {
                        firstName
                    }
                }
            }
        }
    """

    expected_data = {
        "profiles": {
            "edges": [{"node": {"firstName": "Bryan"}}, {"node": {"firstName": "Adam"}}]
        }
    }
    executed = user_gql_client.execute(query, service=service)
    assert executed["data"] == expected_data


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
def test_staff_user_can_sort_profiles_by_custom_fields(
    user_gql_client, group, service, order_by
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
    )
    AddressFactory(
        profile=profile_2,
        city="Ypäjä",
        address="Yrjönkatu 99",
        postal_code="99999",
        country_code="SE",
        primary=True,
    )
    EmailFactory(profile=profile_1, email="adam.tester@example.com", primary=True)
    EmailFactory(profile=profile_2, email="bryan.tester@example.com", primary=True)
    ServiceConnectionFactory(profile=profile_1, service=service)
    ServiceConnectionFactory(profile=profile_2, service=service)
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service)

    t = Template(
        """
        query getProfiles {
            profiles(orderBy: "${order_by}") {
                edges {
                    node {
                        firstName
                    }
                }
            }
        }
    """
    )
    query = t.substitute(order_by=order_by)
    expected_data = {
        "profiles": {
            "edges": [{"node": {"firstName": "Adam"}}, {"node": {"firstName": "Bryan"}}]
        }
    }
    executed = user_gql_client.execute(query, service=service)
    assert executed["data"] == expected_data

    query = t.substitute(order_by=f"-{order_by}")
    expected_data = {
        "profiles": {
            "edges": [{"node": {"firstName": "Bryan"}}, {"node": {"firstName": "Adam"}}]
        }
    }
    executed = user_gql_client.execute(query, service=service)
    assert executed["data"] == expected_data


def test_staff_user_can_filter_profiles_by_emails(user_gql_client, group, service):
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

    # filter by email

    query = """
        query getProfiles($email: String) {
            profiles(emails_Email: $email) {
                count
                totalCount
            }
        }
    """

    expected_data = {"profiles": {"count": 1, "totalCount": 3}}

    executed = user_gql_client.execute(
        query, variables={"email": email.email}, service=service,
    )
    assert executed["data"] == expected_data

    # filter by email_type

    query = """
        query getProfiles($emailType: String) {
            profiles(emails_EmailType: $emailType) {
                count
                totalCount
            }
        }
    """

    expected_data = {"profiles": {"count": 1, "totalCount": 3}}

    executed = user_gql_client.execute(
        query, variables={"emailType": email.email_type.value}, service=service,
    )
    assert executed["data"] == expected_data

    # filter by primary

    query = """
        query getProfiles($primary: Boolean) {
            profiles(emails_Primary: $primary) {
                count
                totalCount
            }
        }
    """

    expected_data = {"profiles": {"count": 2, "totalCount": 3}}

    executed = user_gql_client.execute(
        query, variables={"primary": False}, service=service,
    )
    assert executed["data"] == expected_data

    # filter by verified

    query = """
        query getProfiles($verified: Boolean) {
            profiles(emails_Verified: $verified) {
                count
                totalCount
            }
        }
    """

    expected_data = {"profiles": {"count": 1, "totalCount": 3}}

    executed = user_gql_client.execute(
        query, variables={"verified": True}, service=service,
    )
    assert executed["data"] == expected_data


def test_staff_user_can_filter_profiles_by_phones(user_gql_client, group, service):
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

    # filter by phone

    query = """
        query getProfiles($phone: String) {
            profiles(phones_Phone: $phone) {
                count
                totalCount
            }
        }
    """

    expected_data = {"profiles": {"count": 1, "totalCount": 3}}

    executed = user_gql_client.execute(
        query, variables={"phone": phone.phone}, service=service,
    )
    assert executed["data"] == expected_data

    # filter by phone_type

    query = """
        query getProfiles($phoneType: String) {
            profiles(phones_PhoneType: $phoneType) {
                count
                totalCount
            }
        }
    """

    expected_data = {"profiles": {"count": 1, "totalCount": 3}}

    executed = user_gql_client.execute(
        query, variables={"phoneType": phone.phone_type.value}, service=service,
    )
    assert executed["data"] == expected_data

    # filter by primary

    query = """
        query getProfiles($primary: Boolean) {
            profiles(phones_Primary: $primary) {
                count
                totalCount
            }
        }
    """

    expected_data = {"profiles": {"count": 2, "totalCount": 3}}

    executed = user_gql_client.execute(
        query, variables={"primary": False}, service=service,
    )
    assert executed["data"] == expected_data


def test_staff_user_can_filter_profiles_by_addresses(user_gql_client, group, service):
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

    # filter by address

    query = """
        query getProfiles($address: String) {
            profiles(addresses_Address: $address) {
                count
                totalCount
            }
        }
    """

    expected_data = {"profiles": {"count": 1, "totalCount": 3}}

    executed = user_gql_client.execute(
        query, variables={"address": address.address}, service=service,
    )
    assert executed["data"] == expected_data

    # filter by postal_code

    query = """
        query getProfiles($postalCode: String) {
            profiles(addresses_PostalCode: $postalCode) {
                count
                totalCount
            }
        }
    """

    expected_data = {"profiles": {"count": 2, "totalCount": 3}}

    executed = user_gql_client.execute(
        query, variables={"postalCode": address.postal_code}, service=service,
    )
    assert executed["data"] == expected_data

    # filter by city

    query = """
        query getProfiles($city: String) {
            profiles(addresses_City: $city) {
                count
                totalCount
            }
        }
    """

    expected_data = {"profiles": {"count": 1, "totalCount": 3}}

    executed = user_gql_client.execute(
        query, variables={"city": address.city}, service=service,
    )
    assert executed["data"] == expected_data

    # filter by country code

    query = """
        query getProfiles($countryCode: String) {
            profiles(addresses_CountryCode: $countryCode) {
                count
                totalCount
            }
        }
    """

    expected_data = {"profiles": {"count": 2, "totalCount": 3}}

    executed = user_gql_client.execute(
        query, variables={"countryCode": address.country_code}, service=service,
    )
    assert executed["data"] == expected_data

    # filter by address_type

    query = """
        query getProfiles($addressType: String) {
            profiles(addresses_AddressType: $addressType) {
                count
                totalCount
            }
        }
    """

    expected_data = {"profiles": {"count": 1, "totalCount": 3}}

    executed = user_gql_client.execute(
        query, variables={"addressType": address.address_type.value}, service=service,
    )
    assert executed["data"] == expected_data

    # filter by primary

    query = """
        query getProfiles($primary: Boolean) {
            profiles(addresses_Primary: $primary) {
                count
                totalCount
            }
        }
    """

    expected_data = {"profiles": {"count": 2, "totalCount": 3}}

    executed = user_gql_client.execute(
        query, variables={"primary": False}, service=service,
    )
    assert executed["data"] == expected_data


def test_filtering_profiles_by_subscriptions_has_no_effect(
    user_gql_client, group, service
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

    ServiceConnectionFactory(profile=profile_1, service=service)
    ServiceConnectionFactory(profile=profile_2, service=service)
    ServiceConnectionFactory(profile=profile_3, service=service)
    ServiceConnectionFactory(profile=profile_4, service=service)
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service)

    query = """
        query getProfiles($subscriptionType: String, $postalCode: String) {
            profiles(
                enabledSubscriptions: $subscriptionType,
                addresses_PostalCode: $postalCode,
                orderBy: "firstName"
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

    executed = user_gql_client.execute(
        query,
        variables={"subscriptionType": "whatever", "postalCode": "00100"},
        service=service,
    )
    profiles_ordered_by_first_name = sorted(
        [profile_1, profile_2, profile_3], key=lambda p: p.first_name
    )
    assert executed["data"] == generate_expected_data(profiles_ordered_by_first_name)


# Profiles are ordered by their id field if no other ordering is requested
@pytest.mark.parametrize(
    "order_by,expected_order",
    [(None, ("Bryan", "Clive", "Adam")), ("firstName", ("Adam", "Bryan", "Clive"))],
)
def test_staff_user_can_paginate_profiles(
    order_by, expected_order, user_gql_client, group, service
):
    for profile in (
        ProfileFactory(
            id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
            first_name="Clive",
            last_name="Tester",
        ),
        ProfileFactory(
            id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
            first_name="Adam",
            last_name="Tester",
        ),
        ProfileFactory(
            id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            first_name="Bryan",
            last_name="Tester",
        ),
    ):
        ServiceConnectionFactory(profile=profile, service=service)

    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service)

    query = """
        query getProfiles($orderBy: String, $after: String) {
            profiles(orderBy: $orderBy, first: 1, after: $after) {
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

    end_cursor = None
    for expected_first_name in expected_order:
        executed = user_gql_client.execute(
            query, variables={"orderBy": order_by, "after": end_cursor}, service=service
        )

        expected_edges = [{"node": {"firstName": expected_first_name}}]
        assert "data" in executed
        assert executed["data"]["profiles"]["edges"] == expected_edges
        assert "pageInfo" in executed["data"]["profiles"]
        assert "endCursor" in executed["data"]["profiles"]["pageInfo"]
        end_cursor = executed["data"]["profiles"]["pageInfo"]["endCursor"]


def test_staff_user_with_group_access_can_query_only_profiles_he_has_access_to(
    user_gql_client, group, service_factory
):
    user = user_gql_client.user
    user.groups.add(group)

    entitled_profile = ProfileFactory()
    entitled_service = service_factory()
    ServiceConnectionFactory(profile=entitled_profile, service=entitled_service)
    assign_perm("can_view_profiles", group, entitled_service)

    unentitled_profile = ProfileFactory()
    unentitled_service = service_factory()
    ServiceConnectionFactory(profile=unentitled_profile, service=unentitled_service)

    query = """
        {
            profiles {
                edges {
                    node {
                        firstName
                    }
                }
            }
        }
    """

    executed = user_gql_client.execute(query, service=entitled_service)
    expected_data = {
        "profiles": {"edges": [{"node": {"firstName": entitled_profile.first_name}}]}
    }
    assert executed["data"] == expected_data

    executed = user_gql_client.execute(query, service=unentitled_service)
    assert "errors" in executed
    assert executed["errors"][0]["message"] == _(
        "You do not have permission to perform this action."
    )


def test_not_specifying_requesters_service_results_in_permission_denied_error(
    user_gql_client,
):
    query = """
        {
            profiles {
                edges {
                    node {
                        firstName
                    }
                }
            }
        }
    """
    executed = user_gql_client.execute(query)
    assert_match_error_code(executed, "PERMISSION_DENIED_ERROR")
