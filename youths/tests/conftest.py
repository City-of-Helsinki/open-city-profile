import factory.random
import pytest
from django.contrib.auth.models import AnonymousUser
from graphene.test import Client as GraphQLClient
from rest_framework.test import APIClient

from open_city_profile.schema import schema
from youths.tests.factories import (
    ProfileFactory,
    SuperuserFactory,
    UserFactory,
    YouthProfileFactory,
)


@pytest.fixture(autouse=True)
def allow_global_access_to_test_db(transactional_db):
    pass


@pytest.fixture(autouse=True)
def set_random_seed():
    factory.random.reseed_random(666)


@pytest.fixture
def anon_user():
    return AnonymousUser()


@pytest.fixture
def user():
    return UserFactory()


@pytest.fixture
def superuser():
    return SuperuserFactory()


@pytest.fixture
def profile(user):
    return ProfileFactory(user=user)


@pytest.fixture
def youth_profile(profile):
    return YouthProfileFactory(profile=profile)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user_api_client(user):
    api_client = APIClient()
    api_client.force_authenticate(user=user)
    api_client.user = user
    return api_client


@pytest.fixture
def superuser_api_client(superuser):
    api_client = APIClient()
    api_client.force_authenticate(user=superuser)
    api_client.user = superuser
    return api_client


@pytest.fixture
def gql_client():
    return GraphQLClient(schema)


@pytest.fixture
def anon_user_gql_client(anon_user):
    api_client = GraphQLClient(schema)
    api_client.user = anon_user
    return api_client


@pytest.fixture
def user_gql_client(user):
    api_client = GraphQLClient(schema)
    api_client.user = user
    return api_client


@pytest.fixture
def superuser_gql_client(superuser):
    api_client = GraphQLClient(schema)
    api_client.user = superuser
    return api_client
