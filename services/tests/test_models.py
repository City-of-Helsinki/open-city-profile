import pytest
from django.db.utils import IntegrityError

from ..consts import SERVICE_TYPES
from ..models import Service
from .factories import ProfileFactory, ServiceFactory


def test_add_duplicate_service_for_profile():
    profile = ProfileFactory()
    ServiceFactory(profile=profile)
    assert Service.objects.count() == 1
    with pytest.raises(IntegrityError):
        ServiceFactory(profile=profile)
    assert Service.objects.count() == 1


def test_add_same_service_with_different_profile():
    profile = ProfileFactory()
    ServiceFactory(profile=profile)
    profile = ProfileFactory()
    ServiceFactory(profile=profile)
    assert Service.objects.count() == 2


def test_add_two_different_services_for_same_profile():
    profile = ProfileFactory()
    ServiceFactory(profile=profile, service_type=SERVICE_TYPES[0][0])
    ServiceFactory(profile=profile, service_type=SERVICE_TYPES[1][0])
    assert Service.objects.count() == 2
