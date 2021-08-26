from string import Template

import pytest
from graphql_relay.node.node import to_global_id

from open_city_profile.consts import INVALID_EMAIL_FORMAT_ERROR
from open_city_profile.tests.asserts import assert_match_error_code
from services.tests.factories import ServiceConnectionFactory
from subscriptions.tests.factories import (
    SubscriptionTypeCategoryFactory,
    SubscriptionTypeFactory,
)

from .factories import (
    AddressFactory,
    EmailFactory,
    PhoneFactory,
    ProfileFactory,
    ProfileWithPrimaryEmailFactory,
    SensitiveDataFactory,
)


@pytest.mark.parametrize("with_serviceconnection", (True, False))
def test_update_profile(
    user_gql_client, email_data, profile_data, service, with_serviceconnection
):
    profile = ProfileWithPrimaryEmailFactory(user=user_gql_client.user)
    if with_serviceconnection:
        ServiceConnectionFactory(profile=profile, service=service)

    email = profile.emails.first()

    t = Template(
        """
            mutation {
                updateMyProfile(
                    input: {
                        profile: {
                            nickname: "${nickname}",
                            updateEmails: [
                                {
                                    id: "${email_id}",
                                    emailType: ${email_type},
                                    email:"${email}",
                                    primary: ${primary}
                                }
                            ]
                        }
                    }
                ) {
                    profile {
                        nickname,
                        emails {
                            edges {
                                node {
                                    id
                                    email
                                    emailType
                                    primary
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
        "updateMyProfile": {
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
        email_id=to_global_id(type="EmailNode", id=email.id),
        email=email_data["email"],
        email_type=email_data["email_type"],
        primary=str(email_data["primary"]).lower(),
    )
    executed = user_gql_client.execute(mutation, service=service)
    if with_serviceconnection:
        assert executed["data"] == expected_data
    else:
        assert_match_error_code(executed, "PERMISSION_DENIED_ERROR")
        assert executed["data"]["updateMyProfile"] is None


def test_update_profile_without_email(user_gql_client, profile_data):
    ProfileFactory(user=user_gql_client.user)

    t = Template(
        """
            mutation {
                updateMyProfile(
                    input: {
                        profile: {
                            nickname: "${nickname}"
                        }
                    }
                ) {
                    profile {
                        nickname,
                        emails {
                            edges {
                                node {
                                    email
                                    emailType
                                    primary
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
        "updateMyProfile": {
            "profile": {"nickname": profile_data["nickname"], "emails": {"edges": []}}
        }
    }

    mutation = t.substitute(nickname=profile_data["nickname"],)
    executed = user_gql_client.execute(mutation)
    assert executed["data"] == expected_data


def test_add_email(user_gql_client, email_data):
    profile = ProfileWithPrimaryEmailFactory(user=user_gql_client.user)
    email = profile.emails.first()

    t = Template(
        """
            mutation {
                updateMyProfile(
                    input: {
                        profile: {
                            addEmails: [
                                {
                                    emailType: ${email_type},
                                    email:"${email}",
                                    primary: ${primary}
                                }
                            ]
                        }
                    }
                ) {
                    profile {
                        emails {
                            edges {
                                node {
                                    email
                                    emailType
                                    primary
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
        "updateMyProfile": {
            "profile": {
                "emails": {
                    "edges": [
                        {
                            "node": {
                                "email": email.email,
                                "emailType": email.email_type.name,
                                "primary": email.primary,
                                "verified": False,
                            }
                        },
                        {
                            "node": {
                                "email": email_data["email"],
                                "emailType": email_data["email_type"],
                                "primary": not email_data["primary"],
                                "verified": False,
                            }
                        },
                    ]
                }
            }
        }
    }

    mutation = t.substitute(
        email=email_data["email"],
        email_type=email_data["email_type"],
        primary=str(not email_data["primary"]).lower(),
    )
    executed = user_gql_client.execute(mutation)
    assert dict(executed["data"]) == expected_data


def test_not_add_invalid_email(user_gql_client, email_data):
    ProfileWithPrimaryEmailFactory(user=user_gql_client.user)

    t = Template(
        """
            mutation {
                updateMyProfile(
                    input: {
                        profile: {
                            addEmails: [
                                {
                                    emailType: ${email_type},
                                    email:"${email}",
                                    primary: ${primary}
                                }
                            ]
                        }
                    }
                ) {
                    profile {
                        emails {
                            edges {
                                node {
                                    id
                                }
                            }
                        }
                    }
                }
            }
        """
    )

    mutation = t.substitute(
        email="!dsdsd{}{}{}{}{}{",
        email_type=email_data["email_type"],
        primary=str(not email_data["primary"]).lower(),
    )
    executed = user_gql_client.execute(mutation)
    assert "code" in executed["errors"][0]["extensions"]
    assert executed["errors"][0]["extensions"]["code"] == INVALID_EMAIL_FORMAT_ERROR


def test_not_update_email_to_invalid_format(user_gql_client, email_data):
    profile = ProfileWithPrimaryEmailFactory(user=user_gql_client.user)
    email = profile.emails.first()

    t = Template(
        """
            mutation {
                updateMyProfile(
                    input: {
                        profile: {
                            updateEmails: [
                                {
                                    id: "${email_id}",
                                    emailType: ${email_type},
                                    email:"${email}",
                                    primary: ${primary}
                                }
                            ]
                        }
                    }
                ) {
                    profile {
                        emails {
                            edges {
                                node {
                                    id
                                }
                            }
                        }
                    }
                }
            }
        """
    )

    mutation = t.substitute(
        email_id=to_global_id(type="EmailNode", id=email.id),
        email="!dsdsd{}{}{}{}{}{",
        email_type=email_data["email_type"],
        primary=str(email_data["primary"]).lower(),
    )
    executed = user_gql_client.execute(mutation)
    assert "code" in executed["errors"][0]["extensions"]
    assert executed["errors"][0]["extensions"]["code"] == INVALID_EMAIL_FORMAT_ERROR


UPDATE_EMAIL_MUTATION = """
    mutation updateMyEmails($emailUpdates: [UpdateEmailInput]) {
        updateMyProfile(
            input: {
                profile: {
                    updateEmails: $emailUpdates
                }
            }
        ) {
            profile {
                emails {
                    edges {
                        node {
                            id
                            email
                            emailType
                            primary
                            verified
                        }
                    }
                }
            }
        }
    }
"""


def test_update_email(user_gql_client, email_data):
    profile = ProfileWithPrimaryEmailFactory(user=user_gql_client.user)
    email = profile.emails.first()

    expected_data = {
        "updateMyProfile": {
            "profile": {
                "emails": {
                    "edges": [
                        {
                            "node": {
                                "id": to_global_id(type="EmailNode", id=email.id),
                                "email": email_data["email"],
                                "emailType": email_data["email_type"],
                                "primary": email_data["primary"],
                                "verified": False,
                            }
                        }
                    ]
                }
            }
        }
    }

    email_updates = [
        {
            "id": to_global_id(type="EmailNode", id=email.id),
            "email": email_data["email"],
            "emailType": email_data["email_type"],
            "primary": email_data["primary"],
        }
    ]
    executed = user_gql_client.execute(
        UPDATE_EMAIL_MUTATION, variables={"emailUpdates": email_updates}
    )
    assert dict(executed["data"]) == expected_data


def test_change_primary_email_to_another_one(user_gql_client):
    profile = ProfileFactory(user=user_gql_client.user)
    email = EmailFactory(profile=profile, primary=False)
    email_2 = EmailFactory(profile=profile, primary=True)

    expected_data = {
        "updateMyProfile": {
            "profile": {
                "emails": {
                    "edges": [
                        {
                            "node": {
                                "id": to_global_id(type="EmailNode", id=email.id),
                                "email": email.email,
                                "emailType": email.email_type.name,
                                "primary": True,
                                "verified": False,
                            }
                        },
                        {
                            "node": {
                                "id": to_global_id(type="EmailNode", id=email_2.id),
                                "email": email_2.email,
                                "emailType": email_2.email_type.name,
                                "primary": False,
                                "verified": False,
                            }
                        },
                    ]
                }
            }
        }
    }

    email_updates = [
        {"id": to_global_id(type="EmailNode", id=email.id), "primary": True}
    ]
    executed = user_gql_client.execute(
        UPDATE_EMAIL_MUTATION, variables={"emailUpdates": email_updates}
    )
    assert dict(executed["data"]) == expected_data


def test_changing_an_email_address_marks_it_unverified(user_gql_client):
    profile = ProfileFactory(user=user_gql_client.user)
    email = EmailFactory(profile=profile, email="old@email.example", verified=True)
    new_email_value = "new@email.example"

    expected_data = {
        "updateMyProfile": {
            "profile": {
                "emails": {
                    "edges": [
                        {
                            "node": {
                                "id": to_global_id("EmailNode", email.id),
                                "email": new_email_value,
                                "emailType": email.email_type.name,
                                "primary": email.primary,
                                "verified": False,
                            }
                        },
                    ]
                }
            }
        }
    }

    email_updates = [
        {"id": to_global_id("EmailNode", email.id), "email": new_email_value}
    ]
    executed = user_gql_client.execute(
        UPDATE_EMAIL_MUTATION, variables={"emailUpdates": email_updates}
    )
    assert dict(executed["data"]) == expected_data


def test_remove_email(user_gql_client):
    profile = ProfileWithPrimaryEmailFactory(user=user_gql_client.user, emails=2)
    primary_email = profile.emails.filter(primary=True).first()
    email = profile.emails.filter(primary=False).first()

    t = Template(
        """
            mutation {
                updateMyProfile(
                    input: {
                        profile: {
                            removeEmails: [
                                "${email_id}"
                            ]
                        }
                    }
                ) {
                    profile {
                        emails {
                            edges {
                                node {
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
        "updateMyProfile": {
            "profile": {
                "emails": {
                    "edges": [
                        {
                            "node": {
                                "id": to_global_id(
                                    type="EmailNode", id=primary_email.id
                                ),
                                "email": primary_email.email,
                                "emailType": primary_email.email_type.name,
                                "primary": primary_email.primary,
                            }
                        }
                    ]
                }
            }
        }
    }

    mutation = t.substitute(email_id=to_global_id(type="EmailNode", id=email.id))
    executed = user_gql_client.execute(mutation)
    assert dict(executed["data"]) == expected_data


def test_remove_all_emails(user_gql_client):
    profile = ProfileWithPrimaryEmailFactory(user=user_gql_client.user, emails=2)
    primary_email = profile.emails.filter(primary=True).first()
    email = profile.emails.filter(primary=False).first()

    t = Template(
        """
            mutation {
                updateMyProfile(
                    input: {
                        profile: {
                            removeEmails: [
                                "${primary_email_id}",
                                "${email_id}",
                            ]
                        }
                    }
                ) {
                    profile {
                        emails {
                            edges {
                                node {
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

    expected_data = {"updateMyProfile": {"profile": {"emails": {"edges": []}}}}

    mutation = t.substitute(
        primary_email_id=to_global_id(type="EmailNode", id=primary_email.id),
        email_id=to_global_id(type="EmailNode", id=email.id),
    )
    executed = user_gql_client.execute(mutation)
    assert executed["data"] == expected_data


def test_add_phone(user_gql_client, phone_data):
    ProfileWithPrimaryEmailFactory(user=user_gql_client.user)

    t = Template(
        """
            mutation {
                updateMyProfile(
                    input: {
                        profile: {
                            addPhones: [
                                {
                                    phoneType: ${phone_type},
                                    phone:"${phone}",
                                    primary: ${primary}
                                }
                            ]
                        }
                    }
                ) {
                    profile {
                        phones {
                            edges {
                                node {
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
        "updateMyProfile": {
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
    executed = user_gql_client.execute(mutation)
    assert dict(executed["data"]) == expected_data


def test_update_phone(user_gql_client, phone_data):
    profile = ProfileWithPrimaryEmailFactory(user=user_gql_client.user)
    phone = PhoneFactory(profile=profile)

    t = Template(
        """
            mutation {
                updateMyProfile(
                    input: {
                        profile: {
                            updatePhones: [
                                {
                                    id: "${phone_id}",
                                    phoneType: ${phone_type},
                                    phone:"${phone}",
                                    primary: ${primary}
                                }
                            ]
                        }
                    }
                ) {
                    profile {
                        phones {
                            edges {
                                node {
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
        "updateMyProfile": {
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
    executed = user_gql_client.execute(mutation)
    assert dict(executed["data"]) == expected_data


def test_remove_phone(user_gql_client):
    profile = ProfileWithPrimaryEmailFactory(user=user_gql_client.user)
    phone = PhoneFactory(profile=profile)

    t = Template(
        """
            mutation {
                updateMyProfile(
                    input: {
                        profile: {
                            removePhones: [
                                "${phone_id}"
                            ]
                        }
                    }
                ) {
                    profile {
                        phones {
                            edges {
                                node {
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

    expected_data = {"updateMyProfile": {"profile": {"phones": {"edges": []}}}}

    mutation = t.substitute(phone_id=to_global_id(type="PhoneNode", id=phone.id))
    executed = user_gql_client.execute(mutation)
    assert dict(executed["data"]) == expected_data


def test_add_address(user_gql_client, address_data):
    ProfileWithPrimaryEmailFactory(user=user_gql_client.user)

    t = Template(
        """
            mutation {
                updateMyProfile(
                    input: {
                        profile: {
                            addAddresses: [
                                {
                                    addressType: ${address_type},
                                    address:"${address}",
                                    postalCode: "${postal_code}",
                                    city: "${city}",
                                    countryCode: "${country_code}",
                                    primary: ${primary}
                                }
                            ]
                        }
                    }
                ) {
                    profile {
                        addresses {
                            edges {
                                node {
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
        "updateMyProfile": {
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
    executed = user_gql_client.execute(mutation)
    assert dict(executed["data"]) == expected_data


def test_update_address(user_gql_client, address_data):
    profile = ProfileWithPrimaryEmailFactory(user=user_gql_client.user)
    address = AddressFactory(profile=profile)

    t = Template(
        """
            mutation {
                updateMyProfile(
                    input: {
                        profile: {
                            updateAddresses: [
                                {
                                    id: "${address_id}",
                                    addressType: ${address_type},
                                    address:"${address}",
                                    postalCode:"${postal_code}",
                                    city:"${city}",
                                    primary: ${primary}
                                }
                            ]
                        }
                    }
                ) {
                    profile {
                        addresses {
                            edges {
                                node {
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
        "updateMyProfile": {
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
    executed = user_gql_client.execute(mutation)
    assert dict(executed["data"]) == expected_data


def test_remove_address(user_gql_client):
    profile = ProfileWithPrimaryEmailFactory(user=user_gql_client.user)
    address = AddressFactory(profile=profile)

    t = Template(
        """
            mutation {
                updateMyProfile(
                    input: {
                        profile: {
                            removeAddresses: [
                                "${address_id}"
                            ]
                        }
                    }
                ) {
                    profile {
                        addresses {
                            edges {
                                node {
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

    expected_data = {"updateMyProfile": {"profile": {"addresses": {"edges": []}}}}

    mutation = t.substitute(address_id=to_global_id(type="AddressNode", id=address.id))
    executed = user_gql_client.execute(mutation)
    assert dict(executed["data"]) == expected_data


def test_change_primary_contact_details(
    user_gql_client, email_data, phone_data, address_data
):
    profile = ProfileFactory(user=user_gql_client.user)
    PhoneFactory(profile=profile, primary=True)
    EmailFactory(profile=profile, primary=True)
    AddressFactory(profile=profile, primary=True)

    t = Template(
        """
            mutation {
                updateMyProfile(
                    input: {
                        profile: {
                            addEmails: [
                                {
                                    emailType: ${email_type},
                                    email:"${email}",
                                    primary: ${primary}
                                }
                            ],
                            addPhones: [
                                {
                                    phoneType: ${phone_type},
                                    phone:"${phone}",
                                    primary: ${primary}
                                }
                            ],
                            addAddresses: [
                                {
                                    addressType: ${address_type},
                                    address:"${address}",
                                    postalCode:"${postal_code}",
                                    city:"${city}",
                                    primary: ${primary}
                                }
                            ]
                        }
                    }
                ) {
                    profile {
                        primaryEmail {
                            email,
                            emailType,
                            primary
                        },
                        primaryPhone {
                            phone,
                            phoneType,
                            primary
                        },
                        primaryAddress {
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
        "updateMyProfile": {
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
    executed = user_gql_client.execute(mutation)
    assert dict(executed["data"]) == expected_data


def test_update_sensitive_data(user_gql_client):
    profile = ProfileWithPrimaryEmailFactory(user=user_gql_client.user)
    SensitiveDataFactory(profile=profile, ssn="010199-1234")

    t = Template(
        """
            mutation {
                updateMyProfile(
                    input: {
                        profile: {
                            nickname: "${nickname}"
                            sensitivedata: {
                                ssn: "${ssn}"
                            }
                        }
                    }
                ) {
                    profile {
                        nickname
                        sensitivedata {
                            ssn
                        }
                    }
                }
            }
        """
    )

    data = {"nickname": "Larry", "ssn": "010199-4321"}

    query = t.substitute(**data)

    expected_data = {
        "updateMyProfile": {
            "profile": {
                "nickname": data["nickname"],
                "sensitivedata": {"ssn": data["ssn"]},
            }
        }
    }
    executed = user_gql_client.execute(query)
    assert dict(executed["data"]) == expected_data


def test_update_subscriptions_via_profile(user_gql_client):
    ProfileWithPrimaryEmailFactory(user=user_gql_client.user)
    category = SubscriptionTypeCategoryFactory()
    type_1 = SubscriptionTypeFactory(subscription_type_category=category, code="TEST-1")
    type_2 = SubscriptionTypeFactory(subscription_type_category=category, code="TEST-2")

    t = Template(
        """
        mutation {
            updateMyProfile(
                input: {
                    profile: {
                        subscriptions: [
                            {
                                subscriptionTypeId: "${type_1_id}",
                                enabled: ${type_1_enabled}
                            },
                            {
                                subscriptionTypeId: "${type_2_id}",
                                enabled: ${type_2_enabled}
                            }
                        ]
                    }
                }
            ) {
                profile {
                    subscriptions {
                        edges {
                            node {
                                enabled
                                subscriptionType {
                                    code
                                    subscriptionTypeCategory {
                                        code
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        """
    )

    expected_data = {
        "updateMyProfile": {
            "profile": {
                "subscriptions": {
                    "edges": [
                        {
                            "node": {
                                "enabled": True,
                                "subscriptionType": {
                                    "code": type_1.code,
                                    "subscriptionTypeCategory": {"code": category.code},
                                },
                            }
                        },
                        {
                            "node": {
                                "enabled": False,
                                "subscriptionType": {
                                    "code": type_2.code,
                                    "subscriptionTypeCategory": {"code": category.code},
                                },
                            }
                        },
                    ]
                }
            }
        }
    }

    mutation = t.substitute(
        type_1_id=to_global_id(type="SubscriptionTypeNode", id=type_1.id),
        type_1_enabled="true",
        type_2_id=to_global_id(type="SubscriptionTypeNode", id=type_2.id),
        type_2_enabled="false",
    )
    executed = user_gql_client.execute(mutation)
    assert dict(executed["data"]) == expected_data
