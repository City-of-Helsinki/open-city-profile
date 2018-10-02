import factory
from django.contrib.auth import get_user_model
from thesaurus.models import Concept, Vocabulary

from profiles.models import Profile

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    uuid = factory.Faker('uuid4')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    email = factory.Faker('email')

    class Meta:
        model = User


class ProfileFactory(factory.django.DjangoModelFactory):
    user = factory.SubFactory(UserFactory)

    class Meta:
        model = Profile


class VocabularyFactory(factory.django.DjangoModelFactory):
    prefix = factory.Faker('word')

    class Meta:
        model = Vocabulary


class ConceptFactory(factory.django.DjangoModelFactory):
    code = factory.Faker('word')
    vocabulary = factory.SubFactory(VocabularyFactory)

    class Meta:
        model = Concept
