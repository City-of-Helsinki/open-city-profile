app = "services"


def test_when_migrating_back_then_profile_service_gets_implicit_connection_set(
    execute_migration_test,
):
    def create_data(apps):
        Service = apps.get_model(app, "Service")

        Service.objects.create(name="profile-service", is_profile_service=True)
        Service.objects.create(name="other-service", is_profile_service=False)

    def verify_migration(apps):
        Service = apps.get_model(app, "Service")

        profile_service = Service.objects.get(name="profile-service")
        assert profile_service.implicit_connection is True
        other_service = Service.objects.get(name="other-service")
        assert other_service.implicit_connection is False

    execute_migration_test(
        "0022_remove_service_implicit_connection",
        "0021_add_is_profile_service_field",
        create_data,
        verify_migration,
    )
