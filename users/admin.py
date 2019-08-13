from django.contrib import admin
from django.contrib.auth import get_user_model
from reversion.admin import VersionAdmin

from profiles.admin import ProfileAdminInline

User = get_user_model()


@admin.register(User)
class UserAdminInline(VersionAdmin):
    inlines = [ProfileAdminInline]

    def get_readonly_fields(self, request, obj=None):
        fields = super(UserAdminInline, self).get_readonly_fields(request, obj)
        return list(fields) + ["uuid"]
