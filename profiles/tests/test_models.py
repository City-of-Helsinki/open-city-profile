from django.contrib.auth import get_user_model

from ..models import Profile
from .factories import EmailFactory, ProfileFactory, SensitiveDataFactory, UserFactory

User = get_user_model()


def test_new_profile_with_default_name():
    user = UserFactory()
    profile = Profile.objects.create(user=user)
    assert profile.first_name == user.first_name
    assert profile.last_name == user.last_name


def test_new_profile_without_default_name():
    user = User.objects.create(email="test@user.com", username="user")
    profile = Profile.objects.create(user=user)
    assert profile.first_name == ""
    assert profile.last_name == ""


def test_new_profile_with_existing_name_and_default_name():
    user = UserFactory()
    profile = Profile.objects.create(
        first_name="Existingfirstname", last_name="Existinglastname", user=user
    )
    assert profile.first_name == "Existingfirstname"
    assert profile.last_name == "Existinglastname"


def test_new_profile_with_non_existing_name_and_default_name():
    user = UserFactory()
    profile = Profile.objects.create(first_name="", last_name="", user=user)
    assert profile.first_name
    assert profile.last_name


def test_serialize_profile():
    profile = ProfileFactory()
    email_2 = EmailFactory(profile=profile)
    email_1 = EmailFactory(profile=profile)
    sensitive_data = SensitiveDataFactory(profile=profile)
    serialized_profile = profile.serialize()
    expected_firstname = {"key": "FIRST_NAME", "value": profile.first_name}
    expected_email = {
        "key": "EMAILS",
        "children": [
            {
                "key": "EMAIL",
                "children": [
                    {"key": "PRIMARY", "value": email_1.primary},
                    {"key": "EMAIL_TYPE", "value": email_1.email_type.name},
                    {"key": "EMAIL", "value": email_1.email},
                ],
            },
            {
                "key": "EMAIL",
                "children": [
                    {"key": "PRIMARY", "value": email_2.primary},
                    {"key": "EMAIL_TYPE", "value": email_2.email_type.name},
                    {"key": "EMAIL", "value": email_2.email},
                ],
            },
        ],
    }
    expected_sensitive_data = {
        "key": "SENSITIVEDATA",
        "children": [{"key": "SSN", "value": sensitive_data.ssn}],
    }
    assert "key" in serialized_profile
    assert "children" in serialized_profile
    assert serialized_profile.get("key") == "PROFILE"
    assert expected_firstname in serialized_profile.get("children")
    assert expected_email in serialized_profile.get("children")
    assert expected_sensitive_data in serialized_profile.get("children")
