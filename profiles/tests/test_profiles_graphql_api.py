from string import Template

from django.utils.translation import ugettext_lazy as _
from graphene import relay
from graphql_relay.node.node import to_global_id
from guardian.shortcuts import assign_perm

from open_city_profile.consts import OBJECT_DOES_NOT_EXIST_ERROR
from open_city_profile.tests.factories import GroupFactory
from services.enums import ServiceType
from services.tests.factories import ServiceConnectionFactory, ServiceFactory

from ..schema import ProfileNode
from .factories import AddressFactory, EmailFactory, PhoneFactory, ProfileFactory


def test_normal_user_can_create_profile(rf, user_gql_client, email_data, profile_data):
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    t = Template(
        """
            mutation {
                createProfile(
                    profile: {
                        nickname: \"${nickname}\",
                        addEmails:[
                            {emailType: ${email_type}, email:\"${email}\", primary: ${primary}}
                        ]
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
                        }
                        }
                    }
                }
            }
            }
        """
    )

    expected_data = {
        "createProfile": {
            "profile": {
                "nickname": profile_data["nickname"],
                "emails": {
                    "edges": [
                        {
                            "node": {
                                "email": email_data["email"],
                                "emailType": email_data["email_type"],
                                "primary": email_data["primary"],
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


def test_normal_user_can_update_profile(rf, user_gql_client, email_data, profile_data):
    profile = ProfileFactory(user=user_gql_client.user)
    email = EmailFactory(profile=profile)
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    t = Template(
        """
            mutation {
                updateProfile(
                    profile: {
                        nickname: \"${nickname}\",
                        updateEmails:[
                            {
                                id: \"${email_id}\",
                                emailType: ${email_type},
                                email:\"${email}\",
                                primary: ${primary}
                            }
                        ]
                    }
                ) {
                    profile{
                        nickname,
                        emails{
                            edges{
                            node{
                                id
                                email
                                emailType
                                primary
                            }
                            }
                        }
                    }
                }
            }
        """
    )

    expected_data = {
        "updateProfile": {
            "profile": {
                "nickname": profile_data["nickname"],
                "emails": {
                    "edges": [
                        {
                            "node": {
                                "id": to_global_id(type="EmailNode", id=email.id),
                                "email": email_data["email"],
                                "emailType": email_data["email_type"],
                                "primary": email_data["primary"],
                            }
                        }
                    ]
                },
            }
        }
    }

    mutation = t.substitute(
        nickname=profile_data["nickname"],
        email_id=to_global_id(type="EmailNode", id=email.id),
        email=email_data["email"],
        email_type=email_data["email_type"],
        primary=str(email_data["primary"]).lower(),
    )
    executed = user_gql_client.execute(mutation, context=request)
    assert dict(executed["data"]) == expected_data


def test_normal_user_can_add_email(rf, user_gql_client, email_data):
    ProfileFactory(user=user_gql_client.user)
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    t = Template(
        """
            mutation {
                updateProfile(
                    profile: {
                    addEmails:[
                        {emailType: ${email_type}, email:\"${email}\", primary: ${primary}}
                    ]
                }
            ) {
                profile{
                    emails{
                        edges{
                        node{
                            email
                            emailType
                            primary
                        }
                        }
                    }
                }
            }
            }
        """
    )

    expected_data = {
        "updateProfile": {
            "profile": {
                "emails": {
                    "edges": [
                        {
                            "node": {
                                "email": email_data["email"],
                                "emailType": email_data["email_type"],
                                "primary": email_data["primary"],
                            }
                        }
                    ]
                }
            }
        }
    }

    mutation = t.substitute(
        email=email_data["email"],
        email_type=email_data["email_type"],
        primary=str(email_data["primary"]).lower(),
    )
    executed = user_gql_client.execute(mutation, context=request)
    assert dict(executed["data"]) == expected_data


def test_normal_user_can_add_phone(rf, user_gql_client, phone_data):
    ProfileFactory(user=user_gql_client.user)
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    t = Template(
        """
            mutation {
                updateProfile(
                    profile: {
                    addPhones:[
                        {phoneType: ${phone_type}, phone:\"${phone}\", primary: ${primary}}
                    ]
                }
            ) {
                profile{
                    phones{
                        edges{
                        node{
                            phone
                            phoneType
                            primary
                        }
                        }
                    }
                }
            }
            }
        """
    )

    expected_data = {
        "updateProfile": {
            "profile": {
                "phones": {
                    "edges": [
                        {
                            "node": {
                                "phone": phone_data["phone"],
                                "phoneType": phone_data["phone_type"],
                                "primary": phone_data["primary"],
                            }
                        }
                    ]
                }
            }
        }
    }

    mutation = t.substitute(
        phone=phone_data["phone"],
        phone_type=phone_data["phone_type"],
        primary=str(phone_data["primary"]).lower(),
    )
    executed = user_gql_client.execute(mutation, context=request)
    assert dict(executed["data"]) == expected_data


def test_normal_user_can_add_address(rf, user_gql_client, address_data):
    ProfileFactory(user=user_gql_client.user)
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    t = Template(
        """
            mutation {
                updateProfile(
                    profile: {
                    addAddresses:[
                        {
                            addressType: ${address_type},
                            address:\"${address}\",
                            postalCode: \"${postal_code}\",
                            city: \"${city}\",
                            countryCode: \"${country_code}\",
                            primary: ${primary}
                        }
                    ]
                }
            ) {
                profile{
                    addresses{
                        edges{
                        node{
                            address
                            postalCode
                            city
                            countryCode
                            addressType
                            primary
                        }
                        }
                    }
                }
            }
            }
        """
    )

    expected_data = {
        "updateProfile": {
            "profile": {
                "addresses": {
                    "edges": [
                        {
                            "node": {
                                "address": address_data["address"],
                                "postalCode": address_data["postal_code"],
                                "city": address_data["city"],
                                "countryCode": address_data["country_code"],
                                "addressType": address_data["address_type"],
                                "primary": address_data["primary"],
                            }
                        }
                    ]
                }
            }
        }
    }

    mutation = t.substitute(
        address=address_data["address"],
        postal_code=address_data["postal_code"],
        city=address_data["city"],
        country_code=address_data["country_code"],
        address_type=address_data["address_type"],
        primary=str(address_data["primary"]).lower(),
    )
    executed = user_gql_client.execute(mutation, context=request)
    assert dict(executed["data"]) == expected_data


def test_normal_user_can_update_address(rf, user_gql_client, address_data):
    profile = ProfileFactory(user=user_gql_client.user)
    address = AddressFactory(profile=profile)
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    t = Template(
        """
            mutation {
                updateProfile(
                    profile: {
                    updateAddresses:[
                        {
                            id: \"${address_id}\",
                            addressType: ${address_type},
                            address:\"${address}\",
                            postalCode:\"${postal_code}\",
                            city:\"${city}\",
                            primary: ${primary}
                        }
                    ]
                }
            ) {
                profile{
                    addresses{
                        edges{
                        node{
                            id
                            address
                            postalCode
                            city
                            addressType
                            primary
                        }
                        }
                    }
                }
            }
            }
        """
    )

    expected_data = {
        "updateProfile": {
            "profile": {
                "addresses": {
                    "edges": [
                        {
                            "node": {
                                "id": to_global_id(type="AddressNode", id=address.id),
                                "address": address_data["address"],
                                "postalCode": address_data["postal_code"],
                                "city": address_data["city"],
                                "addressType": address_data["address_type"],
                                "primary": address_data["primary"],
                            }
                        }
                    ]
                }
            }
        }
    }

    mutation = t.substitute(
        address_id=to_global_id(type="AddressNode", id=address.id),
        address=address_data["address"],
        postal_code=address_data["postal_code"],
        city=address_data["city"],
        address_type=address_data["address_type"],
        primary=str(address_data["primary"]).lower(),
    )
    executed = user_gql_client.execute(mutation, context=request)
    assert dict(executed["data"]) == expected_data


def test_normal_user_can_update_email(rf, user_gql_client, email_data):
    profile = ProfileFactory(user=user_gql_client.user)
    email = EmailFactory(profile=profile)
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    t = Template(
        """
            mutation {
                updateProfile(
                    profile: {
                    updateEmails:[
                        {
                            id: \"${email_id}\",
                            emailType: ${email_type},
                            email:\"${email}\",
                            primary: ${primary}
                        }
                    ]
                }
            ) {
                profile{
                    emails{
                        edges{
                        node{
                            id
                            email
                            emailType
                            primary
                        }
                        }
                    }
                }
            }
            }
        """
    )

    expected_data = {
        "updateProfile": {
            "profile": {
                "emails": {
                    "edges": [
                        {
                            "node": {
                                "id": to_global_id(type="EmailNode", id=email.id),
                                "email": email_data["email"],
                                "emailType": email_data["email_type"],
                                "primary": email_data["primary"],
                            }
                        }
                    ]
                }
            }
        }
    }

    mutation = t.substitute(
        email_id=to_global_id(type="EmailNode", id=email.id),
        email=email_data["email"],
        email_type=email_data["email_type"],
        primary=str(email_data["primary"]).lower(),
    )
    executed = user_gql_client.execute(mutation, context=request)
    assert dict(executed["data"]) == expected_data


def test_normal_user_can_update_phone(rf, user_gql_client, phone_data):
    profile = ProfileFactory(user=user_gql_client.user)
    phone = PhoneFactory(profile=profile)
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    t = Template(
        """
            mutation {
                updateProfile(
                    profile: {
                    updatePhones:[
                        {
                            id: \"${phone_id}\",
                            phoneType: ${phone_type},
                            phone:\"${phone}\",
                            primary: ${primary}
                        }
                    ]
                }
            ) {
                profile{
                    phones{
                        edges{
                        node{
                            id
                            phone
                            phoneType
                            primary
                        }
                        }
                    }
                }
            }
            }
        """
    )

    expected_data = {
        "updateProfile": {
            "profile": {
                "phones": {
                    "edges": [
                        {
                            "node": {
                                "id": to_global_id(type="PhoneNode", id=phone.id),
                                "phone": phone_data["phone"],
                                "phoneType": phone_data["phone_type"],
                                "primary": phone_data["primary"],
                            }
                        }
                    ]
                }
            }
        }
    }

    mutation = t.substitute(
        phone_id=to_global_id(type="PhoneNode", id=phone.id),
        phone=phone_data["phone"],
        phone_type=phone_data["phone_type"],
        primary=str(phone_data["primary"]).lower(),
    )
    executed = user_gql_client.execute(mutation, context=request)
    assert dict(executed["data"]) == expected_data


def test_normal_user_can_remove_email(rf, user_gql_client, email_data):
    profile = ProfileFactory(user=user_gql_client.user)
    email = EmailFactory(profile=profile)
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    t = Template(
        """
            mutation {
                updateProfile(
                    profile: {
                    removeEmails:[
                        \"${email_id}\"
                    ]
                }
            ) {
                profile{
                    emails{
                        edges{
                        node{
                            id
                            email
                            emailType
                            primary
                        }
                        }
                    }
                }
            }
            }
        """
    )

    expected_data = {"updateProfile": {"profile": {"emails": {"edges": []}}}}

    mutation = t.substitute(
        email_id=to_global_id(type="EmailNode", id=email.id),
        email=email_data["email"],
        email_type=email_data["email_type"],
        primary=str(email_data["primary"]).lower(),
    )
    executed = user_gql_client.execute(mutation, context=request)
    assert dict(executed["data"]) == expected_data


def test_normal_user_can_remove_phone(rf, user_gql_client, phone_data):
    profile = ProfileFactory(user=user_gql_client.user)
    phone = PhoneFactory(profile=profile)
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    t = Template(
        """
            mutation {
                updateProfile(
                    profile: {
                    removePhones:[
                        \"${phone_id}\"
                    ]
                }
            ) {
                profile{
                    phones{
                        edges{
                        node{
                            id
                            phone
                            phoneType
                            primary
                        }
                        }
                    }
                }
            }
            }
        """
    )

    expected_data = {"updateProfile": {"profile": {"phones": {"edges": []}}}}

    mutation = t.substitute(
        phone_id=to_global_id(type="PhoneNode", id=phone.id),
        phone=phone_data["phone"],
        phone_type=phone_data["phone_type"],
        primary=str(phone_data["primary"]).lower(),
    )
    executed = user_gql_client.execute(mutation, context=request)
    assert dict(executed["data"]) == expected_data


def test_normal_user_can_remove_address(rf, user_gql_client, address_data):
    profile = ProfileFactory(user=user_gql_client.user)
    address = AddressFactory(profile=profile)
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    t = Template(
        """
            mutation {
                updateProfile(
                    profile: {
                    removeAddresses:[
                        \"${address_id}\"
                    ]
                }
            ) {
                profile{
                    addresses{
                        edges{
                        node{
                            id
                            address
                            addressType
                            primary
                        }
                        }
                    }
                }
            }
            }
        """
    )

    expected_data = {"updateProfile": {"profile": {"addresses": {"edges": []}}}}

    mutation = t.substitute(
        address_id=to_global_id(type="AddressNode", id=address.id),
        address=address_data["address"],
        address_type=address_data["address_type"],
        primary=str(address_data["primary"]).lower(),
    )
    executed = user_gql_client.execute(mutation, context=request)
    assert dict(executed["data"]) == expected_data


def test_normal_user_can_query_emails(rf, user_gql_client):
    profile = ProfileFactory(user=user_gql_client.user)
    email = EmailFactory(profile=profile)
    request = rf.post("/graphql")
    request.user = user_gql_client.user
    query = """
        {
            myProfile {
                emails{
                    edges{
                        node{
                            email
                            emailType
                            primary
                        }
                    }
                }
            }
        }
    """
    expected_data = {
        "myProfile": {
            "emails": {
                "edges": [
                    {
                        "node": {
                            "email": email.email,
                            "emailType": email.email_type.name,
                            "primary": email.primary,
                        }
                    }
                ]
            }
        }
    }
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data


def test_normal_user_can_query_phones(rf, user_gql_client):
    profile = ProfileFactory(user=user_gql_client.user)
    phone = PhoneFactory(profile=profile)
    request = rf.post("/graphql")
    request.user = user_gql_client.user
    query = """
        {
            myProfile {
                phones{
                    edges{
                        node{
                            phone
                            phoneType
                            primary
                        }
                    }
                }
            }
        }
    """
    expected_data = {
        "myProfile": {
            "phones": {
                "edges": [
                    {
                        "node": {
                            "phone": phone.phone,
                            "phoneType": phone.phone_type.name,
                            "primary": phone.primary,
                        }
                    }
                ]
            }
        }
    }
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data


def test_normal_user_can_query_addresses(rf, user_gql_client):
    profile = ProfileFactory(user=user_gql_client.user)
    address = AddressFactory(profile=profile)
    request = rf.post("/graphql")
    request.user = user_gql_client.user
    query = """
        {
            myProfile {
                addresses{
                    edges{
                        node{
                            address
                            addressType
                            primary
                        }
                    }
                }
            }
        }
    """
    expected_data = {
        "myProfile": {
            "addresses": {
                "edges": [
                    {
                        "node": {
                            "address": address.address,
                            "addressType": address.address_type.name,
                            "primary": address.primary,
                        }
                    }
                ]
            }
        }
    }
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data


def test_normal_user_can_query_primary_contact_details(rf, user_gql_client):
    profile = ProfileFactory(user=user_gql_client.user)
    phone = PhoneFactory(profile=profile, primary=True)
    email = EmailFactory(profile=profile, primary=True)
    address = AddressFactory(profile=profile, primary=True)
    PhoneFactory(profile=profile, primary=False)
    EmailFactory(profile=profile, primary=False)
    AddressFactory(profile=profile, primary=False)
    request = rf.post("/graphql")
    request.user = user_gql_client.user
    query = """
        {
            myProfile {
                primaryPhone{
                    phone,
                    phoneType,
                    primary
                },
                primaryEmail{
                    email,
                    emailType,
                    primary
                },
                primaryAddress{
                    address,
                    addressType,
                    primary
                }
            }
        }
    """
    expected_data = {
        "myProfile": {
            "primaryPhone": {
                "phone": phone.phone,
                "phoneType": phone.phone_type.name,
                "primary": phone.primary,
            },
            "primaryEmail": {
                "email": email.email,
                "emailType": email.email_type.name,
                "primary": email.primary,
            },
            "primaryAddress": {
                "address": address.address,
                "addressType": address.address_type.name,
                "primary": address.primary,
            },
        }
    }
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data


def test_normal_user_can_change_primary_contact_details(
    rf, user_gql_client, email_data, phone_data, address_data
):
    profile = ProfileFactory(user=user_gql_client.user)
    PhoneFactory(profile=profile, primary=True)
    EmailFactory(profile=profile, primary=True)
    AddressFactory(profile=profile, primary=True)
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    t = Template(
        """
            mutation {
                updateProfile(
                    profile: {
                        addEmails:[
                            {emailType: ${email_type}, email:\"${email}\", primary: ${primary}}
                        ],
                        addPhones:[
                            {phoneType: ${phone_type}, phone:\"${phone}\", primary: ${primary}}
                        ],
                        addAddresses:[
                            {
                                addressType: ${address_type},
                                address:\"${address}\",
                                postalCode:\"${postal_code}\",
                                city:\"${city}\",
                                primary: ${primary}
                            }
                        ]
                    }
                ) {
                profile{
                    primaryEmail{
                        email,
                        emailType,
                        primary
                    },
                    primaryPhone{
                        phone,
                        phoneType,
                        primary
                    },
                    primaryAddress{
                        address,
                        postalCode,
                        city,
                        addressType,
                        primary
                    },
                }
            }
            }
        """
    )

    expected_data = {
        "updateProfile": {
            "profile": {
                "primaryEmail": {
                    "email": email_data["email"],
                    "emailType": email_data["email_type"],
                    "primary": True,
                },
                "primaryPhone": {
                    "phone": phone_data["phone"],
                    "phoneType": phone_data["phone_type"],
                    "primary": True,
                },
                "primaryAddress": {
                    "address": address_data["address"],
                    "postalCode": address_data["postal_code"],
                    "city": address_data["city"],
                    "addressType": address_data["address_type"],
                    "primary": True,
                },
            }
        }
    }

    mutation = t.substitute(
        email=email_data["email"],
        email_type=email_data["email_type"],
        phone=phone_data["phone"],
        phone_type=phone_data["phone_type"],
        address=address_data["address"],
        postal_code=address_data["postal_code"],
        city=address_data["city"],
        address_type=address_data["address_type"],
        primary="true",
    )
    executed = user_gql_client.execute(mutation, context=request)
    assert dict(executed["data"]) == expected_data


def test_normal_user_can_update_primary_contact_details(
    rf, user_gql_client, email_data
):
    profile = ProfileFactory(user=user_gql_client.user)
    email = EmailFactory(profile=profile)
    email_2 = EmailFactory(profile=profile, primary=True)
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    t = Template(
        """
            mutation {
                updateProfile(
                    profile: {
                    updateEmails:[
                        {
                            id: \"${email_id}\",
                            emailType: ${email_type},
                            email:\"${email}\",
                            primary: ${primary}
                        }
                    ]
                }
            ) {
                profile{
                    emails{
                        edges{
                        node{
                            id
                            email
                            emailType
                            primary
                        }
                        }
                    }
                }
            }
            }
        """
    )

    expected_data = {
        "updateProfile": {
            "profile": {
                "emails": {
                    "edges": [
                        {
                            "node": {
                                "id": to_global_id(type="EmailNode", id=email_2.id),
                                "email": email_2.email,
                                "emailType": email_2.email_type.name,
                                "primary": False,
                            }
                        },
                        {
                            "node": {
                                "id": to_global_id(type="EmailNode", id=email.id),
                                "email": email_data["email"],
                                "emailType": email_data["email_type"],
                                "primary": True,
                            }
                        },
                    ]
                }
            }
        }
    }

    mutation = t.substitute(
        email_id=to_global_id(type="EmailNode", id=email.id),
        email=email_data["email"],
        email_type=email_data["email_type"],
        primary="true",
    )
    executed = user_gql_client.execute(mutation, context=request)
    assert dict(executed["data"]) == expected_data


def test_normal_user_can_not_query_berth_profiles(rf, user_gql_client):
    ServiceFactory()
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


def test_admin_user_can_query_berth_profiles(rf, superuser_gql_client):
    profile = ProfileFactory()
    service = ServiceFactory()
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


def test_staff_user_with_group_access_can_query_berth_profiles(rf, user_gql_client):
    profile = ProfileFactory()
    service = ServiceFactory()
    ServiceConnectionFactory(profile=profile, service=service)
    group = GroupFactory()
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


def test_staff_user_can_filter_berth_profiles(rf, user_gql_client):
    profile_1, profile_2 = ProfileFactory(), ProfileFactory()
    service = ServiceFactory()
    ServiceConnectionFactory(profile=profile_1, service=service)
    ServiceConnectionFactory(profile=profile_2, service=service)
    group = GroupFactory()
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


def test_staff_user_can_sort_berth_profiles(rf, user_gql_client):
    profile_1, profile_2 = (
        ProfileFactory(first_name="Adam", last_name="Tester"),
        ProfileFactory(first_name="Bryan", last_name="Tester"),
    )
    service = ServiceFactory()
    ServiceConnectionFactory(profile=profile_1, service=service)
    ServiceConnectionFactory(profile=profile_2, service=service)
    group = GroupFactory()
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


def test_staff_user_can_paginate_berth_profiles(rf, user_gql_client):
    profile_1, profile_2 = (
        ProfileFactory(first_name="Adam", last_name="Tester"),
        ProfileFactory(first_name="Bryan", last_name="Tester"),
    )
    service = ServiceFactory()
    ServiceConnectionFactory(profile=profile_1, service=service)
    ServiceConnectionFactory(profile=profile_2, service=service)
    group = GroupFactory()
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
    # )
    # query = t.substitute(service_type=ServiceType.BERTH.name)
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
    rf, user_gql_client
):
    profile_berth = ProfileFactory()
    profile_youth = ProfileFactory()
    service_berth = ServiceFactory(service_type=ServiceType.BERTH)
    service_youth = ServiceFactory(service_type=ServiceType.YOUTH_MEMBERSHIP)
    ServiceConnectionFactory(profile=profile_berth, service=service_berth)
    ServiceConnectionFactory(profile=profile_youth, service=service_youth)
    group_berth = GroupFactory()
    user = user_gql_client.user
    user.groups.add(group_berth)
    assign_perm("can_view_profiles", group_berth, service_berth)
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


def test_normal_user_can_query_his_own_profile(rf, user_gql_client):
    profile = ProfileFactory(user=user_gql_client.user)
    request = rf.post("/graphql")
    request.user = user_gql_client.user
    query = """
        {
            myProfile {
                firstName
                lastName
            }
        }
    """
    expected_data = {
        "myProfile": {"firstName": profile.first_name, "lastName": profile.last_name}
    }
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data


def test_normal_user_cannot_query_a_profile(rf, user_gql_client):
    profile = ProfileFactory()
    service = ServiceFactory()
    ServiceConnectionFactory(profile=profile, service=service)
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    t = Template(
        """
        {
            profile(id: "${id}", serviceType: ${service_type}) {
                firstName
                lastName
            }
        }
    """
    )

    query = t.substitute(
        id=relay.Node.to_global_id(ProfileNode._meta.name, profile.id),
        service_type=ServiceType.BERTH.name,
    )
    executed = user_gql_client.execute(query, context=request)
    assert "errors" in executed
    assert executed["errors"][0]["message"] == _(
        "You do not have permission to perform this action."
    )


def test_staff_user_can_query_a_profile_connected_to_service_he_is_admin_of(
    rf, user_gql_client
):
    profile = ProfileFactory()
    service = ServiceFactory()
    ServiceConnectionFactory(profile=profile, service=service)
    group = GroupFactory()
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service)
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    t = Template(
        """
        {
            profile(id: "${id}", serviceType: ${service_type}) {
                firstName
                lastName
            }
        }
    """
    )

    query = t.substitute(
        id=relay.Node.to_global_id(ProfileNode._meta.name, profile.id),
        service_type=ServiceType.BERTH.name,
    )
    executed = user_gql_client.execute(query, context=request)
    expected_data = {
        "profile": {"firstName": profile.first_name, "lastName": profile.last_name}
    }
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data


def test_staff_user_cannot_query_a_profile_without_id(rf, user_gql_client):
    profile = ProfileFactory()
    service = ServiceFactory()
    ServiceConnectionFactory(profile=profile, service=service)
    group = GroupFactory()
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service)
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    t = Template(
        """
        {
            profile(serviceType: ${service_type}) {
                firstName
                lastName
            }
        }
    """
    )

    query = t.substitute(service_type=ServiceType.BERTH.name)
    executed = user_gql_client.execute(query, context=request)
    executed = user_gql_client.execute(query, context=request)
    assert "errors" in executed


def test_staff_user_cannot_query_a_profile_without_service_type(rf, user_gql_client):
    profile = ProfileFactory()
    service = ServiceFactory()
    ServiceConnectionFactory(profile=profile, service=service)
    group = GroupFactory()
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service)
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    t = Template(
        """
        {
            profile(id: ${id}) {
                firstName
                lastName
            }
        }
    """
    )

    query = t.substitute(id=relay.Node.to_global_id(ProfileNode._meta.name, profile.id))
    executed = user_gql_client.execute(query, context=request)
    executed = user_gql_client.execute(query, context=request)
    assert "errors" in executed


def test_staff_user_cannot_query_a_profile_with_service_type_that_is_not_connected(
    rf, user_gql_client
):
    profile = ProfileFactory()
    service_berth = ServiceFactory()
    service_youth = ServiceFactory(service_type=ServiceType.YOUTH_MEMBERSHIP)
    ServiceConnectionFactory(profile=profile, service=service_berth)
    group = GroupFactory()
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service_youth)
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    t = Template(
        """
        {
            profile(id: "${id}", serviceType: ${service_type}) {
                firstName
                lastName
            }
        }
    """
    )

    query = t.substitute(
        id=relay.Node.to_global_id(ProfileNode._meta.name, profile.id),
        service_type=ServiceType.YOUTH_MEMBERSHIP.name,
    )
    executed = user_gql_client.execute(query, context=request)
    assert "errors" in executed
    assert "code" in executed["errors"][0]["extensions"]
    assert executed["errors"][0]["extensions"]["code"] == OBJECT_DOES_NOT_EXIST_ERROR


def test_staff_user_cannot_query_a_profile_with_service_type_that_he_is_not_admin_of(
    rf, user_gql_client
):
    profile = ProfileFactory()
    service_berth = ServiceFactory()
    service_youth = ServiceFactory(service_type=ServiceType.YOUTH_MEMBERSHIP)
    ServiceConnectionFactory(profile=profile, service=service_berth)
    group = GroupFactory()
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service_youth)
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    t = Template(
        """
        {
            profile(id: "${id}", serviceType: ${service_type}) {
                firstName
                lastName
            }
        }
    """
    )

    query = t.substitute(
        id=relay.Node.to_global_id(ProfileNode._meta.name, profile.id),
        service_type=ServiceType.BERTH.name,
    )
    executed = user_gql_client.execute(query, context=request)
    executed = user_gql_client.execute(query, context=request)
    assert "errors" in executed
    assert executed["errors"][0]["message"] == _(
        "You do not have permission to perform this action."
    )


def test_profile_node_exposes_key_for_federation_gateway(rf, anon_user_gql_client):
    request = rf.post("/graphql")

    query = """
        query {
            _service {
                sdl
            }
        }
    """

    executed = anon_user_gql_client.execute(query, context=request)
    assert (
        'type ProfileNode implements Node  @key(fields: "id")'
        in executed["data"]["_service"]["sdl"]
    )
