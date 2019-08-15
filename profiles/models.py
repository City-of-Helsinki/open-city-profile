import os
import shutil

import reversion
from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.core.files.storage import FileSystemStorage
from django.db import models
from munigeo.models import AdministrativeDivision
from thesaurus.models import Concept

from users.models import User

from .consts import REPRESENTATION_TYPE, REPRESENTATIVE_CONFIRMATION_DEGREE


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
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    nickname = models.CharField(max_length=32, null=True, blank=True)
    image = models.ImageField(
        upload_to=get_user_media_folder,
        storage=OverwriteStorage(),
        null=True,
        blank=True,
    )
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=255, null=True, blank=True)
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

    def __str__(self):
        return "{} {} ({})".format(
            self.user.first_name, self.user.last_name, self.user.uuid
        )


class DivisionOfInterest(models.Model):
    division = models.OneToOneField(
        AdministrativeDivision,
        on_delete=models.CASCADE,
        related_name="division_of_interest",
    )
