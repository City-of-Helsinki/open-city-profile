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


def test_verified_personal_information_searchable_names_migration(migration_test_db):
    FIRST_NAME = "First name"
    LAST_NAME = "Last name"

    def create_data(apps):
        Profile = apps.get_model(app, "Profile")
        VerifiedPersonalInformation = apps.get_model(app, "VerifiedPersonalInformation")
        profile = Profile.objects.create()
        VerifiedPersonalInformation.objects.create(
            profile=profile, first_name=FIRST_NAME, last_name=LAST_NAME
        )

    def verify_migration(apps):
        VerifiedPersonalInformation = apps.get_model(app, "VerifiedPersonalInformation")
        vpi = VerifiedPersonalInformation.objects.get(
            first_name__icontains=FIRST_NAME[:4].lower()
        )
        assert vpi.first_name == FIRST_NAME
        vpi = VerifiedPersonalInformation.objects.get(
            last_name__icontains=LAST_NAME[:4].lower()
        )
        assert vpi.last_name == LAST_NAME

    execute_migration_test(
        "0034_add_help_texts_to_fields__noop",
        "0036_start_using_raw_verifiedpersonalinformation_names",
        create_data,
        verify_migration,
    )
