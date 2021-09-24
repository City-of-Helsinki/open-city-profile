import inflection
import pytest

pytest.register_assert_rewrite("open_city_profile.tests.asserts")


def to_graphql_name(s):
    return inflection.camelize(s, False)
