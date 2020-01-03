import factory
from thesaurus.models import Concept, Vocabulary

from open_city_profile.tests.factories import UserFactory
from profiles.enums import AddressType, EmailType, PhoneType
from profiles.models import Address, ClaimToken, Email, Phone, Profile


class ProfileFactory(factory.django.DjangoModelFactory):
    user = factory.SubFactory(UserFactory)

    class Meta:
        model = Profile


class ClaimTokenFactory(factory.django.DjangoModelFactory):
    profile = factory.SubFactory(ProfileFactory)

    class Meta:
        model = ClaimToken


class EmailFactory(factory.django.DjangoModelFactory):
    profile = factory.SubFactory(ProfileFactory)
    primary = False
    email_type = EmailType.NONE
    email = factory.Faker("email")

    class Meta:
        model = Email


class PhoneFactory(factory.django.DjangoModelFactory):
    profile = factory.SubFactory(ProfileFactory)
    primary = False
    phone_type = PhoneType.NONE
    phone = factory.Faker("phone_number")

    class Meta:
        model = Phone


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


class VocabularyFactory(factory.django.DjangoModelFactory):
    prefix = factory.Faker("word")

    class Meta:
        model = Vocabulary


class ConceptFactory(factory.django.DjangoModelFactory):
    code = factory.Faker("word")
    vocabulary = factory.SubFactory(VocabularyFactory)

    class Meta:
        model = Concept
