from youths.tests.factories import YouthProfileFactory


def test_membership_number_is_generated_for_new_profile(settings):
    youth_profile = YouthProfileFactory()
    expected_number = str(youth_profile.pk).zfill(
        settings.YOUTH_MEMBERSHIP_NUMBER_LENGTH
    )

    # Post save signal sets the membership number
    assert youth_profile.membership_number == expected_number

    # Post save signal saves the membership number into the DB
    youth_profile.refresh_from_db()
    assert youth_profile.membership_number == expected_number


def test_membership_number_is_generated_for_existing_profile(settings):
    """If membership number is empty, it will be generated."""
    youth_profile = YouthProfileFactory()
    expected_number = str(youth_profile.pk).zfill(
        settings.YOUTH_MEMBERSHIP_NUMBER_LENGTH
    )

    youth_profile.membership_number = ""
    youth_profile.save()

    assert youth_profile.membership_number == expected_number


def test_membership_number_is_not_changed_when_saving():
    expected_number = "MEMBER123"
    youth_profile = YouthProfileFactory()

    youth_profile.membership_number = expected_number
    youth_profile.save()

    assert youth_profile.membership_number == expected_number
