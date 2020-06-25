import factory

from profiles.tests.factories import ProfileFactory
from youths.models import AdditionalContactPerson, YouthProfile


class YouthProfileFactory(factory.django.DjangoModelFactory):
    profile = factory.SubFactory(ProfileFactory)
    school_name = "Kontulan Alakoulu"
    school_class = "1A"
    approver_email = factory.Faker("email")
    birth_date = "2002-02-02"

    class Meta:
        model = YouthProfile


class AdditionalContactPersonDictFactory(factory.DictFactory):
    firstName = factory.Faker("first_name")  # noqa: N815
    lastName = factory.Faker("last_name")  # noqa: N815
    phone = factory.Faker("phone_number")
    email = factory.Faker("email")


class AdditionalContactPersonFactory(factory.django.DjangoModelFactory):
    youth_profile = factory.SubFactory(YouthProfileFactory)
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    phone = factory.Faker("phone_number")
    email = factory.Faker("email")

    class Meta:
        model = AdditionalContactPerson
