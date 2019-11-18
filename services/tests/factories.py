import factory

from profiles.tests.factories import ProfileFactory
from services.models import Service, ServiceConnection


class ServiceFactory(factory.django.DjangoModelFactory):
    service_type = "BERTH"

    class Meta:
        model = Service


class ServiceConnectionFactory(factory.django.DjangoModelFactory):
    profile = factory.SubFactory(ProfileFactory)
    service = factory.SubFactory(ServiceFactory)

    class Meta:
        model = ServiceConnection
