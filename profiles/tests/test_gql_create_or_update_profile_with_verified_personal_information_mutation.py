import uuid

import pytest
from graphql_relay.node.node import from_global_id
from guardian.shortcuts import assign_perm

from open_city_profile.tests import to_graphql_name
from open_city_profile.tests.asserts import assert_match_error_code
from profiles.models import (
    Profile,
    VerifiedPersonalInformation,
    VerifiedPersonalInformationPermanentAddress,
    VerifiedPersonalInformationPermanentForeignAddress,
    VerifiedPersonalInformationTemporaryAddress,
)
from services.enums import ServiceType

from .conftest import ProfileWithVerifiedPersonalInformationTestBase


class TestProfileWithVerifiedPersonalInformationCreation(
    ProfileWithVerifiedPersonalInformationTestBase
):
    @staticmethod
    def execute_mutation(input_data, rf, gql_client):
        user = gql_client.user

        assign_perm("profiles.manage_verified_personal_information", user)

        request = rf.post("/graphql")
        request.user = user

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

        return gql_client.execute(
            query, variables={"input": input_data}, context=request
        )

    @staticmethod
    def execute_successful_mutation(input_data, rf, gql_client):
        executed = TestProfileWithVerifiedPersonalInformationCreation.execute_mutation(
            input_data, rf, gql_client
        )

        global_profile_id = executed["data"]["prof"]["profile"]["id"]
        profile_id = uuid.UUID(from_global_id(global_profile_id)[1])

        return Profile.objects.get(pk=profile_id)

    @staticmethod
    def execute_successful_profile_creation_test(user_id, rf, gql_client):
        input_data = {
            "userId": str(user_id),
            "profile": {
                "verifiedPersonalInformation": {
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
                        "streetAddress": "〒100-8994",
                        "additionalAddress": "東京都中央区八重洲1-5-3",
                        "countryCode": "JP",
                    },
                },
            },
        }

        profile = TestProfileWithVerifiedPersonalInformationCreation.execute_successful_mutation(
            input_data, rf, gql_client
        )

        assert profile.user.uuid == user_id
        verified_personal_information = profile.verified_personal_information
        assert verified_personal_information.first_name == "John"
        assert verified_personal_information.last_name == "Smith"
        assert verified_personal_information.given_name == "Johnny"
        assert (
            verified_personal_information.national_identification_number
            == "220202A1234"
        )
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
        permanent_foreign_address = (
            verified_personal_information.permanent_foreign_address
        )
        assert permanent_foreign_address.street_address == "〒100-8994"
        assert permanent_foreign_address.additional_address == "東京都中央区八重洲1-5-3"
        assert permanent_foreign_address.country_code == "JP"

    def test_profile_with_verified_personal_information_can_be_created(
        self, rf, user_gql_client
    ):
        self.execute_successful_profile_creation_test(uuid.uuid1(), rf, user_gql_client)

    def test_manage_verified_personal_information_permission_is_needed(
        self, rf, user_gql_client
    ):
        request = rf.post("/graphql")
        request.user = user_gql_client.user

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

        executed = user_gql_client.execute(query, context=request)
        assert executed["errors"][0]["extensions"]["code"] == "PERMISSION_DENIED_ERROR"

    def test_existing_user_is_used(self, user, rf, user_gql_client):
        self.execute_successful_profile_creation_test(user.uuid, rf, user_gql_client)

    def test_existing_profile_without_verified_personal_information_is_updated(
        self, profile, rf, user_gql_client
    ):
        self.execute_successful_profile_creation_test(
            profile.user.uuid, rf, user_gql_client
        )

    def test_existing_profile_with_verified_personal_information_is_updated(
        self, profile_with_verified_personal_information, rf, user_gql_client
    ):
        self.execute_successful_profile_creation_test(
            profile_with_verified_personal_information.user.uuid, rf, user_gql_client,
        )

    def test_all_basic_fields_can_be_set_to_null(self, rf, user_gql_client):
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

        profile = self.execute_successful_mutation(input_data, rf, user_gql_client)

        verified_personal_information = profile.verified_personal_information
        assert verified_personal_information.first_name == ""
        assert verified_personal_information.last_name == ""
        assert verified_personal_information.given_name == ""
        assert verified_personal_information.national_identification_number == ""
        assert verified_personal_information.email == ""
        assert verified_personal_information.municipality_of_residence == ""
        assert verified_personal_information.municipality_of_residence_number == ""

    @pytest.mark.parametrize(
        "address_type", ProfileWithVerifiedPersonalInformationTestBase.ADDRESS_TYPES,
    )
    @pytest.mark.parametrize("address_field_index_to_nullify", [0, 1, 2])
    def test_address_fields_can_be_set_to_null(
        self,
        profile_with_verified_personal_information,
        address_type,
        address_field_index_to_nullify,
        rf,
        user_gql_client,
    ):
        address_field_names = self.ADDRESS_FIELD_NAMES[address_type]
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

        profile = self.execute_successful_mutation(input_data, rf, user_gql_client)

        address = getattr(profile.verified_personal_information, address_type)

        for field_name in address_field_names:
            if field_name == field_to_nullify:
                assert getattr(address, field_name) == ""
            else:
                assert getattr(address, field_name) == getattr(
                    existing_address, field_name
                )

    @pytest.mark.parametrize(
        "address_type", ProfileWithVerifiedPersonalInformationTestBase.ADDRESS_TYPES,
    )
    def test_do_not_touch_an_address_if_it_is_not_included_in_the_mutation(
        self,
        profile_with_verified_personal_information,
        address_type,
        rf,
        user_gql_client,
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

        profile = self.execute_successful_mutation(input_data, rf, user_gql_client)

        verified_personal_information = profile.verified_personal_information
        address = getattr(verified_personal_information, address_type)

        for field_name in self.ADDRESS_FIELD_NAMES[address_type]:
            assert getattr(address, field_name) == getattr(existing_address, field_name)

    @pytest.mark.parametrize(
        "address_type", ProfileWithVerifiedPersonalInformationTestBase.ADDRESS_TYPES,
    )
    def test_delete_an_address_if_it_no_longer_has_any_data(
        self,
        profile_with_verified_personal_information,
        address_type,
        rf,
        user_gql_client,
    ):
        user_id = profile_with_verified_personal_information.user.uuid

        address_fields = {}
        for name in self.ADDRESS_FIELD_NAMES[address_type]:
            address_fields[to_graphql_name(name)] = ""

        input_data = {
            "userId": str(user_id),
            "profile": {
                "verifiedPersonalInformation": {
                    to_graphql_name(address_type): address_fields
                },
            },
        }

        profile = TestProfileWithVerifiedPersonalInformationCreation.execute_successful_mutation(
            input_data, rf, user_gql_client
        )

        assert not hasattr(profile.verified_personal_information, address_type)

    @staticmethod
    def service_input_data(user_id, service_client_id):
        user_id = str(user_id)
        return {
            "userId": user_id,
            "serviceClientId": service_client_id,
            "profile": {"verifiedPersonalInformation": {"firstName": "John"}},
        }

    @staticmethod
    def execute_service_connection_test(
        user_id, service_in_mutation, expected_service_connections, rf, gql_client
    ):
        input_data = TestProfileWithVerifiedPersonalInformationCreation.service_input_data(
            user_id, service_in_mutation.client_ids.first().client_id
        )

        profile = TestProfileWithVerifiedPersonalInformationCreation.execute_successful_mutation(
            input_data, rf, gql_client
        )

        connected_services = profile.service_connections.all()

        assert connected_services.count() == len(expected_service_connections)
        for service in expected_service_connections:
            connection = connected_services.get(service=service)
            assert connection.service == service
            assert connection.enabled

    def test_giving_non_existing_service_client_id_results_in_object_does_not_exist_error(
        self, rf, user_gql_client
    ):
        input_data = self.service_input_data(uuid.uuid1(), "not_existing")

        executed = self.execute_mutation(input_data, rf, user_gql_client)

        assert_match_error_code(executed, "OBJECT_DOES_NOT_EXIST_ERROR")

    def test_add_new_service_connections(
        self, service_factory, service_client_id_factory, rf, user_gql_client
    ):
        user_id = uuid.uuid1()
        service1 = service_factory(service_type=ServiceType.BERTH)
        service2 = service_factory(service_type=ServiceType.YOUTH_MEMBERSHIP)
        service_client_id_factory(service=service1)
        service_client_id_factory(service=service2)

        self.execute_service_connection_test(
            user_id, service1, [service1], rf, user_gql_client
        )

        self.execute_service_connection_test(
            user_id, service2, [service1, service2], rf, user_gql_client
        )

    def test_adding_existing_connection_again_does_nothing(
        self,
        profile,
        service,
        service_connection_factory,
        service_client_id_factory,
        rf,
        user_gql_client,
    ):
        service_client_id_factory(service=service)
        service_connection_factory(profile=profile, service=service, enabled=True)

        self.execute_service_connection_test(
            profile.user.uuid, service, [service], rf, user_gql_client
        )

    def test_enable_existing_disabled_service_connection(
        self,
        profile,
        service,
        service_connection_factory,
        service_client_id_factory,
        rf,
        user_gql_client,
    ):
        service_client_id_factory(service=service)
        service_connection_factory(profile=profile, service=service, enabled=False)

        self.execute_service_connection_test(
            profile.user.uuid, service, [service], rf, user_gql_client
        )

    @staticmethod
    def execute_mutation_with_invalid_input(rf, gql_client):
        input_data = {
            "userId": "03117666-117D-4F6B-80B1-A3A92B389711",
            "profile": {
                "verifiedPersonalInformation": {
                    "permanentForeignAddress": {"countryCode": "France"}
                }
            },
        }

        return TestProfileWithVerifiedPersonalInformationCreation.execute_mutation(
            input_data, rf, gql_client
        )

    def test_invalid_input_causes_a_validation_error(self, rf, user_gql_client):
        executed = self.execute_mutation_with_invalid_input(rf, user_gql_client)
        assert executed["errors"][0]["extensions"]["code"] == "VALIDATION_ERROR"

    @pytest.mark.django_db(transaction=True)
    def test_database_stays_unmodified_when_mutation_is_not_completed(
        self, rf, user_gql_client
    ):
        self.execute_mutation_with_invalid_input(rf, user_gql_client)

        assert Profile.objects.count() == 0
        assert VerifiedPersonalInformation.objects.count() == 0
        assert VerifiedPersonalInformationPermanentAddress.objects.count() == 0
        assert VerifiedPersonalInformationTemporaryAddress.objects.count() == 0
        assert VerifiedPersonalInformationPermanentForeignAddress.objects.count() == 0
