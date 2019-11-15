import factory

from profiles.tests.factories import ProfileFactory
from youths.models import YouthProfile


class YouthProfileFactory(factory.django.DjangoModelFactory):
    profile = factory.SubFactory(ProfileFactory)
    school_name = "Kontulan Alakoulu"
    school_class = "1A"
    approver_email = factory.Faker("email")

    class Meta:
        model = YouthProfile
