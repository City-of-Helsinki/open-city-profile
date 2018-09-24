from django.conf import settings
from django.db import models
from django.contrib.postgres.fields import JSONField
from munigeo.models import AdministrativeDivision
from thesaurus.models import Concept

from users.models import User


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    nickname = models.CharField(max_length=32, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=255, null=True, blank=True)
    language = models.CharField(
        max_length=7, choices=settings.LANGUAGES,
        default=settings.LANGUAGES[0][0]
    )
    contact_method = models.CharField(
        max_length=30, choices=settings.CONTACT_METHODS,
        default=settings.CONTACT_METHODS[0][0]
    )
    concepts_of_interest = models.ManyToManyField(Concept, blank=True)
    divisions_of_interest = models.ManyToManyField(AdministrativeDivision, blank=True)
    preferences = JSONField(null=True, blank=True)


class DivisionOfInterest(models.Model):
    division = models.OneToOneField(
        AdministrativeDivision, on_delete=models.CASCADE, related_name='division_of_interest')
