import factory

from profiles.tests.factories import ProfileFactory
from services.models import AllowedDataField, Service, ServiceConnection

from ..enums import ServiceType


class ServiceFactory(factory.django.DjangoModelFactory):
    service_type = ServiceType.BERTH
    title = "Berth"
    description = "Service for Berth Reservations"

    class Meta:
        model = Service


class ServiceConnectionFactory(factory.django.DjangoModelFactory):
    profile = factory.SubFactory(ProfileFactory)
    service = factory.SubFactory(ServiceFactory)

    class Meta:
        model = ServiceConnection


class AllowedDataFieldFactory(factory.django.DjangoModelFactory):
    field_name = "name"
    label = "Name"

    class Meta:
        model = AllowedDataField
