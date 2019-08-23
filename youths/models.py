from datetime import date

import reversion
from django.db import models

from profiles.models import Profile

from .consts import GENDERS, LANGUAGES


def calculate_expiration():
    # Membership always expires at the end of the season (31.7.).
    # Signups before May expire in the summer of the same year, others next year.
    today = date.today()
    return date(year=today.year + 1 if today.month > 4 else today.year, month=7, day=31)


@reversion.register()
class YouthProfile(models.Model):
    # Required info
    profile = models.OneToOneField(
        Profile, related_name="youth_profile", on_delete=models.CASCADE
    )
    ssn = models.CharField(max_length=11)  # TODO ssn validation?
    school_name = models.CharField(max_length=128)
    school_class = models.CharField(max_length=10)
    expiration = models.DateField(default=calculate_expiration)

    # Optional info
    preferred_language = models.CharField(
        max_length=32, choices=LANGUAGES, default=LANGUAGES[0][0]
    )
    volunteer_info = models.TextField(blank=True)
    gender = models.CharField(max_length=32, choices=GENDERS, blank=True)
    diabetes = models.BooleanField(default=False)
    epilepsy = models.BooleanField(default=False)
    heart_disease = models.BooleanField(default=False)
    extra_illnesses_info = models.TextField(blank=True)
    serious_allergies = models.BooleanField(default=False)
    allergies = models.TextField(blank=True)
    notes = models.TextField(
        blank=True
    )  # For documenting e.g. restrictions on gaming or premises

    # Permissions
    approved_by = models.ForeignKey(
        Profile,
        related_name="approved_youth_profiles",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    approved_time = models.DateTimeField(null=True, blank=True, editable=False)
    photo_usage_approved = models.BooleanField(default=False)

    def __str__(self):
        return "{} {} ({})".format(
            self.profile.user.first_name,
            self.profile.user.last_name,
            self.profile.user.uuid,
        )
