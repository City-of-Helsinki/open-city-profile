from django.contrib import admin
from django.contrib.auth import get_user_model
from reversion.admin import VersionAdmin

from profiles.admin import ProfileAdmin

User = get_user_model()


@admin.register(User)
class ExtendedUserAdmin(VersionAdmin):
    inlines = [ProfileAdmin]

    def get_readonly_fields(self, request, obj=None):
        fields = super(ExtendedUserAdmin, self).get_readonly_fields(request, obj)
        return list(fields) + ["uuid"]
