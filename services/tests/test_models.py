import pytest
from django.db.utils import IntegrityError

from ..enums import ServiceType
from ..models import Service, ServiceConnection
from .factories import ProfileFactory, ServiceConnectionFactory, ServiceFactory


def test_generate_services_from_enum():
    for service_type in ServiceType:
        Service.objects.get_or_create(service_type=service_type)
    assert Service.objects.count() == len(ServiceType)


def test_add_service_with_duplicate_service_type():
    ServiceFactory()
    assert Service.objects.count() == 1
    with pytest.raises(IntegrityError):
        ServiceFactory()
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
    service_1 = ServiceFactory(service_type=ServiceType.BERTH)
    service_2 = ServiceFactory(service_type=ServiceType.YOUTH_MEMBERSHIP)
    ServiceConnectionFactory(profile=profile, service=service_1)
    ServiceConnectionFactory(profile=profile, service=service_2)
    assert ServiceConnection.objects.count() == 2
