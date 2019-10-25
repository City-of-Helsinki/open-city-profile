from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from youths.models import YouthProfile


class YouthProfileAdminInline(admin.StackedInline):
    model = YouthProfile
    fk_name = "profile"
    extra = 0
    readonly_fields = ("approved_time", "approval_notification_timestamp", "uuid")
    fieldsets = (
        (
            _("Youth profile basic information"),
            {
                "fields": (
                    "uuid",
                    "profile",
                    "school_name",
                    "school_class",
                    "expiration",
                    "preferred_language",
                    "volunteer_info",
                    "gender",
                    "notes",
                )
            },
        ),
        (
            _("Youth profile illnesses"),
            {
                "fields": (
                    "diabetes",
                    "epilepsy",
                    "heart_disease",
                    "serious_allergies",
                    "allergies",
                    "extra_illnesses_info",
                )
            },
        ),
        (
            _("Youth profile permissions"),
            {
                "fields": (
                    "approver_email",
                    "approval_notification_timestamp",
                    "approved_time",
                    "photo_usage_approved",
                )
            },
        ),
    )
