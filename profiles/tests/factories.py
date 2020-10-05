import factory
from thesaurus.models import Concept, Vocabulary

from open_city_profile.tests.factories import UserFactory
from profiles.enums import AddressType, EmailType, PhoneType
from profiles.models import (
    Address,
    ClaimToken,
    Email,
    Phone,
    Profile,
    SensitiveData,
    TemporaryReadAccessToken,
)


class ProfileFactory(factory.django.DjangoModelFactory):
    user = factory.SubFactory(UserFactory)

    class Meta:
        model = Profile


class ProfileDataDictFactory(factory.DictFactory):
    nickname = factory.Faker("name")


class ClaimTokenFactory(factory.django.DjangoModelFactory):
    profile = factory.SubFactory(ProfileFactory)

    class Meta:
        model = ClaimToken


class TemporaryReadAccessTokenFactory(factory.django.DjangoModelFactory):
    profile = factory.SubFactory(ProfileFactory)

    class Meta:
        model = TemporaryReadAccessToken


class EmailFactory(factory.django.DjangoModelFactory):
    profile = factory.SubFactory(ProfileFactory)
    primary = True
    email_type = EmailType.NONE
    email = factory.Faker("email")

    class Meta:
        model = Email


class EmailDataDictFactory(factory.DictFactory):
    email = factory.Faker("email")
    email_type = EmailType.PERSONAL.name
    primary = True


class ProfileWithPrimaryEmailFactory(ProfileFactory):
    @factory.post_generation
    def emails(self, create, extracted, **kwargs):
        if not create:
            return
        number_of_emails = extracted if extracted else 1
        EmailFactory(profile=self, primary=True)
        for n in range(number_of_emails - 1):
            EmailFactory(profile=self, primary=False)


class PhoneFactory(factory.django.DjangoModelFactory):
    profile = factory.SubFactory(ProfileFactory)
    primary = False
    phone_type = PhoneType.NONE
    phone = factory.Faker("phone_number")

    class Meta:
        model = Phone


class PhoneDataDictFactory(factory.DictFactory):
    phone = factory.Faker("phone_number")
    phone_type = PhoneType.WORK.name
    primary = False


class AddressFactory(factory.django.DjangoModelFactory):
    profile = factory.SubFactory(ProfileFactory)
    primary = False
    address = factory.Faker("street_address")
    postal_code = factory.Faker("postcode")
    city = factory.Faker("city")
    country_code = factory.Faker("country_code")
    address_type = AddressType.NONE

    class Meta:
        model = Address


class AddressDataDictFactory(factory.DictFactory):
    address = factory.Faker("street_address")
    postal_code = factory.Faker("postcode")
    city = factory.Faker("city")
    country_code = factory.Faker("country_code", representation="alpha-2")
    address_type = AddressType.WORK.name
    primary = False


class VocabularyFactory(factory.django.DjangoModelFactory):
    prefix = factory.Faker("word")

    class Meta:
        model = Vocabulary


class ConceptFactory(factory.django.DjangoModelFactory):
    code = factory.Faker("word")
    vocabulary = factory.SubFactory(VocabularyFactory)

    class Meta:
        model = Concept


class SensitiveDataFactory(factory.django.DjangoModelFactory):
    profile = factory.SubFactory(ProfileFactory)
    ssn = factory.Faker("ssn")

    class Meta:
        model = SensitiveData
