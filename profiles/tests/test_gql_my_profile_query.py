import pytest

from open_city_profile.tests import to_graphql_name
from open_city_profile.tests.asserts import assert_match_error_code
from services.tests.factories import (
    AllowedDataFieldFactory,
    ServiceConnectionFactory,
    ServiceFactory,
)

from .conftest import VERIFIED_PERSONAL_INFORMATION_ADDRESS_TYPES
from .factories import (
    AddressFactory,
    EmailFactory,
    PhoneFactory,
    ProfileFactory,
    ProfileWithPrimaryEmailFactory,
    SensitiveDataFactory,
    VerifiedPersonalInformationFactory,
)


def test_normal_user_can_query_emails(user_gql_client, service):
    profile = ProfileWithPrimaryEmailFactory(user=user_gql_client.user)
    email = profile.emails.first()

    query = """
        {
            myProfile {
                emails {
                    edges {
                        node {
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
    service.allowed_data_fields.add(AllowedDataFieldFactory(field_name="email"))
    ServiceConnectionFactory(profile=profile, service=service)

    executed = user_gql_client.execute(query, service=service)
    assert dict(executed["data"]) == expected_data


def test_normal_user_can_query_phones(user_gql_client, service):
    profile = ProfileWithPrimaryEmailFactory(user=user_gql_client.user)
    phone = PhoneFactory(profile=profile)

    query = """
        {
            myProfile {
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
    service.allowed_data_fields.add(AllowedDataFieldFactory(field_name="phone"))
    ServiceConnectionFactory(profile=profile, service=service)

    executed = user_gql_client.execute(query, service=service)
    assert dict(executed["data"]) == expected_data


def test_normal_user_can_query_addresses(user_gql_client, service):
    profile = ProfileWithPrimaryEmailFactory(user=user_gql_client.user)
    address = AddressFactory(profile=profile)

    query = """
        {
            myProfile {
                addresses {
                    edges {
                        node {
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
    service.allowed_data_fields.add(AllowedDataFieldFactory(field_name="address"))
    ServiceConnectionFactory(profile=profile, service=service)

    executed = user_gql_client.execute(query, service=service)
    assert dict(executed["data"]) == expected_data


def test_normal_user_can_query_primary_contact_details(
    user_gql_client, execution_context_class, service
):
    profile = ProfileFactory(user=user_gql_client.user)
    phone = PhoneFactory(profile=profile, primary=True)
    email = EmailFactory(profile=profile, primary=True)
    address = AddressFactory(profile=profile, primary=True)
    PhoneFactory(profile=profile, primary=False)
    EmailFactory(profile=profile, primary=False)
    AddressFactory(profile=profile, primary=False)

    query = """
        {
            myProfile {
                primaryPhone {
                    phone,
                    phoneType,
                    primary
                },
                primaryEmail {
                    email,
                    emailType,
                    primary
                },
                primaryAddress {
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
    service.allowed_data_fields.add(
        AllowedDataFieldFactory(field_name="phone"),
        AllowedDataFieldFactory(field_name="email"),
        AllowedDataFieldFactory(field_name="address"),
    )
    ServiceConnectionFactory(profile=profile, service=service)

    executed = user_gql_client.execute(
        query, execution_context_class=execution_context_class, service=service
    )
    assert dict(executed["data"]) == expected_data


class TestProfileWithVerifiedPersonalInformation:
    QUERY = """
        {
            myProfile {
                verifiedPersonalInformation {
                    firstName
                    lastName
                    givenName
                    nationalIdentificationNumber
                    municipalityOfResidence
                    municipalityOfResidenceNumber
                    permanentAddress {
                        streetAddress
                        postalCode
                        postOffice
                    }
                    temporaryAddress {
                        streetAddress
                        postalCode
                        postOffice
                    }
                    permanentForeignAddress {
                        streetAddress
                        additionalAddress
                        countryCode
                    }
                }
            }
        }
    """

    @pytest.fixture(autouse=True)
    def setup_data(self, db, user_gql_client):
        self.user = user_gql_client.user
        self.client = user_gql_client
        self.service = ServiceFactory(is_profile_service=True)
        self.profile = ProfileFactory(user=user_gql_client.user)
        ServiceConnectionFactory(profile=self.profile, service=self.service)
        self._add_allowed_data_fields_to_service(self.service)

    def _create_allowed_data_fields(self):
        self.allowed_name = AllowedDataFieldFactory(field_name="name")
        self.allowed_address = AllowedDataFieldFactory(field_name="address")
        self.allowed_personal_identity_code = AllowedDataFieldFactory(
            field_name="personalidentitycode"
        )

    def _add_allowed_data_fields_to_service(self, service):
        if not getattr(self, "allowed_name", None):
            self._create_allowed_data_fields()

        service.allowed_data_fields.add(
            self.allowed_name,
            self.allowed_address,
            self.allowed_personal_identity_code,
        )

    def _execute_query(self, loa="substantial", service=None):
        token_payload = {
            "loa": loa,
        }

        kwargs = {"service": self.service}
        if service:
            kwargs["service"] = service

        return self.client.execute(
            TestProfileWithVerifiedPersonalInformation.QUERY,
            auth_token_payload=token_payload,
            **kwargs,
        )

    def test_when_verified_personal_information_does_not_exist_returns_null(self):
        executed = self._execute_query()

        assert "errors" not in executed
        assert executed["data"]["myProfile"]["verifiedPersonalInformation"] is None

    def test_normal_user_can_query_verified_personal_information(self):
        verified_personal_information = VerifiedPersonalInformationFactory(
            profile=self.profile
        )

        permanent_address = verified_personal_information.permanent_address
        temporary_address = verified_personal_information.temporary_address
        permanent_foreign_address = (
            verified_personal_information.permanent_foreign_address
        )

        expected_data = {
            "myProfile": {
                "verifiedPersonalInformation": {
                    "firstName": verified_personal_information.first_name,
                    "lastName": verified_personal_information.last_name,
                    "givenName": verified_personal_information.given_name,
                    "nationalIdentificationNumber": verified_personal_information.national_identification_number,
                    "municipalityOfResidence": verified_personal_information.municipality_of_residence,
                    "municipalityOfResidenceNumber": verified_personal_information.municipality_of_residence_number,
                    "permanentAddress": {
                        "streetAddress": permanent_address.street_address,
                        "postalCode": permanent_address.postal_code,
                        "postOffice": permanent_address.post_office,
                    },
                    "temporaryAddress": {
                        "streetAddress": temporary_address.street_address,
                        "postalCode": temporary_address.postal_code,
                        "postOffice": temporary_address.post_office,
                    },
                    "permanentForeignAddress": {
                        "streetAddress": permanent_foreign_address.street_address,
                        "additionalAddress": permanent_foreign_address.additional_address,
                        "countryCode": permanent_foreign_address.country_code,
                    },
                },
            }
        }

        executed = self._execute_query()

        assert executed["data"] == expected_data

    @pytest.mark.parametrize(
        "address_type", VERIFIED_PERSONAL_INFORMATION_ADDRESS_TYPES
    )
    def test_when_address_does_not_exist_returns_null(self, address_type):
        VerifiedPersonalInformationFactory(profile=self.profile, **{address_type: None})

        executed = self._execute_query()

        assert "errors" not in executed

        received_info = executed["data"]["myProfile"]["verifiedPersonalInformation"]
        for at in VERIFIED_PERSONAL_INFORMATION_ADDRESS_TYPES:
            received_address = received_info[to_graphql_name(at)]
            if at == address_type:
                assert received_address is None
            else:
                assert isinstance(received_address, dict)

    @pytest.mark.parametrize("loa", ["substantial", "high"])
    def test_high_enough_level_of_assurance_gains_access(self, loa):
        VerifiedPersonalInformationFactory(profile=self.profile)

        executed = self._execute_query(loa)

        assert not hasattr(executed, "errors")
        assert isinstance(
            executed["data"]["myProfile"]["verifiedPersonalInformation"], dict
        )

    @pytest.mark.parametrize("loa", [None, "low", "unknown"])
    def test_too_low_level_of_assurance_denies_access(self, loa):
        VerifiedPersonalInformationFactory(profile=self.profile)

        executed = self._execute_query(loa)

        assert_match_error_code(executed, "PERMISSION_DENIED_ERROR")

        assert executed["data"]["myProfile"]["verifiedPersonalInformation"] is None

    @pytest.mark.parametrize("with_serviceconnection", (True, False))
    def test_service_connection_required(self, with_serviceconnection):
        service = ServiceFactory()
        self._add_allowed_data_fields_to_service(service)
        VerifiedPersonalInformationFactory(profile=self.profile)
        if with_serviceconnection:
            ServiceConnectionFactory(profile=self.profile, service=service)

        executed = self.client.execute(
            TestProfileWithVerifiedPersonalInformation.QUERY,
            auth_token_payload={"loa": "substantial"},
            service=service,
        )

        if with_serviceconnection:
            assert not hasattr(executed, "errors")
            assert isinstance(
                executed["data"]["myProfile"]["verifiedPersonalInformation"], dict
            )
        else:
            assert_match_error_code(executed, "PERMISSION_DENIED_ERROR")
            assert executed["data"]["myProfile"] is None


def test_querying_non_existent_profile_doesnt_return_errors(user_gql_client, service):
    query = """
        {
            myProfile {
                firstName
                lastName
            }
        }
    """
    executed = user_gql_client.execute(query)

    assert "errors" not in executed, executed["errors"]
    assert executed["data"]["myProfile"] is None


@pytest.mark.parametrize("with_service", (True, False))
@pytest.mark.parametrize("with_serviceconnection", (True, False))
def test_normal_user_can_query_their_own_profile(
    user_gql_client, service, with_service, with_serviceconnection
):
    service.allowed_data_fields.add(AllowedDataFieldFactory(field_name="name"))
    profile = ProfileFactory(user=user_gql_client.user)
    if with_serviceconnection:
        ServiceConnectionFactory(profile=profile, service=service)

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
    executed = user_gql_client.execute(query, service=service if with_service else None)

    if with_service and with_serviceconnection:
        assert executed["data"] == expected_data
    elif not with_service:
        assert_match_error_code(executed, "SERVICE_NOT_IDENTIFIED_ERROR")
        assert executed["data"]["myProfile"] is None
    else:
        assert_match_error_code(executed, "PERMISSION_DENIED_ERROR")
        assert executed["data"]["myProfile"] is None


def test_normal_user_can_query_their_own_profiles_sensitivedata(
    user_gql_client, service
):
    service.allowed_data_fields.add(
        AllowedDataFieldFactory(field_name="name"),
        AllowedDataFieldFactory(field_name="personalidentitycode"),
    )
    profile = ProfileFactory(user=user_gql_client.user)
    ServiceConnectionFactory(profile=profile, service=service)
    sensitive_data = SensitiveDataFactory(profile=profile)

    query = """
        {
            myProfile {
                firstName
                sensitivedata {
                    ssn
                }
            }
        }
    """
    expected_data = {
        "myProfile": {
            "firstName": profile.first_name,
            "sensitivedata": {"ssn": sensitive_data.ssn},
        }
    }
    executed = user_gql_client.execute(query, service=service)
    assert dict(executed["data"]) == expected_data


def test_my_profile_always_allowed_fields(user_gql_client, service):
    profile = ProfileFactory(user=user_gql_client.user)
    ServiceConnectionFactory(profile=profile, service=service)

    query = """
        {
            myProfile {
                __typename
                id
                verifiedPersonalInformation {
                    __typename
                    firstName
                }
                serviceConnections {
                    edges {
                        node {
                            service {
                                id
                            }
                        }
                    }
                }
                language
                contactMethod
                loginMethods
            }
        }
    """

    executed = user_gql_client.execute(
        query, service=service, auth_token_payload={"loa": "substantial"}
    )

    assert "errors" not in executed


def test_my_profile_results_error_if_querying_fields_not_allowed(
    user_gql_client, service
):
    profile = ProfileFactory(user=user_gql_client.user)
    ServiceConnectionFactory(profile=profile, service=service)

    query = """
        {
            myProfile {
                firstName
                lastName
                sensitivedata {
                    ssn
                }
            }
        }
    """
    executed = user_gql_client.execute(query, service=service)
    assert_match_error_code(executed, "FIELD_NOT_ALLOWED_ERROR")
    assert executed["data"]["myProfile"] is None


def test_my_profile_results_error_if_querying_fields_not_allowed_and_shows_allowed(
    user_gql_client, service
):
    profile = ProfileFactory(user=user_gql_client.user)
    ServiceConnectionFactory(profile=profile, service=service)
    service.allowed_data_fields.add(AllowedDataFieldFactory(field_name="name"))

    query = """
        {
            myProfile {
                firstName
                lastName
                sensitivedata {
                    ssn
                }
            }
        }
    """
    executed = user_gql_client.execute(query, service=service)
    assert_match_error_code(executed, "FIELD_NOT_ALLOWED_ERROR")
    assert executed["data"]["myProfile"]["firstName"] == profile.first_name
    assert executed["data"]["myProfile"]["lastName"] == profile.last_name
    assert executed["data"]["myProfile"]["sensitivedata"] is None


def test_my_profile_checks_allowed_data_fields_for_single_query(
    user_gql_client, service
):
    profile = ProfileFactory(user=user_gql_client.user)
    ServiceConnectionFactory(profile=profile, service=service)
    service.allowed_data_fields.add(AllowedDataFieldFactory(field_name="name"))

    query = """
        {
            myProfile {
                firstName
                lastName
                sensitivedata {
                    ssn
                }
            }
        }
    """
    executed = user_gql_client.execute(query, service=service)
    assert_match_error_code(executed, "FIELD_NOT_ALLOWED_ERROR")
    assert executed["data"]["myProfile"]["firstName"] == profile.first_name
    assert executed["data"]["myProfile"]["lastName"] == profile.last_name
    assert executed["data"]["myProfile"]["sensitivedata"] is None


def test_my_profile_checks_allowed_data_fields_for_multiple_queries(
    user_gql_client, service
):
    profile = ProfileFactory(user=user_gql_client.user)
    ServiceConnectionFactory(profile=profile, service=service)
    service.allowed_data_fields.add(AllowedDataFieldFactory(field_name="name"))

    query = """
        {
            _service {
                __typename
            }
            myProfile {
                firstName
                lastName
                sensitivedata {
                    ssn
                }
            }
            services {
                edges {
                    node {
                        name
                    }
                }
            }
        }
    """
    executed = user_gql_client.execute(query, service=service)
    assert_match_error_code(executed, "FIELD_NOT_ALLOWED_ERROR")
    assert executed["data"]["myProfile"]["firstName"] == profile.first_name
    assert executed["data"]["myProfile"]["lastName"] == profile.last_name
    assert executed["data"]["myProfile"]["sensitivedata"] is None
    assert executed["data"]["services"] is None


@pytest.mark.parametrize(
    "amr_claim_value", ["suomi_fi", "helsinki_tunnus", "heltunnistussuomifi"]
)
def test_user_can_see_own_login_methods_with_correct_amr_claim(
    user_gql_client, profile, group, service, monkeypatch, amr_claim_value
):
    def mock_return(*_, **__):
        return {"suomi_fi", "password"}

    monkeypatch.setattr(
        "profiles.keycloak_integration.get_user_identity_providers", mock_return
    )

    profile = ProfileFactory(user=user_gql_client.user)
    ServiceConnectionFactory(profile=profile, service=service)

    query = """
        {
            myProfile {
                loginMethods
            }
        }
    """
    executed = user_gql_client.execute(
        query, auth_token_payload={"amr": amr_claim_value}, service=service
    )
    assert "errors" not in executed
    assert set(executed["data"]["myProfile"]["loginMethods"]) == {
        "SUOMI_FI",
        "PASSWORD",
    }


@pytest.mark.parametrize("amr_claim_value", [None, "helsinkiad"])
def test_user_cannot_see_own_login_methods_with_other_amr_claims(
    user_gql_client, profile, group, service, monkeypatch, amr_claim_value
):
    def mock_return(*_, **__):
        return {"this should not show up"}

    monkeypatch.setattr(
        "profiles.keycloak_integration.get_user_identity_providers", mock_return
    )

    profile = ProfileFactory(user=user_gql_client.user)
    ServiceConnectionFactory(profile=profile, service=service)

    query = """
        {
            myProfile {
                loginMethods
            }
        }
    """
    executed = user_gql_client.execute(
        query, auth_token_payload={"amr": amr_claim_value}, service=service
    )
    assert "errors" not in executed
    assert executed["data"]["myProfile"]["loginMethods"] == []


def test_user_does_not_see_non_enum_login_methods(
    user_gql_client, profile, group, service, monkeypatch
):
    def mock_return(*_, **__):
        return {"password", "this should not show up"}

    monkeypatch.setattr(
        "profiles.keycloak_integration.get_user_identity_providers", mock_return
    )

    profile = ProfileFactory(user=user_gql_client.user)
    ServiceConnectionFactory(profile=profile, service=service)

    query = """
        {
            myProfile {
                loginMethods
            }
        }
    """
    executed = user_gql_client.execute(
        query, auth_token_payload={"amr": "helsinki_tunnus"}, service=service
    )
    assert "errors" not in executed
    assert set(executed["data"]["myProfile"]["loginMethods"]) == {"PASSWORD"}
