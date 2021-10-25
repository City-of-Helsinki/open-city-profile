from adminsortable.admin import SortableAdmin
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from guardian.admin import GuardedModelAdmin
from parler.admin import TranslatableAdmin

from .models import AllowedDataField, Service, ServiceClientId, ServiceConnection


class ServiceClientIdInline(admin.StackedInline):
    model = ServiceClientId
    extra = 0
    verbose_name = "client id"
    verbose_name_plural = "client ids"


@admin.register(Service)
class ServiceAdmin(TranslatableAdmin, GuardedModelAdmin):
    list_display = ("indicate_profile_service",)
    fieldsets = (
        (_("Translatable texts"), {"fields": ("title", "description")}),
        (
            _("Common options"),
            {
                "fields": (
                    "name",
                    "allowed_data_fields",
                    "gdpr_url",
                    "gdpr_query_scope",
                    "gdpr_delete_scope",
                )
            },
        ),
    )
    inlines = [ServiceClientIdInline]

    def indicate_profile_service(self, obj):
        result = str(obj)
        if obj.is_profile_service:
            result = format_html(
                '<span title="{}">⚙️ {}</span>', _("Profile service"), result
            )
        return result

    indicate_profile_service.short_description = str(Service._meta.verbose_name)


@admin.register(AllowedDataField)
class AllowedDataFieldAdmin(TranslatableAdmin, SortableAdmin):
    pass


class ServiceConnectionInline(admin.StackedInline):
    model = ServiceConnection
    extra = 0
    fk_name = "profile"
