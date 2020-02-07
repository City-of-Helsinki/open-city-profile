import uuid
from datetime import date

import reversion
from django.conf import settings
from django.db import models
from django.utils import timezone
from django_ilmoitin.utils import send_notification
from enumfields import EnumField

from profiles.models import Profile

from .enums import NotificationType
from .enums import YouthLanguage as LanguageAtHome


def calculate_expiration(from_date=date.today()):
    # Membership always expires at the end of the season (31.7.).
    # Signups before May expire in the summer of the same year, others next year.
    return date(
        year=from_date.year + 1 if from_date.month > 4 else from_date.year,
        month=7,
        day=31,
    )


@reversion.register()
class YouthProfile(models.Model):
    # Required info
    profile = models.OneToOneField(
        Profile, related_name="youth_profile", on_delete=models.CASCADE
    )
    birth_date = models.DateField()
    school_name = models.CharField(max_length=128, blank=True)
    school_class = models.CharField(max_length=10, blank=True)
    expiration = models.DateField(default=calculate_expiration)

    language_at_home = EnumField(
        LanguageAtHome, max_length=32, default=LanguageAtHome.FINNISH
    )

    # Permissions
    approver_first_name = models.CharField(max_length=255, blank=True)
    approver_last_name = models.CharField(max_length=255, blank=True)
    approver_phone = models.CharField(max_length=50, blank=True)
    approver_email = models.EmailField(max_length=254, blank=True)
    approval_token = models.CharField(
        max_length=36, blank=True, default=uuid.uuid4, editable=False
    )
    approval_notification_timestamp = models.DateTimeField(
        null=True, blank=True, editable=False
    )
    approved_time = models.DateTimeField(null=True, blank=True, editable=False)
    photo_usage_approved = models.NullBooleanField()

    @property
    def membership_number(self):
        num = 0 if self.pk is None else self.pk
        return str(num).zfill(settings.YOUTH_MEMBERSHIP_NUMBER_LENGTH)

    def make_approvable(self):
        self.approval_token = uuid.uuid4()
        send_notification(
            email=self.approver_email,
            notification_type=NotificationType.YOUTH_PROFILE_CONFIRMATION_NEEDED.value,
            context={"youth_profile": self},
        )
        self.approval_notification_timestamp = timezone.now()

    def __str__(self):
        return "{} {} ({})".format(
            self.profile.user.first_name,
            self.profile.user.last_name,
            self.profile.user.uuid,
        )
