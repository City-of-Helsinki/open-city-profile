import uuid

import pytest
from graphql_relay.node.node import from_global_id
from guardian.shortcuts import assign_perm

from open_city_profile.tests import to_graphql_name
from open_city_profile.tests.asserts import assert_match_error_code
from profiles.enums import EmailType
from profiles.models import (
    Profile,
    VerifiedPersonalInformation,
    VerifiedPersonalInformationPermanentAddress,
    VerifiedPersonalInformationPermanentForeignAddress,
    VerifiedPersonalInformationTemporaryAddress,
)
from profiles.tests.factories import EmailFactory

from .conftest import (
    VERIFIED_PERSONAL_INFORMATION_ADDRESS_FIELD_NAMES,
    VERIFIED_PERSONAL_INFORMATION_ADDRESS_TYPES,
)


def execute_mutation(input_data, gql_client):
    user = gql_client.user

    assign_perm("profiles.manage_verified_personal_information", user)

    query = """
        mutation createOrUpdateProfileWithVerifiedPersonalInformation(
            $input: CreateOrUpdateProfileWithVerifiedPersonalInformationMutationInput!
        ) {
            prof: createOrUpdateProfileWithVerifiedPersonalInformation(
                input: $input,
            ) {
                profile {
                    id,
                }
            }
        }
    """

    return gql_client.execute(query, variables={"input": input_data})


def execute_successful_mutation(input_data, gql_client):
    executed = execute_mutation(input_data, gql_client)

    global_profile_id = executed["data"]["prof"]["profile"]["id"]
    profile_id = uuid.UUID(from_global_id(global_profile_id)[1])

    return Profile.objects.get(pk=profile_id)


def generate_input_data(user_id, overrides={}):
    vpi_data = {
        "firstName": "John",
        "lastName": "Smith",
        "givenName": "Johnny",
        "nationalIdentificationNumber": "220202A1234",
        "email": "john.smith@domain.example",
        "municipalityOfResidence": "Helsinki",
        "municipalityOfResidenceNumber": "091",
        "permanentAddress": {
            "streetAddress": "Permanent Street 1",
            "postalCode": "12345",
            "postOffice": "Permanent City",
        },
        "temporaryAddress": {
            "streetAddress": "Temporary Street 2",
            "postalCode": "98765",
            "postOffice": "Temporary City",
        },
        "permanentForeignAddress": {
            "streetAddress": "Permanent foreign address",
            "additionalAddress": "Additional foreign address",
            "countryCode": "JP",
        },
    }
    vpi_data.update(overrides)

    input_data = {
        "userId": str(user_id),
        "profile": {"verifiedPersonalInformation": vpi_data},
    }

    return input_data


def execute_successful_profile_creation_test(user_id, gql_client):
    input_data = generate_input_data(user_id)

    profile = execute_successful_mutation(input_data, gql_client)

    assert profile.user.uuid == user_id
    verified_personal_information = profile.verified_personal_information
    assert verified_personal_information.first_name == "John"
    assert verified_personal_information.last_name == "Smith"
    assert verified_personal_information.given_name == "Johnny"
    assert verified_personal_information.national_identification_number == "220202A1234"
    assert verified_personal_information.email == "john.smith@domain.example"
    assert verified_personal_information.municipality_of_residence == "Helsinki"
    assert verified_personal_information.municipality_of_residence_number == "091"
    permanent_address = verified_personal_information.permanent_address
    assert permanent_address.street_address == "Permanent Street 1"
    assert permanent_address.postal_code == "12345"
    assert permanent_address.post_office == "Permanent City"
    temporary_address = verified_personal_information.temporary_address
    assert temporary_address.street_address == "Temporary Street 2"
    assert temporary_address.postal_code == "98765"
    assert temporary_address.post_office == "Temporary City"
    permanent_foreign_address = verified_personal_information.permanent_foreign_address
    assert permanent_foreign_address.street_address == "Permanent foreign address"
    assert permanent_foreign_address.additional_address == "Additional foreign address"
    assert permanent_foreign_address.country_code == "JP"


def test_profile_with_verified_personal_information_can_be_created(user_gql_client):
    execute_successful_profile_creation_test(uuid.uuid1(), user_gql_client)


def test_manage_verified_personal_information_permission_is_needed(user_gql_client):
    query = """
    mutation {
        createOrUpdateProfileWithVerifiedPersonalInformation(
            input: {
                userId: "03117666-117D-4F6B-80B1-A3A92B389711",
                profile: {
                    verifiedPersonalInformation: {
                    }
                }
            }
        ) {
            profile {
                id,
            }
        }
    }
    """

    executed = user_gql_client.execute(query)
    assert executed["errors"][0]["extensions"]["code"] == "PERMISSION_DENIED_ERROR"


def test_existing_user_is_used(user, user_gql_client):
    execute_successful_profile_creation_test(user.uuid, user_gql_client)


def test_existing_profile_without_verified_personal_information_is_updated(
    profile, user_gql_client
):
    execute_successful_profile_creation_test(profile.user.uuid, user_gql_client)


def test_existing_profile_with_verified_personal_information_is_updated(
    profile_with_verified_personal_information, user_gql_client
):
    execute_successful_profile_creation_test(
        profile_with_verified_personal_information.user.uuid, user_gql_client,
    )


def test_all_basic_fields_can_be_set_to_null(user_gql_client):
    input_data = {
        "userId": "03117666-117D-4F6B-80B1-A3A92B389711",
        "profile": {
            "verifiedPersonalInformation": {
                "firstName": None,
                "lastName": None,
                "givenName": None,
                "nationalIdentificationNumber": None,
                "email": None,
                "municipalityOfResidence": None,
                "municipalityOfResidenceNumber": None,
            },
        },
    }

    profile = execute_successful_mutation(input_data, user_gql_client)

    verified_personal_information = profile.verified_personal_information
    assert verified_personal_information.first_name == ""
    assert verified_personal_information.last_name == ""
    assert verified_personal_information.given_name == ""
    assert verified_personal_information.national_identification_number == ""
    assert verified_personal_information.email == ""
    assert verified_personal_information.municipality_of_residence == ""
    assert verified_personal_information.municipality_of_residence_number == ""


@pytest.mark.parametrize(
    "address_type", VERIFIED_PERSONAL_INFORMATION_ADDRESS_TYPES,
)
@pytest.mark.parametrize("address_field_index_to_nullify", [0, 1, 2])
def test_address_fields_can_be_set_to_null(
    profile_with_verified_personal_information,
    address_type,
    address_field_index_to_nullify,
    user_gql_client,
):
    address_field_names = VERIFIED_PERSONAL_INFORMATION_ADDRESS_FIELD_NAMES[
        address_type
    ]
    field_to_nullify = address_field_names[address_field_index_to_nullify]

    existing_address = getattr(
        profile_with_verified_personal_information.verified_personal_information,
        address_type,
    )

    user_id = profile_with_verified_personal_information.user.uuid

    address_data = {to_graphql_name(field_to_nullify): None}

    input_data = {
        "userId": str(user_id),
        "profile": {
            "verifiedPersonalInformation": {
                to_graphql_name(address_type): address_data
            },
        },
    }

    profile = execute_successful_mutation(input_data, user_gql_client)

    address = getattr(profile.verified_personal_information, address_type)

    for field_name in address_field_names:
        if field_name == field_to_nullify:
            assert getattr(address, field_name) == ""
        else:
            assert getattr(address, field_name) == getattr(existing_address, field_name)


@pytest.mark.parametrize(
    "address_type", VERIFIED_PERSONAL_INFORMATION_ADDRESS_TYPES,
)
def test_do_not_touch_an_address_if_it_is_not_included_in_the_mutation(
    profile_with_verified_personal_information, address_type, user_gql_client,
):
    existing_address = getattr(
        profile_with_verified_personal_information.verified_personal_information,
        address_type,
    )

    user_id = profile_with_verified_personal_information.user.uuid

    input_data = {
        "userId": str(user_id),
        "profile": {"verifiedPersonalInformation": {}},
    }

    profile = execute_successful_mutation(input_data, user_gql_client)

    verified_personal_information = profile.verified_personal_information
    address = getattr(verified_personal_information, address_type)

    for field_name in VERIFIED_PERSONAL_INFORMATION_ADDRESS_FIELD_NAMES[address_type]:
        assert getattr(address, field_name) == getattr(existing_address, field_name)


@pytest.mark.parametrize(
    "address_type", VERIFIED_PERSONAL_INFORMATION_ADDRESS_TYPES,
)
def test_delete_an_address_if_it_no_longer_has_any_data(
    profile_with_verified_personal_information, address_type, user_gql_client,
):
    user_id = profile_with_verified_personal_information.user.uuid

    address_fields = {}
    for name in VERIFIED_PERSONAL_INFORMATION_ADDRESS_FIELD_NAMES[address_type]:
        address_fields[to_graphql_name(name)] = ""

    input_data = {
        "userId": str(user_id),
        "profile": {
            "verifiedPersonalInformation": {
                to_graphql_name(address_type): address_fields
            },
        },
    }

    profile = execute_successful_mutation(input_data, user_gql_client)

    assert not hasattr(profile.verified_personal_information, address_type)


email_address = "test_email@domain.example"


def primary_email_input_data(user_id, email=email_address):
    return {
        "userId": str(user_id),
        "profile": {
            "primaryEmail": {"email": email},
            "verifiedPersonalInformation": {},
        },
    }


def test_set_primary_email_for_a_new_profile(user_gql_client):
    user_id = uuid.uuid1()

    input_data = primary_email_input_data(user_id)
    profile = execute_successful_mutation(input_data, user_gql_client)

    assert profile.emails.count() == 1
    email = profile.emails.first()
    assert email.email == email_address
    assert email.primary is True
    assert email.email_type == EmailType.NONE
    assert email.verified is False


def test_change_primary_email_for_an_existing_profile(user_gql_client):
    old_email = EmailFactory()
    user_id = old_email.profile.user.uuid

    input_data = primary_email_input_data(user_id)
    profile = execute_successful_mutation(input_data, user_gql_client)

    assert profile.emails.count() == 2

    email = profile.emails.get(primary=True)
    assert email.email == email_address
    assert email.email_type == EmailType.NONE
    assert email.verified is False

    email = profile.emails.get(pk=old_email.pk)
    assert email.email == old_email.email
    assert email.primary is False


@pytest.mark.parametrize("old_is_primary", (True, False))
def test_existing_primary_email_remains_when_trying_to_set_the_same_email_as_a_primary_email(
    old_is_primary, user_gql_client
):
    old_email = EmailFactory(email_type=EmailType.PERSONAL, primary=old_is_primary)
    user_id = old_email.profile.user.uuid

    input_data = primary_email_input_data(user_id, old_email.email)
    profile = execute_successful_mutation(input_data, user_gql_client)

    assert profile.emails.count() == 1
    email = profile.emails.first()
    assert email.email == old_email.email
    assert email.primary is True
    assert email.email_type == old_email.email_type


@pytest.mark.parametrize(
    "test_email", ("", " ", "not_an_email", " extra_white_space@address.example")
)
def test_deny_invalid_primary_email_address(test_email, user_gql_client):
    user_id = uuid.uuid1()

    input_data = primary_email_input_data(user_id, test_email)

    executed = execute_mutation(input_data, user_gql_client)

    assert_match_error_code(executed, "VALIDATION_ERROR")
    assert executed["data"]["prof"] is None


def service_input_data(user_id, service_client_id):
    user_id = str(user_id)
    return {
        "userId": user_id,
        "serviceClientId": service_client_id,
        "profile": {"verifiedPersonalInformation": {"firstName": "John"}},
    }


def execute_service_connection_test(
    user_id, service_in_mutation, expected_service_connections, gql_client
):
    input_data = service_input_data(
        user_id, service_in_mutation.client_ids.first().client_id
    )

    profile = execute_successful_mutation(input_data, gql_client)

    connected_services = profile.service_connections.all()

    assert connected_services.count() == len(expected_service_connections)
    for service in expected_service_connections:
        connection = connected_services.get(service=service)
        assert connection.service == service
        assert connection.enabled


def test_giving_non_existing_service_client_id_results_in_object_does_not_exist_error(
    user_gql_client,
):
    input_data = service_input_data(uuid.uuid1(), "not_existing")

    executed = execute_mutation(input_data, user_gql_client)

    assert_match_error_code(executed, "OBJECT_DOES_NOT_EXIST_ERROR")


def test_add_new_service_connections(
    service_factory, service_client_id_factory, user_gql_client
):
    user_id = uuid.uuid1()
    service1 = service_factory()
    service2 = service_factory()
    service_client_id_factory(service=service1)
    service_client_id_factory(service=service2)

    execute_service_connection_test(user_id, service1, [service1], user_gql_client)

    execute_service_connection_test(
        user_id, service2, [service1, service2], user_gql_client
    )


def test_adding_existing_connection_again_does_nothing(
    profile,
    service,
    service_connection_factory,
    service_client_id_factory,
    user_gql_client,
):
    service_client_id_factory(service=service)
    service_connection_factory(profile=profile, service=service, enabled=True)

    execute_service_connection_test(
        profile.user.uuid, service, [service], user_gql_client
    )


def test_enable_existing_disabled_service_connection(
    profile,
    service,
    service_connection_factory,
    service_client_id_factory,
    user_gql_client,
):
    service_client_id_factory(service=service)
    service_connection_factory(profile=profile, service=service, enabled=False)

    execute_service_connection_test(
        profile.user.uuid, service, [service], user_gql_client
    )


@pytest.mark.parametrize(
    "field_name",
    [
        "firstName",
        "lastName",
        "givenName",
        "nationalIdentificationNumber",
        "email",
        "municipalityOfResidence",
        "municipalityOfResidenceNumber",
    ],
)
def test_invalid_input_causes_a_validation_error(user_gql_client, field_name):
    input_data = generate_input_data(uuid.uuid1(), overrides={field_name: "x" * 1025})
    executed = execute_mutation(input_data, user_gql_client)

    assert executed["errors"][0]["extensions"]["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize(
    "address_type", VERIFIED_PERSONAL_INFORMATION_ADDRESS_TYPES,
)
@pytest.mark.parametrize("address_field_index", [0, 1, 2])
def test_invalid_address_input_causes_a_validation_error(
    user_gql_client, address_type, address_field_index,
):
    address_field_name = VERIFIED_PERSONAL_INFORMATION_ADDRESS_FIELD_NAMES[
        address_type
    ][address_field_index]
    address_fields = {to_graphql_name(address_field_name): "x" * 101}

    input_data = generate_input_data(
        uuid.uuid1(), overrides={to_graphql_name(address_type): address_fields},
    )
    executed = execute_mutation(input_data, user_gql_client)

    assert executed["errors"][0]["extensions"]["code"] == "VALIDATION_ERROR"


@pytest.mark.django_db(transaction=True)
def test_database_stays_unmodified_when_mutation_is_not_completed(user_gql_client):
    input_data = generate_input_data(uuid.uuid1(), overrides={"first": "x" * 101})
    execute_mutation(input_data, user_gql_client)

    assert Profile.objects.count() == 0
    assert VerifiedPersonalInformation.objects.count() == 0
    assert VerifiedPersonalInformationPermanentAddress.objects.count() == 0
    assert VerifiedPersonalInformationTemporaryAddress.objects.count() == 0
    assert VerifiedPersonalInformationPermanentForeignAddress.objects.count() == 0
