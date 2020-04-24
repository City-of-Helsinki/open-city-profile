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
    """Calculates the expiration date for a youth membership based on the given date.

    Membership always expires at the end of the season. Signups made before the long season start month
    expire in the summer of the same year, others next year.
    """
    full_season_start = settings.YOUTH_MEMBERSHIP_FULL_SEASON_START_MONTH
    expiration_day, expiration_month = settings.YOUTH_MEMBERSHIP_SEASON_END_DATE
    expiration_year = (
        from_date.year + 1 if from_date.month >= full_season_start else from_date.year
    )
    return date(year=expiration_year, month=expiration_month, day=expiration_day)


@reversion.register()
class YouthProfile(models.Model):
    # Required info
    profile = models.OneToOneField(
        Profile, related_name="youth_profile", on_delete=models.CASCADE
    )
    # Post-save signal generates the membership number
    membership_number = models.CharField(max_length=16, blank=True)
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

    def make_approvable(self):
        self.approval_token = uuid.uuid4()
        send_notification(
            email=self.approver_email,
            notification_type=NotificationType.YOUTH_PROFILE_CONFIRMATION_NEEDED.value,
            context={"youth_profile": self},
            language=self.language_at_home.value,
        )
        self.approval_notification_timestamp = timezone.now()

    def __str__(self):
        if self.profile:
            return "{} {} ({})".format(
                self.profile.first_name, self.profile.last_name, self.profile.pk
            )
        else:
            return self.pk

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
