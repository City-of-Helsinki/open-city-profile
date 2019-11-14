import factory
from django.contrib.auth import get_user_model

from profiles.models import Profile
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


class ProfileFactory(factory.django.DjangoModelFactory):
    user = factory.SubFactory(UserFactory)
    nickname = factory.Faker("first_name")

    class Meta:
        model = Profile


class YouthProfileFactory(factory.django.DjangoModelFactory):
    profile = factory.SubFactory(ProfileFactory)
    school_name = "Kontulan Alakoulu"
    school_class = "1A"
    approver_email = factory.Faker("email")
    birth_date = "2002-02-02"

    class Meta:
        model = YouthProfile
