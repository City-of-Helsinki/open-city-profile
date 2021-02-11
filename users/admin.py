from copy import deepcopy

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from reversion.admin import VersionAdmin

User = get_user_model()


@admin.register(User)
class UserAdmin(VersionAdmin, DjangoUserAdmin):
    list_display = (
        "uuid",
        "email",
        "first_name",
        "last_name",
        "is_staff",
    )
    search_fields = ("uuid", "first_name", "last_name", "email")

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if obj:
            fieldsets = deepcopy(fieldsets)
            fieldsets[1][1]["fields"] += ("uuid", "get_profile_uuid_link")
            fieldsets[2][1]["fields"] += ("department_name", "ad_groups")
        return fieldsets

    def get_readonly_fields(self, request, obj=None):
        fields = super().get_readonly_fields(request, obj)
        return list(fields) + ["uuid", "get_profile_uuid_link"]

    def get_profile_uuid_link(self, obj):
        profile_id = obj.profile.id
        profile_url = reverse("admin:profiles_profile_change", args=(profile_id,))
        hint = _("See Profile")
        return format_html(
            '<a href="{}" title="{}">{}</a>', profile_url, hint, profile_id
        )

    get_profile_uuid_link.short_description = _("Profile")
