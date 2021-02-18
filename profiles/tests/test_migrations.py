import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

app = "profiles"


def execute_migration_test(migrate_from, migrate_to, before_migration, after_migration):
    migrate_from = [(app, migrate_from)]
    migrate_to = [(app, migrate_to)]

    executor = MigrationExecutor(connection)
    executor.migrate(migrate_from)
    old_apps = executor.loader.project_state(migrate_from).apps

    passable_data = before_migration(old_apps) or ()

    # Migrate forwards.
    executor.loader.build_graph()  # reload.
    executor.migrate(migrate_to)
    new_apps = executor.loader.project_state(migrate_to).apps

    after_migration(new_apps, *passable_data)


def test_fix_primary_email_migration(migration_test_db):
    def create_data(apps):
        Profile = apps.get_model(app, "Profile")
        Email = apps.get_model(app, "Email")

        profile_with_one_primary_email = Profile.objects.create()
        Email.objects.create(
            profile=profile_with_one_primary_email,
            email="profile_with_one_primary_email@example.com",
            primary=True,
        )

        profile_with_emails_but_no_primary_email = Profile.objects.create()
        Email.objects.create(
            profile=profile_with_emails_but_no_primary_email,
            email="profile_with_emails_but_no_primary_email@example.com",
            primary=False,
        )

        profile_with_no_email = Profile.objects.create()

        profile_with_multiple_primary_emails = Profile.objects.create()
        Email.objects.create(
            profile=profile_with_multiple_primary_emails,
            email="profile_with_multiple_primary_emails_1@example.com",
            primary=True,
        )
        Email.objects.create(
            profile=profile_with_multiple_primary_emails,
            email="profile_with_multiple_primary_emails_2@example.com",
            primary=True,
        )

        return (
            profile_with_one_primary_email,
            profile_with_emails_but_no_primary_email,
            profile_with_no_email,
            profile_with_multiple_primary_emails,
        )

    def verify_migration(
        apps,
        profile_with_one_primary_email,
        profile_with_emails_but_no_primary_email,
        profile_with_no_email,
        profile_with_multiple_primary_emails,
    ):
        Profile = apps.get_model(app, "Profile")

        profile = Profile.objects.get(pk=profile_with_one_primary_email.pk)
        assert profile.emails.filter(primary=True).count() == 1

        profile = Profile.objects.get(pk=profile_with_emails_but_no_primary_email.pk)
        assert profile.emails.filter(primary=True).count() == 1

        with pytest.raises(Profile.DoesNotExist):
            Profile.objects.get(pk=profile_with_no_email.pk)

        profile = Profile.objects.get(pk=profile_with_multiple_primary_emails.pk)
        assert profile.emails.filter(primary=True).count() == 1

    execute_migration_test(
        "0024_order_emails", "0025_fix_primary_emails", create_data, verify_migration
    )
