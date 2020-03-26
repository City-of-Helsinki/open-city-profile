from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from youths.models import YouthProfile


class YouthProfileAdminInline(admin.StackedInline):
    model = YouthProfile
    fk_name = "profile"
    extra = 0
    readonly_fields = ("approved_time", "approval_notification_timestamp")
    fieldsets = (
        (
            _("Youth profile basic information"),
            {
                "fields": (
                    "profile",
                    "school_name",
                    "school_class",
                    "expiration",
                    "language_at_home",
                )
            },
        ),
        (
            _("Youth profile permissions"),
            {
                "fields": (
                    "approver_first_name",
                    "approver_last_name",
                    "approver_phone",
                    "approver_email",
                    "approval_notification_timestamp",
                    "approved_time",
                    "photo_usage_approved",
                )
            },
        ),
    )
