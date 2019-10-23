import factory
from django.contrib.auth import get_user_model

from profiles.models import BasicProfile
from youths.models import YouthProfile

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


class BasicProfileFactory(factory.django.DjangoModelFactory):
    user = factory.SubFactory(UserFactory)
    email = factory.Faker("email")

    class Meta:
        model = BasicProfile


class YouthProfileFactory(factory.django.DjangoModelFactory):
    profile = factory.SubFactory(BasicProfileFactory)
    school_name = "Kontulan Alakoulu"
    school_class = "1A"
    approver_email = factory.Faker("email")

    class Meta:
        model = YouthProfile
