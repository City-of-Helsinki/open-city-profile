import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


def test_fix_primary_email_migration(transactional_db):
    executor = MigrationExecutor(connection)
    app = "profiles"
    migrate_from = [(app, "0024_order_emails")]
    migrate_to = [(app, "0025_fix_primary_emails")]

    executor.migrate(migrate_from)
    old_apps = executor.loader.project_state(migrate_from).apps

    # Create some old data.
    Profile = old_apps.get_model(app, "Profile")
    Email = old_apps.get_model(app, "Email")

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

    # Migrate forwards.
    executor.loader.build_graph()  # reload.
    executor.migrate(migrate_to)
    new_apps = executor.loader.project_state(migrate_to).apps

    # Test the new data.
    Profile = new_apps.get_model(app, "Profile")

    profile = Profile.objects.get(pk=profile_with_one_primary_email.pk)
    assert profile.emails.filter(primary=True).count() == 1

    profile = Profile.objects.get(pk=profile_with_emails_but_no_primary_email.pk)
    assert profile.emails.filter(primary=True).count() == 1

    with pytest.raises(Profile.DoesNotExist):
        Profile.objects.get(pk=profile_with_no_email.pk)

    profile = Profile.objects.get(pk=profile_with_multiple_primary_emails.pk)
    assert profile.emails.filter(primary=True).count() == 1
