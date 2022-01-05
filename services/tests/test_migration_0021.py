from functools import partial

import pytest

app = "services"


def create_services(num_implicit_connection_services, apps):
    Service = apps.get_model(app, "Service")

    for i in range(num_implicit_connection_services + 1):
        Service.objects.create(
            name=f"service {i}",
            implicit_connection=i < num_implicit_connection_services,
        )


def test_when_there_is_exactly_one_implicit_connection_service_then_profile_service_is_set(
    execute_migration_test,
):
    def verify_migration(apps):
        Service = apps.get_model(app, "Service")

        assert Service.objects.filter(is_profile_service=True).count() == 1
        assert Service.objects.filter(is_profile_service=True).get().name == "service 0"

    execute_migration_test(
        "0020_change_gdpr_url_help_text",
        "0021_add_is_profile_service_field",
        partial(create_services, 1),
        verify_migration,
    )


@pytest.mark.parametrize("num_implicit_connection_services", [0, 2])
def test_when_there_is_not_exactly_one_implicit_connection_service_then_profile_service_is_not_set(
    num_implicit_connection_services, execute_migration_test
):
    def verify_migration(apps):
        Service = apps.get_model(app, "Service")

        assert not Service.objects.filter(is_profile_service=True).exists()

    execute_migration_test(
        "0020_change_gdpr_url_help_text",
        "0021_add_is_profile_service_field",
        partial(create_services, num_implicit_connection_services),
        verify_migration,
    )
