import factory
from django.contrib.auth import get_user_model

from profiles.models import Profile
from services.models import Service, ServiceConnection

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    uuid = factory.Faker("uuid4")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    email = factory.Faker("email")

    class Meta:
        model = User


class SuperuserFactory(UserFactory):
    is_superuser = True

    class Meta:
        model = User


class ProfileFactory(factory.django.DjangoModelFactory):
    user = factory.SubFactory(UserFactory)
    email = factory.Faker("email")

    class Meta:
        model = Profile


class ServiceFactory(factory.django.DjangoModelFactory):
    service_type = "BERTH"

    class Meta:
        model = Service


class ServiceConnectionFactory(factory.django.DjangoModelFactory):
    profile = factory.SubFactory(ProfileFactory)
    service = factory.SubFactory(ServiceFactory)

    class Meta:
        model = ServiceConnection
