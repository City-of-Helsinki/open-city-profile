import pytest
from django.db.utils import IntegrityError

from ..enums import ServiceType
from ..models import Service, ServiceConnection
from .factories import ProfileFactory, ServiceConnectionFactory


def test_generate_services_from_enum():
    for service_type in ServiceType:
        Service.objects.create(service_type=service_type)
    assert Service.objects.count() == len(ServiceType)


@pytest.mark.django_db(transaction=True)
def test_add_service_with_duplicate_service_type(service_factory):
    service_factory()
    assert Service.objects.count() == 1
    with pytest.raises(IntegrityError):
        service_factory()
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
    service_1 = service_factory(service_type=ServiceType.BERTH)
    service_2 = service_factory(service_type=ServiceType.YOUTH_MEMBERSHIP)
    ServiceConnectionFactory(profile=profile, service=service_1)
    ServiceConnectionFactory(profile=profile, service=service_2)
    assert ServiceConnection.objects.count() == 2


def test_allowed_data_fields_get_correct_orders(allowed_data_field_factory):
    first_data_field = allowed_data_field_factory()
    assert first_data_field.order == 1
    second_data_field = allowed_data_field_factory()
    assert second_data_field.order == 2


def test_download_gdpr_data_with_valid_service_and_url(
    requests_mock, youth_profile_response, service_factory, profile
):
    # setup models
    service = service_factory(gdpr_url="http://valid-gdpr-url.com/profiles/")
    service_connection = ServiceConnectionFactory(profile=profile, service=service)
    # mock request
    requests_mock.get(
        f"http://valid-gdpr-url.com/profiles/{profile.pk}", json=youth_profile_response
    )

    response = service_connection.download_gdpr_data()
    assert response.json() == youth_profile_response


def test_download_gdpr_data_with_invalid_service(
    requests_mock, service_factory, profile, service
):
    # setup models
    service_connection = ServiceConnectionFactory(profile=profile, service=service)
    # mock request
    requests_mock.get(f"http://valid-gdpr-url.com/profiles/{profile.pk}", json={})

    response = service_connection.download_gdpr_data()
    assert response == {}


def test_download_gdpr_data_with_invalid_url(requests_mock, profile, service_factory):
    # setup models
    service = service_factory(gdpr_url="http://invalid-gdpr-url.com/profiles/")
    service_connection = ServiceConnectionFactory(profile=profile, service=service)
    # mock request
    requests_mock.get(
        f"http://invalid-gdpr-url.com/profiles/{profile.pk}", json={}, status_code=404
    )

    response = service_connection.download_gdpr_data()
    assert response == {}
