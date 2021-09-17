from graphql_relay import to_global_id

from open_city_profile.tests.asserts import assert_match_error_code
from profiles.models import Profile

from .factories import PhoneFactory


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
