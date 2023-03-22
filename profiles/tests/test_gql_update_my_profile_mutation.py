from string import Template

import pytest
from graphql_relay.node.node import to_global_id

from open_city_profile.exceptions import DataConflictError
from open_city_profile.tests.asserts import assert_match_error_code
from profiles.models import Address, Email, Phone
from profiles.tests.profile_input_validation import ExistingProfileInputValidationBase
from services.tests.factories import ServiceConnectionFactory

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
    user_gql_client, email_data, profile_data, service, with_serviceconnection,
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


EMAILS_MUTATION = """
    mutation updateMyEmails($profileInput: ProfileInput!) {
        updateMyProfile(
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

NEW_EMAIL_VALUE = "new@email.example"


@pytest.mark.parametrize(
    "global_id_type, global_id_id, succeeds",
    (
        (None, None, True),
        ("PhoneNode", None, False),
        ("NonExisting", None, False),
        (None, "something", False),
        (None, 10000, False),
        (None, -1, False),
    ),
)
def test_update_email(
    global_id_type, global_id_id, succeeds, user_gql_client, email_data
):
    profile = ProfileWithPrimaryEmailFactory(user=user_gql_client.user)
    email = profile.emails.first()

    global_id_type = global_id_type or "EmailNode"
    global_id_id = global_id_id or email.id

    email_updates = [
        {
            "id": to_global_id(type=global_id_type, id=global_id_id),
            "email": email_data["email"],
            "emailType": email_data["email_type"],
            "primary": email_data["primary"],
        }
    ]

    executed = user_gql_client.execute(
        EMAILS_MUTATION, variables={"profileInput": {"updateEmails": email_updates}}
    )

    if succeeds:
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

        assert dict(executed["data"]) == expected_data
    else:
        assert executed["data"]["updateMyProfile"] is None
        assert_match_error_code(executed, "OBJECT_DOES_NOT_EXIST_ERROR")


def test_can_not_update_email_of_another_profile(user_gql_client):
    ProfileWithPrimaryEmailFactory(user=user_gql_client.user)
    another_email = ProfileWithPrimaryEmailFactory().emails.first()

    email_updates = [
        {
            "id": to_global_id(type="EmailNode", id=another_email.id),
            "email": NEW_EMAIL_VALUE,
        }
    ]
    executed = user_gql_client.execute(
        EMAILS_MUTATION, variables={"profileInput": {"updateEmails": email_updates}}
    )

    assert executed["data"]["updateMyProfile"] is None
    assert_match_error_code(executed, "OBJECT_DOES_NOT_EXIST_ERROR")
    assert Email.objects.get(id=another_email.id).email == another_email.email


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
        EMAILS_MUTATION, variables={"profileInput": {"updateEmails": email_updates}}
    )
    assert dict(executed["data"]) == expected_data


def test_can_not_change_primary_email_to_non_primary(user_gql_client):
    profile = ProfileWithPrimaryEmailFactory(user=user_gql_client.user)
    email = profile.emails.first()

    email_updates = [
        {"id": to_global_id(type="EmailNode", id=email.id), "primary": False}
    ]
    executed = user_gql_client.execute(
        EMAILS_MUTATION, variables={"profileInput": {"updateEmails": email_updates}}
    )
    assert_match_error_code(executed, "PROFILE_MUST_HAVE_PRIMARY_EMAIL")


def test_can_not_delete_primary_email(user_gql_client):
    profile = ProfileWithPrimaryEmailFactory(user=user_gql_client.user)
    email = profile.emails.first()

    email_deletes = [to_global_id(type="EmailNode", id=email.id)]
    executed = user_gql_client.execute(
        EMAILS_MUTATION, variables={"profileInput": {"removeEmails": email_deletes}}
    )
    assert_match_error_code(executed, "PROFILE_MUST_HAVE_PRIMARY_EMAIL")


def test_can_replace_a_primary_email_with_a_newly_created_one(
    user_gql_client, email_data
):
    profile = ProfileWithPrimaryEmailFactory(user=user_gql_client.user)
    old_primary_email = profile.emails.first()

    email_creations = [
        {
            "email": email_data["email"],
            "emailType": email_data["email_type"],
            "primary": True,
        }
    ]
    email_updates = [
        {
            "id": to_global_id(type="EmailNode", id=old_primary_email.id),
            "primary": False,
        }
    ]

    executed = user_gql_client.execute(
        EMAILS_MUTATION,
        variables={
            "profileInput": {
                "addEmails": email_creations,
                "updateEmails": email_updates,
            }
        },
    )

    new_primary_email = Email.objects.get(email=email_data["email"])

    expected_data = {
        "updateMyProfile": {
            "profile": {
                "emails": {
                    "edges": [
                        {
                            "node": {
                                "id": to_global_id(
                                    type="EmailNode", id=new_primary_email.id
                                ),
                                "email": email_data["email"],
                                "emailType": email_data["email_type"],
                                "primary": True,
                                "verified": False,
                            }
                        },
                        {
                            "node": {
                                "id": to_global_id(
                                    type="EmailNode", id=old_primary_email.id
                                ),
                                "email": old_primary_email.email,
                                "emailType": old_primary_email.email_type.name,
                                "primary": False,
                                "verified": False,
                            }
                        },
                    ]
                }
            }
        }
    }

    assert executed["data"] == expected_data


def test_changing_an_email_address_marks_it_unverified(user_gql_client):
    profile = ProfileFactory(user=user_gql_client.user)
    email = EmailFactory(profile=profile, email="old@email.example", verified=True)

    expected_data = {
        "updateMyProfile": {
            "profile": {
                "emails": {
                    "edges": [
                        {
                            "node": {
                                "id": to_global_id("EmailNode", email.id),
                                "email": NEW_EMAIL_VALUE,
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
        {"id": to_global_id("EmailNode", email.id), "email": NEW_EMAIL_VALUE}
    ]
    executed = user_gql_client.execute(
        EMAILS_MUTATION, variables={"profileInput": {"updateEmails": email_updates}}
    )
    assert dict(executed["data"]) == expected_data


@pytest.mark.parametrize(
    "global_id_type, global_id_id, succeeds",
    (
        (None, None, True),
        ("PhoneNode", None, False),
        ("NonExisting", None, False),
        (None, "something", False),
        (None, 10000, False),
        (None, -1, False),
    ),
)
def test_remove_email(global_id_type, global_id_id, succeeds, user_gql_client):
    profile = ProfileWithPrimaryEmailFactory(user=user_gql_client.user, emails=2)
    primary_email = profile.emails.filter(primary=True).first()
    email = profile.emails.filter(primary=False).first()

    global_id_type = global_id_type or "EmailNode"
    global_id_id = global_id_id or email.id

    email_deletes = [
        to_global_id(type=global_id_type, id=global_id_id),
    ]
    executed = user_gql_client.execute(
        EMAILS_MUTATION, variables={"profileInput": {"removeEmails": email_deletes}}
    )

    if succeeds:
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
                                    "verified": primary_email.verified,
                                }
                            }
                        ]
                    }
                }
            }
        }

        assert dict(executed["data"]) == expected_data
    else:
        assert executed["data"]["updateMyProfile"] is None
        assert_match_error_code(executed, "OBJECT_DOES_NOT_EXIST_ERROR")


def test_can_not_remove_email_of_another_profile(user_gql_client):
    ProfileWithPrimaryEmailFactory(user=user_gql_client.user)
    another_email = ProfileWithPrimaryEmailFactory().emails.first()

    email_deletes = [
        to_global_id(type="EmailNode", id=another_email.id),
    ]
    executed = user_gql_client.execute(
        EMAILS_MUTATION, variables={"profileInput": {"removeEmails": email_deletes}}
    )

    assert executed["data"]["updateMyProfile"] is None
    assert_match_error_code(executed, "OBJECT_DOES_NOT_EXIST_ERROR")
    assert Email.objects.filter(id=another_email.id).exists()


def test_remove_all_emails_if_they_are_not_primary(user_gql_client):
    profile = ProfileFactory(user=user_gql_client.user)
    email1 = EmailFactory(profile=profile, primary=False)
    email2 = EmailFactory(profile=profile, primary=False)

    expected_data = {"updateMyProfile": {"profile": {"emails": {"edges": []}}}}

    email_deletes = [
        to_global_id(type="EmailNode", id=email1.id),
        to_global_id(type="EmailNode", id=email2.id),
    ]
    executed = user_gql_client.execute(
        EMAILS_MUTATION, variables={"profileInput": {"removeEmails": email_deletes}}
    )
    assert executed["data"] == expected_data


def test_when_keycloak_returns_conflict_on_update_then_correct_error_code_is_produced(
    user_gql_client, mocker
):
    user = user_gql_client.user
    profile = ProfileWithPrimaryEmailFactory(user=user)
    email = profile.emails.first()
    NEW_FIRST_NAME = "New first name"
    NEW_LAST_NAME = "New last name"

    keycloak_mock = mocker.patch(
        "profiles.schema.send_profile_changes_to_keycloak",
        side_effect=DataConflictError(""),
    )

    variables = {
        "profileInput": {
            "firstName": NEW_FIRST_NAME,
            "lastName": NEW_LAST_NAME,
            "updateEmails": [
                {"id": to_global_id("EmailNode", email.id), "email": NEW_EMAIL_VALUE}
            ],
        }
    }
    executed = user_gql_client.execute(EMAILS_MUTATION, variables=variables)

    assert_match_error_code(executed, "DATA_CONFLICT_ERROR")
    keycloak_mock.assert_called_once_with(
        user.uuid, NEW_FIRST_NAME, NEW_LAST_NAME, NEW_EMAIL_VALUE
    )


PHONES_MUTATION = """
    mutation updateMyPhones($profileInput: ProfileInput!) {
        updateMyProfile(
            input: {
                profile: $profileInput
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


def test_add_phone(user_gql_client, phone_data):
    profile = ProfileWithPrimaryEmailFactory(user=user_gql_client.user)

    executed = user_gql_client.execute(
        PHONES_MUTATION,
        variables={
            "profileInput": {
                "addPhones": [
                    {
                        "phone": phone_data["phone"],
                        "phoneType": phone_data["phone_type"],
                        "primary": phone_data["primary"],
                    }
                ]
            }
        },
    )

    phone = profile.phones.get()

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

    assert dict(executed["data"]) == expected_data


@pytest.mark.parametrize(
    "global_id_type, global_id_id, succeeds",
    (
        (None, None, True),
        ("AddressNode", None, False),
        ("NonExisting", None, False),
        (None, "something", False),
        (None, 10000, False),
        (None, -1, False),
    ),
)
def test_update_phone(
    global_id_type, global_id_id, succeeds, user_gql_client, phone_data
):
    profile = ProfileWithPrimaryEmailFactory(user=user_gql_client.user)
    phone = PhoneFactory(profile=profile)

    global_id_type = global_id_type or "PhoneNode"
    global_id_id = global_id_id or phone.id

    executed = user_gql_client.execute(
        PHONES_MUTATION,
        variables={
            "profileInput": {
                "updatePhones": [
                    {
                        "id": to_global_id(type=global_id_type, id=global_id_id),
                        "phone": phone_data["phone"],
                        "phoneType": phone_data["phone_type"],
                        "primary": phone_data["primary"],
                    }
                ]
            }
        },
    )

    if succeeds:
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

        assert dict(executed["data"]) == expected_data
    else:
        assert executed["data"]["updateMyProfile"] is None
        assert_match_error_code(executed, "OBJECT_DOES_NOT_EXIST_ERROR")


def test_can_not_update_phone_of_another_profile(user_gql_client):
    ProfileFactory(user=user_gql_client.user)
    another_phone = PhoneFactory(profile=ProfileFactory())

    executed = user_gql_client.execute(
        PHONES_MUTATION,
        variables={
            "profileInput": {
                "updatePhones": [
                    {
                        "id": to_global_id(type="PhoneNode", id=another_phone.id),
                        "phone": "New phone",
                    }
                ]
            }
        },
    )

    assert executed["data"]["updateMyProfile"] is None
    assert_match_error_code(executed, "OBJECT_DOES_NOT_EXIST_ERROR")
    assert Phone.objects.get(id=another_phone.id).phone == another_phone.phone


@pytest.mark.parametrize(
    "global_id_type, global_id_id, succeeds",
    (
        (None, None, True),
        ("AddressNode", None, False),
        ("NonExisting", None, False),
        (None, "something", False),
        (None, 10000, False),
        (None, -1, False),
    ),
)
def test_remove_phone(global_id_type, global_id_id, succeeds, user_gql_client):
    profile = ProfileWithPrimaryEmailFactory(user=user_gql_client.user)
    phone = PhoneFactory(profile=profile)

    global_id_type = global_id_type or "PhoneNode"
    global_id_id = global_id_id or phone.id

    executed = user_gql_client.execute(
        PHONES_MUTATION,
        variables={
            "profileInput": {
                "removePhones": [to_global_id(type=global_id_type, id=global_id_id)]
            }
        },
    )

    if succeeds:
        expected_data = {"updateMyProfile": {"profile": {"phones": {"edges": []}}}}

        assert dict(executed["data"]) == expected_data
    else:
        assert executed["data"]["updateMyProfile"] is None
        assert_match_error_code(executed, "OBJECT_DOES_NOT_EXIST_ERROR")


def test_can_not_remove_phone_of_another_profile(user_gql_client):
    ProfileWithPrimaryEmailFactory(user=user_gql_client.user)
    another_phone = PhoneFactory(profile=ProfileFactory())

    executed = user_gql_client.execute(
        PHONES_MUTATION,
        variables={
            "profileInput": {
                "removePhones": [to_global_id(type="PhoneNode", id=another_phone.id)]
            }
        },
    )

    assert executed["data"]["updateMyProfile"] is None
    assert_match_error_code(executed, "OBJECT_DOES_NOT_EXIST_ERROR")
    assert Phone.objects.filter(id=another_phone.id).exists()


class TestProfileInputValidation(ExistingProfileInputValidationBase):
    def create_profile(self, user):
        return ProfileFactory(user=user)

    def execute_query(self, user_gql_client, profile_input):
        return user_gql_client.execute(
            PHONES_MUTATION, variables={"profileInput": profile_input},
        )


ADDRESSES_MUTATION = """
    mutation updateMyAddresses($profileInput: ProfileInput!) {
        updateMyProfile(
            input: {
                profile: $profileInput
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


def test_add_address(user_gql_client, address_data):
    profile = ProfileWithPrimaryEmailFactory(user=user_gql_client.user)

    executed = user_gql_client.execute(
        ADDRESSES_MUTATION,
        variables={
            "profileInput": {
                "addAddresses": [
                    {
                        "address": address_data["address"],
                        "postalCode": address_data["postal_code"],
                        "city": address_data["city"],
                        "countryCode": address_data["country_code"],
                        "addressType": address_data["address_type"],
                        "primary": address_data["primary"],
                    }
                ]
            }
        },
    )

    address = profile.addresses.get()

    expected_data = {
        "updateMyProfile": {
            "profile": {
                "addresses": {
                    "edges": [
                        {
                            "node": {
                                "id": to_global_id("AddressNode", address.id),
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

    assert dict(executed["data"]) == expected_data


@pytest.mark.parametrize(
    "global_id_type, global_id_id, succeeds",
    (
        (None, None, True),
        ("EmailNode", None, False),
        ("NonExisting", None, False),
        (None, "something", False),
        (None, 10000, False),
        (None, -1, False),
    ),
)
def test_update_address(
    global_id_type, global_id_id, succeeds, user_gql_client, address_data
):
    profile = ProfileWithPrimaryEmailFactory(user=user_gql_client.user)
    address = AddressFactory(profile=profile)

    global_id_type = global_id_type or "AddressNode"
    global_id_id = global_id_id or address.id

    executed = user_gql_client.execute(
        ADDRESSES_MUTATION,
        variables={
            "profileInput": {
                "updateAddresses": [
                    {
                        "id": to_global_id(type=global_id_type, id=global_id_id),
                        "address": address_data["address"],
                        "postalCode": address_data["postal_code"],
                        "city": address_data["city"],
                        "countryCode": address_data["country_code"],
                        "addressType": address_data["address_type"],
                        "primary": address_data["primary"],
                    }
                ]
            }
        },
    )

    if succeeds:
        expected_data = {
            "updateMyProfile": {
                "profile": {
                    "addresses": {
                        "edges": [
                            {
                                "node": {
                                    "id": to_global_id(
                                        type="AddressNode", id=address.id
                                    ),
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

        assert dict(executed["data"]) == expected_data
    else:
        assert executed["data"]["updateMyProfile"] is None
        assert_match_error_code(executed, "OBJECT_DOES_NOT_EXIST_ERROR")


def test_can_not_update_address_of_another_profile(user_gql_client):
    ProfileFactory(user=user_gql_client.user)
    another_address = AddressFactory(profile=ProfileFactory())

    executed = user_gql_client.execute(
        ADDRESSES_MUTATION,
        variables={
            "profileInput": {
                "updateAddresses": [
                    {
                        "id": to_global_id(type="AddressNode", id=another_address.id),
                        "address": "New address",
                    }
                ]
            }
        },
    )

    assert executed["data"]["updateMyProfile"] is None
    assert_match_error_code(executed, "OBJECT_DOES_NOT_EXIST_ERROR")
    assert Address.objects.get(id=another_address.id).address == another_address.address


@pytest.mark.parametrize(
    "global_id_type, global_id_id, succeeds",
    (
        (None, None, True),
        ("EmailNode", None, False),
        ("NonExisting", None, False),
        (None, "something", False),
        (None, 10000, False),
        (None, -1, False),
    ),
)
def test_remove_address(global_id_type, global_id_id, succeeds, user_gql_client):
    profile = ProfileWithPrimaryEmailFactory(user=user_gql_client.user)
    address = AddressFactory(profile=profile)

    global_id_type = global_id_type or "AddressNode"
    global_id_id = global_id_id or address.id

    executed = user_gql_client.execute(
        ADDRESSES_MUTATION,
        variables={
            "profileInput": {
                "removeAddresses": [to_global_id(type=global_id_type, id=global_id_id)]
            }
        },
    )

    if succeeds:
        expected_data = {"updateMyProfile": {"profile": {"addresses": {"edges": []}}}}

        assert dict(executed["data"]) == expected_data
    else:
        assert executed["data"]["updateMyProfile"] is None
        assert_match_error_code(executed, "OBJECT_DOES_NOT_EXIST_ERROR")


def test_can_not_remove_address_of_another_profile(user_gql_client):
    ProfileWithPrimaryEmailFactory(user=user_gql_client.user)
    another_address = AddressFactory(profile=ProfileFactory())

    executed = user_gql_client.execute(
        ADDRESSES_MUTATION,
        variables={
            "profileInput": {
                "removeAddresses": [
                    to_global_id(type="AddressNode", id=another_address.id)
                ]
            }
        },
    )

    assert executed["data"]["updateMyProfile"] is None
    assert_match_error_code(executed, "OBJECT_DOES_NOT_EXIST_ERROR")
    assert Address.objects.filter(id=another_address.id).exists()


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
