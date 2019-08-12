import factory.random
import pytest
from rest_framework.test import APIClient

from youths.tests.factories import (
    ProfileFactory,
    SuperuserFactory,
    UserFactory,
    YouthProfileFactory,
)


@pytest.fixture(autouse=True)
def allow_global_access_to_test_db(transactional_db):
    pass


@pytest.fixture(autouse=True)
def set_random_seed():
    factory.random.reseed_random(666)


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
def superuser_api_client(superuser):
    api_client = APIClient()
    api_client.force_authenticate(user=superuser)
    api_client.user = superuser
    return api_client


@pytest.fixture
def superuser():
    return SuperuserFactory()


@pytest.fixture
def profile(user):
    return ProfileFactory(user=user)


@pytest.fixture
def youth_profile(profile):
    return YouthProfileFactory(profile=profile)
