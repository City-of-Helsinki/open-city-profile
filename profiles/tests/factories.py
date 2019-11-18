import factory
from thesaurus.models import Concept, Vocabulary

from open_city_profile.tests.factories import UserFactory
from profiles.models import Profile


class ProfileFactory(factory.django.DjangoModelFactory):
    user = factory.SubFactory(UserFactory)

    class Meta:
        model = Profile


class VocabularyFactory(factory.django.DjangoModelFactory):
    prefix = factory.Faker("word")

    class Meta:
        model = Vocabulary


class ConceptFactory(factory.django.DjangoModelFactory):
    code = factory.Faker("word")
    vocabulary = factory.SubFactory(VocabularyFactory)

    class Meta:
        model = Concept
