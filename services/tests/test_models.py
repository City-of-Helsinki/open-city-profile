import pytest
import requests
from django.db.utils import IntegrityError

from ..enums import ServiceType
from ..exceptions import MissingGDPRUrlException
from ..models import Service, ServiceConnection
from .factories import ProfileFactory, ServiceConnectionFactory

GDPR_URL = "https://example.com/"


def test_generate_services_from_enum():
    for service_type in ServiceType:
        Service.objects.create(service_type=service_type)
    assert Service.objects.count() == len(ServiceType)


def test_generate_services_without_service_type(service_factory):
    service_factory(service_type=None)
    service_factory(service_type=None)
    assert Service.objects.count() == 2


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


@pytest.mark.parametrize("service__gdpr_url", [GDPR_URL])
def test_download_gdpr_data_with_valid_service_and_url(
    requests_mock, youth_profile_response, service, profile
):
    service_connection = ServiceConnectionFactory(profile=profile, service=service)
    requests_mock.get(
        f"{GDPR_URL}{profile.pk}",
        json=youth_profile_response,
        request_headers={"authorization": "Bearer token"},
    )

    response = service_connection.download_gdpr_data(api_token="token")
    assert response == youth_profile_response


def test_download_gdpr_data_returns_empty_dict_if_no_url(
    requests_mock, profile, service
):
    service_connection = ServiceConnectionFactory(profile=profile, service=service)
    requests_mock.get(
        f"{GDPR_URL}{profile.pk}",
        json={},
        request_headers={"authorization": "Bearer token"},
    )

    response = service_connection.download_gdpr_data(api_token="token")
    assert response == {}


@pytest.mark.parametrize("service__gdpr_url", [GDPR_URL])
def test_download_gdpr_data_returns_empty_dict_if_request_fails(
    requests_mock, profile, service
):
    service_connection = ServiceConnectionFactory(profile=profile, service=service)
    requests_mock.get(
        f"{GDPR_URL}{profile.pk}",
        json={},
        status_code=404,
        request_headers={"authorization": "Bearer token"},
    )

    response = service_connection.download_gdpr_data(api_token="token")
    assert response == {}


def test_remove_service_gdpr_data_no_url(profile, service):
    service_connection = ServiceConnectionFactory(profile=profile, service=service)

    with pytest.raises(MissingGDPRUrlException):
        service_connection.delete_gdpr_data(api_token="token", dry_run=True)
    with pytest.raises(MissingGDPRUrlException):
        service_connection.delete_gdpr_data(api_token="token")


@pytest.mark.parametrize("service__gdpr_url", [GDPR_URL])
def test_remove_service_gdpr_data_successful(profile, service, requests_mock):
    requests_mock.delete(
        f"{GDPR_URL}{profile.pk}",
        json={},
        status_code=204,
        request_headers={"authorization": "Bearer token"},
    )

    service_connection = ServiceConnectionFactory(profile=profile, service=service)

    dry_run_ok = service_connection.delete_gdpr_data(api_token="token", dry_run=True)
    real_ok = service_connection.delete_gdpr_data(api_token="token")

    assert dry_run_ok
    assert real_ok


@pytest.mark.parametrize("service__gdpr_url", [GDPR_URL])
def test_remove_service_gdpr_data_fail(profile, service, requests_mock):
    requests_mock.delete(
        f"{GDPR_URL}{profile.pk}",
        json={},
        status_code=405,
        request_headers={"authorization": "Bearer token"},
    )

    service_connection = ServiceConnectionFactory(profile=profile, service=service)

    with pytest.raises(requests.RequestException):
        service_connection.delete_gdpr_data(api_token="token", dry_run=True)
    with pytest.raises(requests.RequestException):
        service_connection.delete_gdpr_data(api_token="token")
