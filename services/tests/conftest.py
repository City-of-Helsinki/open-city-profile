import pytest
from graphene.test import Client as GraphQLClient

from open_city_profile.schema import schema
from services.tests.factories import UserFactory


@pytest.fixture(autouse=True)
def allow_global_access_to_test_db(transactional_db):
    pass


@pytest.fixture
def user():
    return UserFactory()


@pytest.fixture
def user_gql_client(user):
    api_client = GraphQLClient(schema)
    api_client.user = user
    return api_client
