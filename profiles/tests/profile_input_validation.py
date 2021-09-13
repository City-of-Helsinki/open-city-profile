from open_city_profile.tests.asserts import assert_match_error_code


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

    def test_adding_phone_with_empty_phone_number_causes_a_validation_error(
        self, user_gql_client, phone_data
    ):
        profile_input = {
            "addPhones": [{"phone": "", "phoneType": phone_data["phone_type"]}],
        }

        executed = self.execute_query(user_gql_client, profile_input)

        assert_match_error_code(executed, "VALIDATION_ERROR")
