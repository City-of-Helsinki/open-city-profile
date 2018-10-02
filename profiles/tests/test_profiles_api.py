import os
import tempfile

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.utils import override_settings
from rest_framework.reverse import reverse

from profiles.models import get_user_media_folder, Profile
from profiles.tests.factories import ProfileFactory
from profiles.tests.utils import create_in_memory_image_file, delete, get, post_create, put_update

PROFILE_URL = reverse('profile-list')

temp_dir = tempfile.mkdtemp()


def get_user_profile_url(profile):
    return reverse('profile-detail', kwargs={'user__uuid': profile.user.uuid})


def test_unauthenticated_user_cannot_access(api_client):
    get(api_client, PROFILE_URL, 401)


def test_user_can_see_only_own_profile(user_api_client, profile):
    other_user_profile = ProfileFactory()

    data = get(user_api_client, PROFILE_URL)
    results = data['results']
    assert len(results) == 1
    assert Profile.objects.count() > 1

    get(user_api_client, get_user_profile_url(other_user_profile), status_code=404)


def test_post_create_profile(user_api_client):
    assert Profile.objects.count() == 0

    post_create(user_api_client, PROFILE_URL)

    assert Profile.objects.count() == 1
    profile = Profile.objects.latest('id')
    assert profile.user == user_api_client.user


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
    phone_number_data = {'phone': '0461234567'}

    put_update(user_api_client, user_profile_url, phone_number_data)

    profile.refresh_from_db()
    assert profile.phone == phone_number_data['phone']


def test_expected_profile_data_fields(user_api_client, profile):
    expected_fields = {
        'nickname',
        'image',
        'email',
        'phone',
        'language',
        'contact_method',
        'concepts_of_interest',
        'divisions_of_interest',
        'preferences'
    }

    user_profile_url = get_user_profile_url(profile)
    profile_endpoint_data = get(user_api_client, user_profile_url)

    assert set(profile_endpoint_data.keys()) == expected_fields


@override_settings(MEDIA_ROOT=temp_dir, MEDIA_URL='')
def test_put_profile_image(user_api_client, profile, default_image):
    assert not profile.image

    user_profile_url = get_user_profile_url(profile)
    image_data = {'image': default_image}

    put_update(user_api_client, user_profile_url, image_data)

    profile.refresh_from_db()
    assert profile.image

    expected_image_path = os.path.join(
        settings.MEDIA_ROOT,
        get_user_media_folder(profile, default_image.name)
    )
    actual_image_path = os.path.join(settings.MEDIA_ROOT, profile.image.url)
    assert os.path.exists(actual_image_path)
    assert actual_image_path == expected_image_path


@override_settings(MEDIA_ROOT=temp_dir, MEDIA_URL='')
def test_override_previous_profile_image(user_api_client, profile_with_image):
    assert profile_with_image.image

    old_image_path = os.path.join(settings.MEDIA_ROOT, profile_with_image.image.url)
    assert os.path.exists(old_image_path)

    new_image_file = create_in_memory_image_file('new_avatar', 'png')
    new_image = SimpleUploadedFile(
        'new_avatar.png',
        new_image_file.read(),
        'image/png',
    )
    user_profile_url = get_user_profile_url(profile_with_image)
    new_image_data = {'image': new_image}

    put_update(user_api_client, user_profile_url, new_image_data)

    profile_with_image.refresh_from_db()

    new_image_path = os.path.join(settings.MEDIA_ROOT, profile_with_image.image.url)
    assert os.path.exists(new_image_path)
    assert not os.path.exists(old_image_path)
