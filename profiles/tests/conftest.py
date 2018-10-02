import factory.random
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from profiles.tests.factories import ProfileFactory, UserFactory
from profiles.tests.utils import create_in_memory_image_file


@pytest.fixture(autouse=True)
def allow_global_access_to_test_db(transactional_db):
    pass


@pytest.fixture(autouse=True)
def set_random_seed():
    factory.random.reseed_random(666)


@pytest.fixture(autouse=True)
def email_setup(settings):
    settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user_api_client(user):
    api_client = APIClient()
    api_client.force_authenticate(user=user)
    api_client.user = user
    return api_client


@pytest.fixture
def user():
    return UserFactory()


@pytest.fixture
def profile(user):
    return ProfileFactory(user=user)


@pytest.fixture
def default_image():
    image_file = create_in_memory_image_file()
    uploaded_image = SimpleUploadedFile(
        'test_image.png',
        image_file.read(),
        'image/png',
    )
    return uploaded_image


@pytest.fixture
def profile_with_image(profile, default_image):
    profile.image = default_image
    profile.save()
    return profile
