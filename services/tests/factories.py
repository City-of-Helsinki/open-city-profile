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
    field_name = factory.Sequence(lambda n: "name %d" % n)
    label = factory.Sequence(lambda n: "Label %d" % n)

    class Meta:
        model = AllowedDataField
