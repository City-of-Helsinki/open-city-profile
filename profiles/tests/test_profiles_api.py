import os
import tempfile

import reversion
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.utils import override_settings
from rest_framework.reverse import reverse
from reversion.models import Version
from thesaurus.models import Concept

from profiles.models import get_user_media_folder, Profile
from profiles.tests.factories import ProfileFactory
from utils.test_utils import (
    create_in_memory_image_file,
    delete,
    get,
    post_create,
    put_update,
)

PROFILE_URL = reverse("profile-list")

temp_dir = tempfile.mkdtemp()


def get_user_profile_url(profile):
    return reverse("profile-detail", kwargs={"user__uuid": profile.user.uuid})


def test_unauthenticated_user_cannot_access(api_client):
    get(api_client, PROFILE_URL, 401)


def test_user_can_see_only_own_profile(user_api_client, profile):
    other_user_profile = ProfileFactory()

    data = get(user_api_client, PROFILE_URL)
    results = data["results"]
    assert len(results) == 1
    assert Profile.objects.count() > 1

    get(user_api_client, get_user_profile_url(other_user_profile), status_code=404)


def test_superuser_can_view_all_profiles(superuser_api_client):
    a_user_profile = ProfileFactory()
    other_user_profile = ProfileFactory()  # noqa

    data = get(superuser_api_client, PROFILE_URL)
    results = data["results"]
    assert len(results) == 2

    get(superuser_api_client, get_user_profile_url(a_user_profile), status_code=200)


def test_post_create_own_profile(user_api_client):
    assert Profile.objects.count() == 0

    post_create(user_api_client, PROFILE_URL)

    assert Profile.objects.count() == 1
    profile = Profile.objects.latest("id")
    assert profile.user == user_api_client.user


def test_cannot_create_multiple_profiles(user_api_client, profile):
    assert Profile.objects.count() == 1

    post_create(user_api_client, PROFILE_URL, status_code=409)

    assert Profile.objects.count() == 1


def test_user_can_delete_own_profile(user_api_client, profile):
    assert Profile.objects.count() == 1

    user_profile_url = get_user_profile_url(profile)
    delete(user_api_client, user_profile_url)

    assert Profile.objects.count() == 0


def test_user_cannot_delete_other_profiles(user_api_client, profile):
    other_user_profile = ProfileFactory()
    assert Profile.objects.count() == 2

    # Response status should be 404 as other profiles are hidden from the user
    delete(user_api_client, get_user_profile_url(other_user_profile), status_code=404)

    assert Profile.objects.count() == 2


def test_put_update_own_profile(user_api_client, profile):
    assert Profile.objects.count() == 1

    user_profile_url = get_user_profile_url(profile)
    phone_number_data = {"phone": "0461234567"}

    put_update(user_api_client, user_profile_url, phone_number_data)

    profile.refresh_from_db()
    assert profile.phone == phone_number_data["phone"]


def test_superuser_can_update_profile(superuser_api_client, profile):
    new_email_data = {"email": "new.email@provider.com"}
    assert profile.email != new_email_data["email"]

    put_update(superuser_api_client, get_user_profile_url(profile), new_email_data)
    profile.refresh_from_db()
    assert profile.email == new_email_data["email"]
    assert profile.user != superuser_api_client.user


def test_put_update_own_first_name_and_last_name(user_api_client, profile):
    assert Profile.objects.count() == 1

    user_profile_url = get_user_profile_url(profile)
    name_data = {"first_name": "New", "last_name": "User"}

    put_update(user_api_client, user_profile_url, name_data)

    profile.refresh_from_db()
    assert profile.first_name == name_data["first_name"]
    assert profile.last_name == name_data["last_name"]


def test_expected_profile_data_fields(user_api_client, profile):
    expected_fields = {
        "first_name",
        "last_name",
        "nickname",
        "image",
        "email",
        "phone",
        "language",
        "contact_method",
        "concepts_of_interest",
        "divisions_of_interest",
        "preferences",
        "legal_relationships",
    }

    user_profile_url = get_user_profile_url(profile)
    profile_endpoint_data = get(user_api_client, user_profile_url)

    assert set(profile_endpoint_data.keys()) == expected_fields


@override_settings(MEDIA_ROOT=temp_dir, MEDIA_URL="")
def test_put_profile_image(user_api_client, profile, default_image):
    assert not profile.image

    user_profile_url = get_user_profile_url(profile)
    image_data = {"image": default_image}

    put_update(user_api_client, user_profile_url, image_data)

    profile.refresh_from_db()
    assert profile.image

    expected_image_path = os.path.join(
        settings.MEDIA_ROOT, get_user_media_folder(profile, default_image.name)
    )
    actual_image_path = os.path.join(settings.MEDIA_ROOT, profile.image.url)
    assert os.path.exists(actual_image_path)
    assert actual_image_path == expected_image_path


@override_settings(MEDIA_ROOT=temp_dir, MEDIA_URL="")
def test_override_previous_profile_image(user_api_client, profile_with_image):
    assert profile_with_image.image

    old_image_path = os.path.join(settings.MEDIA_ROOT, profile_with_image.image.url)
    assert os.path.exists(old_image_path)

    new_image_file = create_in_memory_image_file("new_avatar", "png")
    new_image = SimpleUploadedFile("new_avatar.png", new_image_file.read(), "image/png")
    user_profile_url = get_user_profile_url(profile_with_image)
    new_image_data = {"image": new_image}

    put_update(user_api_client, user_profile_url, new_image_data)

    profile_with_image.refresh_from_db()

    new_image_path = os.path.join(settings.MEDIA_ROOT, profile_with_image.image.url)
    assert os.path.exists(new_image_path)
    assert not os.path.exists(old_image_path)


def test_concept_of_interest_to_representation(user_api_client, profile, concept):
    profile.concepts_of_interest.add(concept)
    user_profile_url = get_user_profile_url(profile)
    profile_endpoint_data = get(user_api_client, user_profile_url)

    serialized_concept_of_interest = "{}:{}".format(
        concept.vocabulary.prefix, concept.code
    )

    assert (
        serialized_concept_of_interest in profile_endpoint_data["concepts_of_interest"]
    )


def test_concept_of_interest_to_internal_value(user_api_client, profile, concept):
    assert not profile.concepts_of_interest.exists()

    serialized_concept_of_interest = "{}:{}".format(
        concept.vocabulary.prefix, concept.code
    )
    concept_of_interest_data = {
        "concepts_of_interest": [serialized_concept_of_interest]
    }

    user_profile_url = get_user_profile_url(profile)
    put_update(user_api_client, user_profile_url, concept_of_interest_data)

    assert profile.concepts_of_interest.exists()
    coi = profile.concepts_of_interest.first()
    assert coi == concept


def test_put_nonexistent_concept_of_interest(user_api_client, profile):
    assert not profile.concepts_of_interest.exists()
    assert not Concept.objects.exists()

    serialized_concept_of_interest = "nonexistent:concept"
    concept_of_interest_data = {
        "concepts_of_interest": [serialized_concept_of_interest]
    }

    user_profile_url = get_user_profile_url(profile)
    put_update(
        user_api_client, user_profile_url, concept_of_interest_data, status_code=400
    )


def test_put_concept_of_interest_in_wrong_format(user_api_client, profile, concept):
    assert not profile.concepts_of_interest.exists()
    assert Concept.objects.exists()

    badly_serialized_concept_of_interest = "{}-{}".format(
        concept.vocabulary.prefix, concept.code
    )
    concept_of_interest_data = {
        "concepts_of_interest": [badly_serialized_concept_of_interest]
    }

    user_profile_url = get_user_profile_url(profile)
    put_update(
        user_api_client, user_profile_url, concept_of_interest_data, status_code=400
    )


def test_update_own_profile_creates_change_log_entry(user_api_client):
    with reversion.create_revision():
        post_create(user_api_client, PROFILE_URL)

    profile = Profile.objects.latest("id")
    versions = Version.objects.get_for_object(profile)
    assert len(versions) == 1

    user_profile_url = get_user_profile_url(profile)
    email_data = {"email": "new.email@provider.com"}
    put_update(user_api_client, user_profile_url, email_data)

    profile.refresh_from_db()
    versions = Version.objects.get_for_object(profile)
    assert len(versions) == 2
    assert versions[0].revision.user == user_api_client.user
    assert versions[0].field_dict["email"] == email_data["email"]


def test_admin_update_profile_creates_change_log_entry(
    user_api_client, superuser_api_client
):
    with reversion.create_revision():
        post_create(user_api_client, PROFILE_URL)

    profile = Profile.objects.latest("id")
    versions = Version.objects.get_for_object(profile)
    assert len(versions) == 1
    assert versions[0].revision.user == user_api_client.user

    user_profile_url = get_user_profile_url(profile)
    email_data = {"email": "new.email@provider.com"}
    put_update(superuser_api_client, user_profile_url, email_data)

    profile.refresh_from_db()
    versions = Version.objects.get_for_object(profile)
    assert len(versions) == 2
    assert versions[0].revision.user == superuser_api_client.user
