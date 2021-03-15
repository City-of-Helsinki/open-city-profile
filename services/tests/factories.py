import factory

from profiles.tests.factories import ProfileFactory
from services.models import (
    AllowedDataField,
    Service,
    ServiceClientId,
    ServiceConnection,
)

from ..enums import ServiceType


class ServiceFactory(factory.django.DjangoModelFactory):
    service_type = ServiceType.BERTH
    name = factory.Sequence(lambda n: "service %d" % n)
    title = "Berth"
    description = "Service for Berth Reservations"
    gdpr_url = ""

    class Meta:
        model = Service


class ServiceClientIdFactory(factory.django.DjangoModelFactory):
    service = factory.SubFactory(ServiceFactory)

    @factory.lazy_attribute
    def client_id(self):
        id_format = f"{self.service.name}_client_id_%%%"
        faker = factory.Faker("numerify", text=id_format)
        return faker.generate()

    class Meta:
        model = ServiceClientId


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
