import pytest
from django.db.utils import IntegrityError

from ..enums import ServiceType
from ..models import Service, ServiceConnection
from .factories import (
    AllowedDataFieldFactory,
    ProfileFactory,
    ServiceConnectionFactory,
    ServiceFactory,
)


def test_generate_services_from_enum():
    for service_type in ServiceType:
        Service.objects.create(service_type=service_type)
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


def test_allowed_data_fields_get_correct_orders():
    first_data_field = AllowedDataFieldFactory()
    assert first_data_field.order == 1
    second_data_field = AllowedDataFieldFactory()
    assert second_data_field.order == 2


def test_download_gdpr_data_with_valid_service_and_url(
    requests_mock, youth_profile_response
):
    # setup models
    profile = ProfileFactory()
    service = ServiceFactory(gdpr_url="http://valid-gdpr-url.com/profiles/")
    service_connection = ServiceConnectionFactory(profile=profile, service=service)
    # mock request
    requests_mock.get(
        f"http://valid-gdpr-url.com/profiles/{profile.pk}", json=youth_profile_response
    )

    response = service_connection.download_gdpr_data()
    assert response.json() == youth_profile_response


def test_download_gdpr_data_with_invalid_service(requests_mock):
    # setup models
    profile = ProfileFactory()
    service = ServiceFactory()
    service_connection = ServiceConnectionFactory(profile=profile, service=service)
    # mock request
    requests_mock.get(f"http://valid-gdpr-url.com/profiles/{profile.pk}", json={})

    response = service_connection.download_gdpr_data()
    assert response == {}


def test_download_gdpr_data_with_invalid_url(requests_mock):
    # setup models
    profile = ProfileFactory()
    service = ServiceFactory(gdpr_url="http://invalid-gdpr-url.com/profiles/")
    service_connection = ServiceConnectionFactory(profile=profile, service=service)
    # mock request
    requests_mock.get(
        f"http://invalid-gdpr-url.com/profiles/{profile.pk}", json={}, status_code=404
    )

    response = service_connection.download_gdpr_data()
    assert response.status_code == 404
    assert response.json() == {}
