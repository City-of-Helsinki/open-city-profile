import factory.random
import pytest
from django.contrib.auth.models import AnonymousUser
from graphene.test import Client as GrapheneClient

from open_city_profile.middlewares import GQLDataLoaders
from open_city_profile.schema import schema
from open_city_profile.tests.factories import (
    GroupFactory,
    SuperuserFactory,
    UserFactory,
)
from open_city_profile.views import GraphQLView


class GraphQLClient(GrapheneClient):
    def execute(self, *args, **kwargs):
        """
        Custom wrapper on the execute method, allows adding the
        GQL DataLoaders middleware, since it has to be added to make
        the DataLoaders available through the context.
        """
        return super().execute(*args, middleware=[GQLDataLoaders()], **kwargs)


@pytest.fixture(autouse=True)
def autouse_db(db):
    pass


@pytest.fixture(autouse=True)
def set_random_seed():
    factory.random.reseed_random(666)


@pytest.fixture(autouse=True)
def email_setup(settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"


@pytest.fixture
def user():
    return UserFactory()


@pytest.fixture
def anon_user():
    return AnonymousUser()


@pytest.fixture
def superuser():
    return SuperuserFactory()


@pytest.fixture
def group():
    return GroupFactory()


def get_gql_client_with_error_formating():
    return GraphQLClient(schema, format_error=GraphQLView.format_error)


@pytest.fixture
def gql_client():
    gql_client = get_gql_client_with_error_formating()
    return gql_client


@pytest.fixture
def anon_user_gql_client(anon_user):
    gql_client = get_gql_client_with_error_formating()
    gql_client.user = anon_user
    return gql_client


@pytest.fixture
def user_gql_client(user):
    gql_client = get_gql_client_with_error_formating()
    gql_client.user = user
    return gql_client


@pytest.fixture
def superuser_gql_client(superuser):
    gql_client = get_gql_client_with_error_formating()
    gql_client.user = superuser
    return gql_client
