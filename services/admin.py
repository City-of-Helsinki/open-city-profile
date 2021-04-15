from adminsortable.admin import SortableAdmin
from django.contrib import admin
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
                    "implicit_connection",
                )
            },
        ),
    )
    inlines = [ServiceClientIdInline]


@admin.register(AllowedDataField)
class AllowedDataFieldAdmin(TranslatableAdmin, SortableAdmin):
    pass


class ServiceConnectionInline(admin.StackedInline):
    model = ServiceConnection
    extra = 0
    fk_name = "profile"
