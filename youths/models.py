import uuid
from datetime import date

import reversion
from django.db import models

from profiles.models import Profile

from .consts import LANGUAGES


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
    birth_date = models.DateField()
    school_name = models.CharField(max_length=128)
    school_class = models.CharField(max_length=10)
    expiration = models.DateField(default=calculate_expiration)

    language_at_home = models.CharField(
        max_length=32, choices=LANGUAGES, default=LANGUAGES[0][0]
    )

    # Permissions
    approver_first_name = models.CharField(max_length=255, blank=True)
    approver_last_name = models.CharField(max_length=255, blank=True)
    approver_phone = models.CharField(max_length=50, blank=True)
    approver_email = models.EmailField()
    approval_token = models.CharField(
        max_length=36, blank=True, default=uuid.uuid4, editable=False
    )
    approval_notification_timestamp = models.DateTimeField(
        null=True, blank=True, editable=False
    )
    approved_time = models.DateTimeField(null=True, blank=True, editable=False)
    photo_usage_approved = models.BooleanField(default=False)

    def __str__(self):
        return "{} {} ({})".format(
            self.profile.user.first_name,
            self.profile.user.last_name,
            self.profile.user.uuid,
        )
