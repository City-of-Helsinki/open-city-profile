from django.conf import settings
from django.db import models
from django.contrib.postgres.fields import JSONField
from thesaurus.models import Concept

from users.models import User


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=255, null=True, blank=True)
    language = models.CharField(max_length=7, choices=settings.LANGUAGES)
    contact_method = models.CharField(max_length=30, choices=settings.CONTACT_METHODS)
    concepts_of_interest = models.ManyToManyField(Concept, blank=True)
    preferences = JSONField(null=True, blank=True)
