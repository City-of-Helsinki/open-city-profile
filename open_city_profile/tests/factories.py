import factory
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    uuid = factory.Faker("uuid4", cast_to=None)
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    email = factory.Faker("email")

    class Meta:
        model = User


class SuperuserFactory(UserFactory):
    is_superuser = True

    class Meta:
        model = User


class SystemUserFactory(UserFactory):
    is_system_user = True

    class Meta:
        model = User


class GroupFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Group
