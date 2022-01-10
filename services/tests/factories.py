import factory

from profiles.tests.factories import ProfileFactory
from services.models import (
    AllowedDataField,
    Service,
    ServiceClientId,
    ServiceConnection,
)


class ServiceFactory(factory.django.DjangoModelFactory):
    service_type = None
    name = factory.Sequence(lambda n: "service %d" % n)

    @factory.lazy_attribute
    def title(self):
        return f"{self.name} title"

    @factory.lazy_attribute
    def description(self):
        return f"{self.name} description"

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

    @factory.post_generation
    def final_order(self, create, extracted, **kwargs):
        if extracted is not None:
            self.order = extracted

    class Meta:
        model = AllowedDataField
