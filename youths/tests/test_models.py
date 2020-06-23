import pytest
from django.core.exceptions import ValidationError

from youths.tests.factories import AdditionalContactPersonFactory


def test_serialize_youth_profile(youth_profile):
    AdditionalContactPersonFactory(youth_profile=youth_profile)
    serialized_youth_profile = youth_profile.serialize()

    expected = [
        {"key": "BIRTH_DATE", "value": youth_profile.birth_date.strftime("%Y-%m-%d")},
        {
            "key": "EXPIRATION",
            "value": youth_profile.expiration.strftime("%Y-%m-%d %H:%M"),
        },
        {"key": "APPROVER_FIRST_NAME", "value": youth_profile.approver_first_name},
        {"key": "APPROVER_LAST_NAME", "value": youth_profile.approver_last_name},
        {"key": "APPROVER_PHONE", "value": youth_profile.approver_phone},
        {"key": "APPROVER_EMAIL", "value": youth_profile.approver_email},
        {"key": "PHOTO_USAGE_APPROVED", "value": youth_profile.photo_usage_approved},
        {"key": "SCHOOL_NAME", "value": youth_profile.school_name},
        {"key": "SCHOOL_CLASS", "value": youth_profile.school_class},
        {"key": "LANGUAGE_AT_HOME", "value": youth_profile.language_at_home.value},
    ]

    expected_related = ["ADDITIONAL_CONTACT_PERSONS"]

    assert "key" in serialized_youth_profile
    assert "children" in serialized_youth_profile
    assert serialized_youth_profile["key"] == "YOUTHPROFILE"
    assert len(serialized_youth_profile["children"]) == len(expected) + len(
        expected_related
    )

    for d in expected:
        assert d in serialized_youth_profile["children"]

    # Check that related objects are included
    for key in expected_related:
        assert any(map(lambda x: x["key"] == key, serialized_youth_profile["children"]))


def test_serialize_additional_contact_person():
    acd = AdditionalContactPersonFactory()
    expected = [
        {"key": "FIRST_NAME", "value": acd.first_name},
        {"key": "LAST_NAME", "value": acd.last_name},
        {"key": "PHONE", "value": acd.phone},
        {"key": "EMAIL", "value": acd.email},
    ]

    serialized_acd = acd.serialize()

    assert "key" in serialized_acd
    assert "children" in serialized_acd
    assert serialized_acd["key"] == "ADDITIONALCONTACTPERSON"
    assert len(serialized_acd["children"]) == 4

    for d in expected:
        assert d in serialized_acd["children"]


def test_membership_number_is_generated_for_new_profile(settings, youth_profile):
    expected_number = str(youth_profile.pk).zfill(
        settings.YOUTH_MEMBERSHIP_NUMBER_LENGTH
    )

    # Post save signal sets the membership number
    assert youth_profile.membership_number == expected_number

    # Post save signal saves the membership number into the DB
    youth_profile.refresh_from_db()
    assert youth_profile.membership_number == expected_number


def test_membership_number_is_generated_for_existing_profile(settings, youth_profile):
    """If membership number is empty, it will be generated."""
    expected_number = str(youth_profile.pk).zfill(
        settings.YOUTH_MEMBERSHIP_NUMBER_LENGTH
    )

    youth_profile.membership_number = ""
    youth_profile.save()

    assert youth_profile.membership_number == expected_number


def test_membership_number_is_not_changed_when_saving(youth_profile):
    expected_number = "MEMBER123"

    youth_profile.membership_number = expected_number
    youth_profile.save()

    assert youth_profile.membership_number == expected_number


def test_additional_contact_person_runs_full_clean_when_saving(youth_profile):
    acp = AdditionalContactPersonFactory()
    with pytest.raises(ValidationError):
        acp.email = "notanemail"
        acp.save()
