from datetime import datetime, timezone

import factory.random
import pytest
from django.contrib.auth.models import AnonymousUser
from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import RequestFactory
from graphene.test import Client as GrapheneClient
from graphene_django.settings import graphene_settings
from graphene_django.views import instantiate_middleware
from graphql import build_client_schema, get_introspection_query
from graphql_sync_dataloaders import DeferredExecutionContext
from helusers.authz import UserAuthorization

from open_city_profile.schema import schema
from open_city_profile.tests.factories import (
    GroupFactory,
    SuperuserFactory,
    SystemUserFactory,
    UserFactory,
)
from open_city_profile.views import GraphQLView
from services.models import Service
from services.tests.factories import AllowedDataFieldFactory, ServiceFactory

_not_provided = object()


class GraphQLClient(GrapheneClient):
    def execute(
        self,
        *args,
        auth_token_payload=None,
        service=_not_provided,
        context=None,
        allowed_data_fields: list[str] = None,
        **kwargs,
    ):
        """
        Custom execute method which adds all of the middlewares defined in the
        settings to the execution. Additionally adds a profile service to the
        context if no service is provided.

        e.g. GQL DataLoaders middleware is used to make the DataLoaders
        available through the context.
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

        if not hasattr(context, "service"):
            context.service = None

        if service is _not_provided:
            service = Service.objects.filter(is_profile_service=True).first()
            if not service:
                service = ServiceFactory(name="profile", is_profile_service=True)

            context.service = service
        elif service:
            context.service = service
        if allowed_data_fields:
            for field_name in allowed_data_fields:
                context.service.allowed_data_fields.add(
                    AllowedDataFieldFactory(field_name=field_name)
                )

        return super().execute(
            *args,
            context=context,
            middleware=list(instantiate_middleware(graphene_settings.MIDDLEWARE)),
            **kwargs,
        )


@pytest.fixture(autouse=True)
def autouse_db(db):
    pass


@pytest.fixture
def execute_migration_test(request, transactional_db):
    def reset_migrations():
        call_command("migrate", verbosity=0)

    request.addfinalizer(reset_migrations)

    app = request.module.app

    def execute_migration_test(
        migrate_from, migrate_to, before_migration, after_migration
    ):
        migrate_from = [(app, migrate_from)]
        migrate_to = [(app, migrate_to)]

        executor = MigrationExecutor(connection)
        executor.migrate(migrate_from)
        old_apps = executor.loader.project_state(migrate_from).apps

        passable_data = before_migration(old_apps) or ()

        executor.loader.build_graph()
        executor.migrate(migrate_to)
        new_apps = executor.loader.project_state(migrate_to).apps

        after_migration(new_apps, *passable_data)

    return execute_migration_test


@pytest.fixture(autouse=True)
def set_random_seed():
    factory.random.reseed_random(666)


@pytest.fixture(autouse=True)
def email_setup(settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"


@pytest.fixture(autouse=True)
def enable_instrospection_query(settings):
    settings.ENABLE_GRAPHQL_INTROSPECTION = True


@pytest.fixture
def keycloak_setup(settings):
    settings.KEYCLOAK_BASE_URL = "https://localhost/keycloak"
    settings.KEYCLOAK_REALM = "test-keycloak-realm"
    settings.KEYCLOAK_CLIENT_ID = "test-keycloak-client-id"
    settings.KEYCLOAK_CLIENT_SECRET = "test-keycloak-client-secret"


@pytest.fixture
def execution_context_class():
    return DeferredExecutionContext


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
def system_user():
    return SystemUserFactory()


@pytest.fixture
def group():
    return GroupFactory()


def _get_gql_client_with_error_formating():
    return GraphQLClient(schema, format_error=GraphQLView.format_error)


@pytest.fixture
def anon_user_gql_client():
    gql_client = _get_gql_client_with_error_formating()
    gql_client.user = AnonymousUser()
    return gql_client


@pytest.fixture
def user_gql_client():
    gql_client = _get_gql_client_with_error_formating()
    gql_client.user = UserFactory()
    return gql_client


@pytest.fixture
def superuser_gql_client():
    gql_client = _get_gql_client_with_error_formating()
    gql_client.user = SuperuserFactory()
    return gql_client


@pytest.fixture
def gql_schema(anon_user_gql_client, execution_context_class):
    introspection = anon_user_gql_client.execute(
        get_introspection_query(descriptions=False),
        execution_context_class=execution_context_class,
    )
    return build_client_schema(introspection["data"])


def get_unix_timestamp_now():
    return int(datetime.now(tz=timezone.utc).timestamp())


@pytest.fixture
def unix_timestamp_now():
    return get_unix_timestamp_now()


@pytest.fixture(params=[None, ""])
def empty_string_value(request):
    return request.param


@pytest.fixture(autouse=True)
def enable_allowed_data_fields_restriction(settings):
    settings.ENABLE_ALLOWED_DATA_FIELDS_RESTRICTION = True
