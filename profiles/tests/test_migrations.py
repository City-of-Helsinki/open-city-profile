import pytest

app = "profiles"


def test_fix_primary_email_migration(execute_migration_test):
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
        "0024_order_emails", "0025_fix_primary_emails", create_data, verify_migration,
    )


def test_verified_personal_information_searchable_names_migration(
    execute_migration_test,
):
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


def test_verified_personal_information_searchable_national_identification_number_migration(
    execute_migration_test,
):
    ID_NUMBER = "010199-1234"

    def create_data(apps):
        Profile = apps.get_model(app, "Profile")
        VerifiedPersonalInformation = apps.get_model(app, "VerifiedPersonalInformation")
        profile = Profile.objects.create()
        VerifiedPersonalInformation.objects.create(
            profile=profile, national_identification_number=ID_NUMBER
        )

    def verify_migration(apps):
        VerifiedPersonalInformation = apps.get_model(app, "VerifiedPersonalInformation")
        vpi = VerifiedPersonalInformation.objects.get(
            national_identification_number=ID_NUMBER
        )
        assert vpi.national_identification_number == ID_NUMBER

    execute_migration_test(
        "0036_start_using_raw_verifiedpersonalinformation_names",
        "0038_start_using_searchable_national_identification_number",
        create_data,
        verify_migration,
    )


def test_phone_number_to_not_null_migration(execute_migration_test):
    NUM_PROFILES = 2
    PHONE_NUMBER_LENGTH = 7

    def create_data(apps):
        Profile = apps.get_model(app, "Profile")
        Phone = apps.get_model(app, "Phone")

        for i in range(NUM_PROFILES):
            profile = Profile.objects.create(first_name=str(i))
            Phone.objects.create(profile=profile, phone=str(i) * PHONE_NUMBER_LENGTH)
            Phone.objects.create(profile=profile, phone=None)

    def verify_migration(apps):
        Profile = apps.get_model(app, "Profile")
        Phone = apps.get_model(app, "Phone")

        assert Phone.objects.count() == NUM_PROFILES

        for i in range(NUM_PROFILES):
            profile = Profile.objects.get(first_name=str(i))
            assert profile.phones.count() == 1
            good_phone = Phone.objects.get(profile=profile)
            assert good_phone.phone == str(i) * PHONE_NUMBER_LENGTH

    execute_migration_test(
        "0047_remove_verifiedpersonalinformation_email",
        "0048_change_phone_number_to_not_null",
        create_data,
        verify_migration,
    )
