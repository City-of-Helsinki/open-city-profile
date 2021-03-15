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
        "get_profile_uuid_link",
        "email",
        "get_first_name",
        "get_last_name",
        "is_staff",
    )
    list_select_related = ("profile", "profile__verified_personal_information")
    search_fields = (
        "uuid",
        "first_name",
        "last_name",
        "email",
        "profile__id",
        "profile__first_name",
        "profile__last_name",
        "profile__verified_personal_information__first_name",
        "profile__verified_personal_information__last_name",
    )

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
    get_profile_uuid_link.admin_order_field = "profile__id"

    def get_first_name(self, obj):
        return (
            obj.first_name
            or obj.profile.first_name
            or obj.profile.verified_personal_information.first_name
        )

    get_first_name.short_description = _("First name")

    def get_last_name(self, obj):
        return (
            obj.last_name
            or obj.profile.last_name
            or obj.profile.verified_personal_information.last_name
        )

    get_last_name.short_description = _("Last name")
