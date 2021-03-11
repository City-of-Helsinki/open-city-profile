import pytest
from helusers.authz import UserAuthorization

from open_city_profile.tests import to_graphql_name
from open_city_profile.tests.asserts import assert_match_error_code
from subscriptions.models import Subscription
from subscriptions.tests.factories import (
    SubscriptionTypeCategoryFactory,
    SubscriptionTypeFactory,
)

from .conftest import ProfileWithVerifiedPersonalInformationTestBase
from .factories import (
    AddressFactory,
    EmailFactory,
    PhoneFactory,
    ProfileFactory,
    ProfileWithPrimaryEmailFactory,
    SensitiveDataFactory,
    VerifiedPersonalInformationFactory,
)


def test_normal_user_can_query_emails(user_gql_client):
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
    executed = user_gql_client.execute(query)
    assert dict(executed["data"]) == expected_data


def test_normal_user_can_query_phones(user_gql_client):
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
    executed = user_gql_client.execute(query)
    assert dict(executed["data"]) == expected_data


def test_normal_user_can_query_addresses(user_gql_client):
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
    executed = user_gql_client.execute(query)
    assert dict(executed["data"]) == expected_data


def test_normal_user_can_query_primary_contact_details(user_gql_client):
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
    executed = user_gql_client.execute(query)
    assert dict(executed["data"]) == expected_data


class TestProfileWithVerifiedPersonalInformation(
    ProfileWithVerifiedPersonalInformationTestBase
):
    QUERY = """
        {
            myProfile {
                verifiedPersonalInformation {
                    firstName
                    lastName
                    givenName
                    nationalIdentificationNumber
                    email
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

    @staticmethod
    def _execute_query(rf, gql_client, loa="substantial"):
        user = gql_client.user

        request = rf.post("/graphql")
        request.user = user

        token_payload = {
            "loa": loa,
        }
        request.user_auth = UserAuthorization(user, token_payload)

        return gql_client.execute(
            TestProfileWithVerifiedPersonalInformation.QUERY, context=request
        )

    def test_when_verified_personal_infomation_does_not_exist_returns_null(
        self, rf, user_gql_client
    ):
        ProfileFactory(user=user_gql_client.user)

        executed = self._execute_query(rf, user_gql_client)

        assert "errors" not in executed
        assert executed["data"]["myProfile"]["verifiedPersonalInformation"] is None

    def test_normal_user_can_query_verified_personal_information(
        self, rf, user_gql_client
    ):
        profile = ProfileFactory(user=user_gql_client.user)
        verified_personal_information = VerifiedPersonalInformationFactory(
            profile=profile
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
                    "email": verified_personal_information.email,
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

        executed = self._execute_query(rf, user_gql_client)

        assert executed["data"] == expected_data

    @pytest.mark.parametrize(
        "address_type", ProfileWithVerifiedPersonalInformationTestBase.ADDRESS_TYPES,
    )
    def test_when_address_does_not_exist_returns_null(
        self, address_type, rf, user_gql_client
    ):
        profile = ProfileFactory(user=user_gql_client.user)
        VerifiedPersonalInformationFactory(
            profile=profile, **{address_type: None},
        )

        executed = self._execute_query(rf, user_gql_client)

        assert "errors" not in executed

        received_info = executed["data"]["myProfile"]["verifiedPersonalInformation"]
        for at in self.ADDRESS_TYPES:
            received_address = received_info[to_graphql_name(at)]
            if at == address_type:
                assert received_address is None
            else:
                assert isinstance(received_address, dict)

    @pytest.mark.parametrize("loa", ["substantial", "high"])
    def test_high_enough_level_of_assurance_gains_access(
        self, loa, rf, user_gql_client
    ):
        profile = ProfileFactory(user=user_gql_client.user)
        VerifiedPersonalInformationFactory(profile=profile)

        executed = self._execute_query(rf, user_gql_client, loa)

        assert not hasattr(executed, "errors")
        assert isinstance(
            executed["data"]["myProfile"]["verifiedPersonalInformation"], dict
        )

    @pytest.mark.parametrize("loa", [None, "low", "unknown"])
    def test_too_low_level_of_assurance_denies_access(self, loa, rf, user_gql_client):
        profile = ProfileFactory(user=user_gql_client.user)
        VerifiedPersonalInformationFactory(profile=profile)

        executed = self._execute_query(rf, user_gql_client, loa)

        assert_match_error_code(executed, "PERMISSION_DENIED_ERROR")

        assert executed["data"]["myProfile"]["verifiedPersonalInformation"] is None


def test_normal_user_can_query_his_own_profile(user_gql_client):
    profile = ProfileFactory(user=user_gql_client.user)

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
    executed = user_gql_client.execute(query)
    assert dict(executed["data"]) == expected_data


def test_normal_user_can_query_his_own_profiles_sensitivedata(user_gql_client):
    profile = ProfileFactory(user=user_gql_client.user)
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
    executed = user_gql_client.execute(query)
    assert dict(executed["data"]) == expected_data


def test_normal_user_can_query_his_own_profile_with_subscriptions(user_gql_client):
    profile = ProfileFactory(user=user_gql_client.user)
    cat = SubscriptionTypeCategoryFactory(
        code="TEST-CATEGORY-1", label="Test Category 1"
    )
    type_1 = SubscriptionTypeFactory(
        subscription_type_category=cat, code="TEST-1", label="Test 1"
    )
    type_2 = SubscriptionTypeFactory(
        subscription_type_category=cat, code="TEST-2", label="Test 2"
    )
    Subscription.objects.create(profile=profile, subscription_type=type_1, enabled=True)
    Subscription.objects.create(
        profile=profile, subscription_type=type_2, enabled=False
    )

    query = """
        {
            myProfile {
                firstName
                lastName
                subscriptions {
                    edges {
                        node {
                            enabled
                            subscriptionType {
                                order
                                code
                                label
                                subscriptionTypeCategory {
                                    code
                                    label
                                }
                            }
                        }
                    }
                }
            }
        }
    """
    expected_data = {
        "myProfile": {
            "firstName": profile.first_name,
            "lastName": profile.last_name,
            "subscriptions": {
                "edges": [
                    {
                        "node": {
                            "enabled": True,
                            "subscriptionType": {
                                "order": 1,
                                "code": "TEST-1",
                                "label": "Test 1",
                                "subscriptionTypeCategory": {
                                    "code": "TEST-CATEGORY-1",
                                    "label": "Test Category 1",
                                },
                            },
                        }
                    },
                    {
                        "node": {
                            "enabled": False,
                            "subscriptionType": {
                                "order": 2,
                                "code": "TEST-2",
                                "label": "Test 2",
                                "subscriptionTypeCategory": {
                                    "code": "TEST-CATEGORY-1",
                                    "label": "Test Category 1",
                                },
                            },
                        }
                    },
                ]
            },
        }
    }
    executed = user_gql_client.execute(query)
    assert dict(executed["data"]) == expected_data
