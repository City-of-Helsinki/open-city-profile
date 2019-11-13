import pytest
from django.db.utils import IntegrityError

from ..consts import SERVICE_TYPES
from ..models import Service, ServiceConnection
from .factories import ProfileFactory, ServiceConnectionFactory, ServiceFactory


def test_generate_services_from_enum():
    for service_type in SERVICE_TYPES:
        Service.objects.get_or_create(service_type=service_type[0])
    assert Service.objects.count() == len(SERVICE_TYPES)


def test_add_service_with_duplicate_service_type():
    ServiceFactory(service_type=SERVICE_TYPES[0][0])
    assert Service.objects.count() == 1
    with pytest.raises(IntegrityError):
        ServiceFactory(service_type=SERVICE_TYPES[0][0])
    assert Service.objects.count() == 1


def test_connect_duplicate_service_for_profile():
    profile = ProfileFactory()
    service = ServiceFactory()
    ServiceConnectionFactory(profile=profile, service=service)
    assert ServiceConnection.objects.count() == 1
    with pytest.raises(IntegrityError):
        ServiceConnectionFactory(profile=profile, service=service)
    assert ServiceConnection.objects.count() == 1


def test_connect_same_service_with_different_profile():
    service = ServiceFactory()
    profile = ProfileFactory()
    ServiceConnectionFactory(profile=profile, service=service)
    profile = ProfileFactory()
    ServiceConnectionFactory(profile=profile, service=service)
    assert ServiceConnection.objects.count() == 2


def test_connect_two_different_services_for_same_profile():
    profile = ProfileFactory()
    service_1 = ServiceFactory(service_type=SERVICE_TYPES[0][0])
    service_2 = ServiceFactory(service_type=SERVICE_TYPES[1][0])
    ServiceConnectionFactory(profile=profile, service=service_1)
    ServiceConnectionFactory(profile=profile, service=service_2)
    assert ServiceConnection.objects.count() == 2
