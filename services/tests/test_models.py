import uuid

import pytest
from django.db.utils import IntegrityError

from open_city_profile.tests.factories import UserFactory

from ..models import Service, ServiceConnection
from .factories import ProfileFactory, ServiceConnectionFactory

GDPR_URL = "https://example.com/"
PROFILE_ID = "2aa5a665-77a0-4e62-af24-ec48be5ba9a2"
USER_UUID = "fd800fb5-9974-4df0-a275-07eaf78dcb07"


def test_generate_services_without_service_type(service_factory):
    service_factory(service_type=None)
    service_factory(service_type=None)
    assert Service.objects.count() == 2


@pytest.mark.django_db(transaction=True)
def test_add_service_with_duplicate_name(service_factory):
    service_factory(name="service_name")
    assert Service.objects.count() == 1
    with pytest.raises(IntegrityError):
        service_factory(name="service_name")
    assert Service.objects.count() == 1


@pytest.mark.django_db(transaction=True)
def test_there_can_be_only_one_profile_service(service_factory):
    service_factory(is_profile_service=True)
    with pytest.raises(IntegrityError):
        service_factory(is_profile_service=True)
    assert Service.objects.count() == 1


@pytest.mark.django_db(transaction=True)
def test_connect_duplicate_service_for_profile(service):
    profile = ProfileFactory()
    ServiceConnectionFactory(profile=profile, service=service)
    assert ServiceConnection.objects.count() == 1
    with pytest.raises(IntegrityError):
        ServiceConnectionFactory(profile=profile, service=service)
    assert ServiceConnection.objects.count() == 1


def test_connect_same_service_with_different_profile(service):
    number_of_connections = 2
    for i in range(number_of_connections):
        profile = ProfileFactory()
        ServiceConnectionFactory(profile=profile, service=service)
    assert ServiceConnection.objects.count() == number_of_connections


def test_connect_two_different_services_for_same_profile(service_factory):
    profile = ProfileFactory()
    service_1 = service_factory()
    service_2 = service_factory()
    ServiceConnectionFactory(profile=profile, service=service_1)
    ServiceConnectionFactory(profile=profile, service=service_2)
    assert ServiceConnection.objects.count() == 2


def test_allowed_data_fields_get_correct_orders(allowed_data_field_factory):
    first_data_field = allowed_data_field_factory()
    assert first_data_field.order == 1
    second_data_field = allowed_data_field_factory()
    assert second_data_field.order == 2


@pytest.mark.parametrize(
    "service__gdpr_url, expected",
    [
        # These three are testing that the method works like the old GDPR URL generation
        ["https://example.com/path", "https://example.com/" + PROFILE_ID],
        ["https://example.com/?param=123", "https://example.com/" + PROFILE_ID],
        ["https://example.com/gdpr/", "https://example.com/gdpr/" + PROFILE_ID],
        # The rest test the new functionality with the template string
        [
            "https://example.com/$testvalue/",
            "https://example.com/$testvalue/" + PROFILE_ID,
        ],
        [
            "https://example.com/gdpr/$profile_id",
            "https://example.com/gdpr/" + PROFILE_ID,
        ],
        [
            "https://example.com/$profile_id/gdpr/",
            "https://example.com/" + PROFILE_ID + "/gdpr/",
        ],
        [
            "https://example.com/gdpr/$user_uuid",
            "https://example.com/gdpr/" + USER_UUID,
        ],
        [
            "https://example.com/$user_uuid/gdpr/",
            "https://example.com/" + USER_UUID + "/gdpr/",
        ],
        [
            "https://example.com/gdpr/?profile_id=$profile_id",
            "https://example.com/gdpr/?profile_id=" + PROFILE_ID,
        ],
    ],
)
def test_service_get_gdpr_url_for_profile(service, expected):
    user = UserFactory(uuid=uuid.UUID(USER_UUID))
    profile = ProfileFactory(id=PROFILE_ID, user=user)

    assert service.get_gdpr_url_for_profile(profile) == expected


@pytest.mark.parametrize(
    "service__gdpr_url, expected",
    [
        # These three are testing that the method works like the old GDPR URL generation
        ["https://example.com/path", "https://example.com/" + PROFILE_ID],
        ["https://example.com/?param=123", "https://example.com/" + PROFILE_ID],
        ["https://example.com/gdpr/", "https://example.com/gdpr/" + PROFILE_ID],
        # The rest test the new functionality with the template string
        [
            "https://example.com/$testvalue/",
            "https://example.com/$testvalue/" + PROFILE_ID,
        ],
        [
            "https://example.com/gdpr/$profile_id",
            "https://example.com/gdpr/" + PROFILE_ID,
        ],
        [
            "https://example.com/$profile_id/gdpr/",
            "https://example.com/" + PROFILE_ID + "/gdpr/",
        ],
        ["https://example.com/gdpr/$user_uuid/$profile_id", None],
        ["https://example.com/gdpr/$user_uuid", None],
        ["https://example.com/$user_uuid/gdpr/", None],
        [
            "https://example.com/gdpr/?profile_id=$profile_id",
            "https://example.com/gdpr/?profile_id=" + PROFILE_ID,
        ],
    ],
)
def test_service_get_gdpr_url_for_profile_without_user(service, expected):
    profile = ProfileFactory(id=PROFILE_ID, user=None)

    assert service.get_gdpr_url_for_profile(profile) == expected


@pytest.mark.parametrize("service__gdpr_url", [GDPR_URL])
def test_service_get_gdpr_url_for_profile_no_profile(service):
    assert service.get_gdpr_url_for_profile(None) is None
