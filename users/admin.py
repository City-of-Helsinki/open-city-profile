from copy import deepcopy

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from reversion.admin import VersionAdmin

from profiles.admin import ProfileAdminInline

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
    inlines = [ProfileAdminInline]

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if obj:
            fieldsets = deepcopy(fieldsets)
            fieldsets[1][1]["fields"] += ("uuid",)
            fieldsets[2][1]["fields"] += ("department_name", "ad_groups")
        return fieldsets

    def get_readonly_fields(self, request, obj=None):
        fields = super().get_readonly_fields(request, obj)
        return list(fields) + ["uuid"]
