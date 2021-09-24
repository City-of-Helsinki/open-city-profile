import pytest
from graphql_relay import to_global_id

from open_city_profile.tests.asserts import assert_match_error_code
from profiles.models import Profile

from .factories import EmailFactory, PhoneFactory


class ProfileInputValidationBase:
    def execute_query(self, user_gql_client, profile_input):
        """This method needs to be implemented by sub classes.

        Executes the GraphQL query, perhaps with something like
        user_gql_client(query, variables={"profile_input": profile_input}),
        and returns the result. The implementation specifies the used query
        and can also provide extra input to the query as needed."""
        raise NotImplementedError(
            "execute_query needs to be implemented in a sub class."
        )

    def _execute_query(self, user_gql_client, profile_input):
        return self.execute_query(user_gql_client, profile_input)

    @pytest.mark.parametrize("field_name", ["firstName", "lastName", "nickname"])
    def test_giving_too_long_name_field_causes_a_validation_error(
        self, field_name, user_gql_client
    ):
        profile_input = {field_name: "x" * 256}

        executed = self._execute_query(user_gql_client, profile_input)

        assert_match_error_code(executed, "VALIDATION_ERROR")

    def test_all_name_fields_can_be_set_to_null(self, user_gql_client):
        profile_input = {
            "firstName": None,
            "lastName": None,
            "nickname": None,
        }

        executed = self._execute_query(user_gql_client, profile_input)

        assert "errors" not in executed, executed.get("errors")

    @pytest.mark.parametrize("invalid_email", ["", "not-an-email"])
    def test_adding_invalid_email_address_causes_an_invalid_email_format_error(
        self, invalid_email, email_data, user_gql_client
    ):
        profile_input = {
            "addEmails": [
                {"email": invalid_email, "emailType": email_data["email_type"]}
            ],
        }

        executed = self._execute_query(user_gql_client, profile_input)

        assert_match_error_code(executed, "INVALID_EMAIL_FORMAT")

    def test_adding_phone_with_empty_phone_number_causes_a_validation_error(
        self, user_gql_client, phone_data
    ):
        profile_input = {
            "addPhones": [{"phone": "", "phoneType": phone_data["phone_type"]}],
        }

        executed = self._execute_query(user_gql_client, profile_input)

        assert_match_error_code(executed, "VALIDATION_ERROR")

    def test_giving_invalid_ssn_causes_a_validation_error(self, user_gql_client):
        profile_input = {
            "sensitivedata": {"ssn": "101010X1234"},
        }

        executed = self._execute_query(user_gql_client, profile_input)

        assert_match_error_code(executed, "VALIDATION_ERROR")


class ExistingProfileInputValidationBase(ProfileInputValidationBase):
    def create_profile(self, user_making_the_request) -> Profile:
        """This method needs to be implemented by sub classes.

        Creates and returns a pre-existing Profile for the test.
        Receives the User making the GraphQL query as an argument.

        This method is called before execute_query for a test method
        is called. The created Profile is available as self.profile
        in execute_query.
        """
        raise NotImplementedError(
            "create_profile needs to be implemented in a sub class."
        )

    def _get_profile(self, user):
        if not hasattr(self, "profile"):
            self.profile = self.create_profile(user)

        return self.profile

    def _execute_query(self, user_gql_client, profile_input):
        # Ensure Profile has been created
        self._get_profile(user_gql_client.user)
        return super()._execute_query(user_gql_client, profile_input)

    @pytest.mark.parametrize("invalid_email", [None, "", "not-an-email"])
    def test_updating_to_invalid_email_address_causes_an_invalid_email_format_error(
        self, invalid_email, user_gql_client
    ):
        profile = self._get_profile(user_gql_client.user)
        email = EmailFactory(profile=profile, primary=False)

        profile_input = {
            "updateEmails": [
                {
                    "id": to_global_id(type="EmailNode", id=email.id),
                    "email": invalid_email,
                }
            ],
        }

        executed = self._execute_query(user_gql_client, profile_input)

        assert_match_error_code(executed, "INVALID_EMAIL_FORMAT")

    def test_updating_phone_number_with_empty_phone_number_causes_a_validation_error(
        self, user_gql_client, empty_string_value
    ):
        profile = self._get_profile(user_gql_client.user)
        phone = PhoneFactory(profile=profile)

        profile_input = {
            "updatePhones": [
                {
                    "id": to_global_id(type="PhoneNode", id=phone.id),
                    "phone": empty_string_value,
                }
            ],
        }

        executed = self._execute_query(user_gql_client, profile_input)

        assert_match_error_code(executed, "VALIDATION_ERROR")
