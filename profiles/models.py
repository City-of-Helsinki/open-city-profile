import os
import shutil

import reversion
from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.core.files.storage import FileSystemStorage
from django.db import models
from encrypted_fields import fields
from munigeo.models import AdministrativeDivision
from thesaurus.models import Concept

from users.models import User
from utils.models import UUIDModel

from .consts import (
    ADDRESS_TYPES,
    EMAIL_TYPES,
    PHONE_TYPES,
    REPRESENTATION_TYPE,
    REPRESENTATIVE_CONFIRMATION_DEGREE,
)


def get_user_media_folder(instance, filename):
    return "%s/profile_images/%s" % (instance.user.uuid, filename)


class OverwriteStorage(FileSystemStorage):
    """
    Custom storage that deletes previous profile images
    by deleting the /profiles_images/ folder
    """

    def get_available_name(self, name, max_length=None):
        dir_name, file_name = os.path.split(name)
        if self.exists(dir_name):
            shutil.rmtree(os.path.join(settings.MEDIA_ROOT, dir_name))
        return name


@reversion.register()
class LegalRelationship(models.Model):
    representative = models.ForeignKey(  # "parent"
        "Profile", related_name="representatives", on_delete=models.CASCADE
    )
    representee = models.ForeignKey(  # "child"
        "Profile", related_name="representees", on_delete=models.CASCADE
    )
    type = models.CharField(  # ATM only "custodianship"
        max_length=30, choices=REPRESENTATION_TYPE, default=REPRESENTATION_TYPE[0][0]
    )
    confirmation_degree = models.CharField(
        max_length=30,
        choices=REPRESENTATIVE_CONFIRMATION_DEGREE,
        default=REPRESENTATIVE_CONFIRMATION_DEGREE[0][0],
    )
    expiration = models.DateField(blank=True, null=True)

    def __str__(self):
        return "{} - {}".format(self.representative, self.type)

    def get_notification_context(self):
        return {"relationship": self}


@reversion.register()
class Profile(UUIDModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=255, blank=True)
    last_name = models.CharField(max_length=255, blank=True)
    nickname = models.CharField(max_length=32, null=True, blank=True)
    image = models.ImageField(
        upload_to=get_user_media_folder,
        storage=OverwriteStorage(),
        null=True,
        blank=True,
    )
    language = models.CharField(
        max_length=7, choices=settings.LANGUAGES, default=settings.LANGUAGES[0][0]
    )
    contact_method = models.CharField(
        max_length=30,
        choices=settings.CONTACT_METHODS,
        default=settings.CONTACT_METHODS[0][0],
    )
    concepts_of_interest = models.ManyToManyField(Concept, blank=True)
    divisions_of_interest = models.ManyToManyField(AdministrativeDivision, blank=True)
    preferences = JSONField(null=True, blank=True)

    legal_relationships = models.ManyToManyField(
        "self", through=LegalRelationship, symmetrical=False
    )

    def get_default_email(self):
        return Email.objects.get(profile=self, primary=True)

    def save(self, *args, **kwargs):
        if (
            self._state.adding  # uuid pk forces us to do this, since self.pk is True
            and not (self.first_name and self.last_name)
            and self.user
        ):
            self.first_name = self.user.first_name or self.first_name
            self.last_name = self.user.last_name or self.last_name
        super().save(*args, **kwargs)

    def __str__(self):
        return "{} {} ({})".format(self.first_name, self.last_name, self.user.uuid)


class DivisionOfInterest(models.Model):
    division = models.OneToOneField(
        AdministrativeDivision,
        on_delete=models.CASCADE,
        related_name="division_of_interest",
    )


class SensitiveData(models.Model):
    profile = models.OneToOneField(Profile, on_delete=models.CASCADE)
    ssn = fields.EncryptedCharField(max_length=11)


class Contact(models.Model):
    primary = models.BooleanField(default=False)

    class Meta:
        abstract = True


class Phone(Contact):
    profile = models.ForeignKey(
        Profile, related_name="phones", on_delete=models.CASCADE
    )
    phone = models.CharField(max_length=255, null=True, blank=False)
    phone_type = models.CharField(max_length=32, choices=PHONE_TYPES, blank=False)


class Email(Contact):
    profile = models.ForeignKey(
        Profile, related_name="emails", on_delete=models.CASCADE
    )
    email = models.EmailField(null=True, blank=True)
    email_type = models.CharField(max_length=32, choices=EMAIL_TYPES, blank=False)


class Address(Contact):
    profile = models.ForeignKey(
        Profile, related_name="addresses", on_delete=models.CASCADE
    )
    address = models.CharField(max_length=128, blank=False)
    postal_code = models.CharField(max_length=5, blank=False)
    city = models.CharField(max_length=64, blank=False)
    country_code = models.CharField(max_length=2, blank=True)
    address_type = models.CharField(max_length=32, choices=ADDRESS_TYPES, blank=False)
