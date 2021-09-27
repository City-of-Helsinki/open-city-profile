import inflection
import pytest

pytest.register_assert_rewrite("open_city_profile.tests.asserts")


def to_graphql_name(s):
    return inflection.camelize(s, False)


def to_graphql_object(dic):
    return dict([(to_graphql_name(k), v) for k, v in dic.items()])
