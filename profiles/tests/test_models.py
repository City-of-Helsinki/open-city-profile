from django.contrib.auth import get_user_model

from ..models import Profile
from .factories import UserFactory

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
        first_name="Notusersfirstname", last_name="Notuserslastname", user=user
    )
    assert profile.first_name != "Notusersfirstname"
    assert profile.last_name != "Notuserslastname"
