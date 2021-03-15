from datetime import datetime, timezone

import factory.random
import pytest
from django.contrib.auth.models import AnonymousUser
from django.core.management import call_command
from django.test import RequestFactory
from graphene.test import Client as GrapheneClient
from graphql import build_client_schema, introspection_query
from helusers.authz import UserAuthorization

from open_city_profile.graphene import GQLDataLoaders
from open_city_profile.schema import schema
from open_city_profile.tests.factories import (
    GroupFactory,
    SuperuserFactory,
    UserFactory,
)
from open_city_profile.views import GraphQLView


class GraphQLClient(GrapheneClient):
    def execute(
        self, *args, auth_token_payload=None, service=None, context=None, **kwargs
    ):
        """
        Custom wrapper on the execute method, allows adding the
        GQL DataLoaders middleware, since it has to be added to make
        the DataLoaders available through the context.
        """
        if context is None:
            context = RequestFactory().post("/graphql")

        if not hasattr(context, "user") and hasattr(self, "user"):
            context.user = self.user

        if (
            hasattr(context, "user")
            and context.user.is_authenticated
            and not hasattr(context, "user_auth")
        ):
            context.user_auth = UserAuthorization(
                context.user, auth_token_payload or {}
            )

        if service is not None:
            context.service = service

        return super().execute(
            *args, context=context, middleware=[GQLDataLoaders()], **kwargs
        )


@pytest.fixture(autouse=True)
def autouse_db(db):
    pass


@pytest.fixture
def migration_test_db(request, transactional_db):
    def reset_migrations():
        call_command("migrate", verbosity=0)

    request.addfinalizer(reset_migrations)

    return transactional_db


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


def _get_gql_client_with_error_formating():
    return GraphQLClient(schema, format_error=GraphQLView.format_error)


@pytest.fixture
def anon_user_gql_client(anon_user):
    gql_client = _get_gql_client_with_error_formating()
    gql_client.user = anon_user
    return gql_client


@pytest.fixture
def user_gql_client(user):
    gql_client = _get_gql_client_with_error_formating()
    gql_client.user = user
    return gql_client


@pytest.fixture
def superuser_gql_client(superuser):
    gql_client = _get_gql_client_with_error_formating()
    gql_client.user = superuser
    return gql_client


@pytest.fixture
def gql_schema(anon_user_gql_client):
    introspection = anon_user_gql_client.execute(introspection_query)
    return build_client_schema(introspection["data"])


def get_unix_timestamp_now():
    return int(datetime.now(tz=timezone.utc).timestamp())


@pytest.fixture
def unix_timestamp_now():
    return get_unix_timestamp_now()
