import pytest

from open_city_profile.tests.conftest import *  # noqa
from profiles.tests.factories import ConceptFactory, ProfileFactory, VocabularyFactory


@pytest.fixture
def profile(user):
    return ProfileFactory(user=user)


@pytest.fixture
def vocabulary():
    return VocabularyFactory()


@pytest.fixture
def concept(vocabulary):
    return ConceptFactory(vocabulary=vocabulary)
