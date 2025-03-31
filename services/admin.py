from adminsortable.admin import SortableAdmin
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from guardian.admin import GuardedModelAdmin
from parler.admin import TranslatableAdmin

from .enums import ServiceIdp
from .models import AllowedDataField, Service, ServiceClientId, ServiceConnection


class ServiceClientIdInline(admin.StackedInline):
    model = ServiceClientId
    extra = 0
    verbose_name = "client id"
    verbose_name_plural = "client ids"


class AllowedDataFieldsFilter(admin.SimpleListFilter):
    title = _("allowed data fields")
    parameter_name = "allowed_data_fields"

    def lookups(self, request, model_admin):
        names = (
            AllowedDataField.objects.all()
            .order_by("field_name")
            .values_list("field_name", flat=True)
        )
        return [
            ("empty", _("Empty")),
        ] + [(name, name) for name in names]

    def queryset(self, request, queryset):
        value = self.value()
        if value == "empty":
            return queryset.filter(allowed_data_fields__isnull=True)
        elif value:
            return queryset.filter(allowed_data_fields__field_name=self.value())
        return queryset


class IdpFilter(admin.SimpleListFilter):
    title = _("IDP")
    parameter_name = "idp"

    def lookups(self, request, model_admin):
        return [
            ("empty", _("Empty")),
        ] + [(value, label) for value, label in ServiceIdp.choices()]

    def queryset(self, request, queryset):
        value = self.value()
        if value == "empty":
            return queryset.filter(idp__isnull=True)
        elif value:
            return queryset.filter(idp__contains=[self.value()])
        return queryset


@admin.register(Service)
class ServiceAdmin(TranslatableAdmin, GuardedModelAdmin):
    list_display = (
        "indicate_profile_service",
        "_allowed_data_fields",
        "_client_ids",
        "idp",
        "_gdpr",
    )
    list_filter = (AllowedDataFieldsFilter, IdpFilter)
    search_fields = (
        "name",
        "translations__title",
        "client_ids__client_id",
    )
    ordering = ("name",)

    inlines = [ServiceClientIdInline]

    @admin.display(description=str(Service._meta.verbose_name))
    def indicate_profile_service(self, obj):
        if obj.is_profile_service:
            return format_html(
                '<span title="{}">⚙️ {}</span>', _("Profile service"), obj.name
            )
        return obj.name

    def _allowed_data_fields(self, obj):
        return ", ".join(
            [data_field.field_name for data_field in obj.allowed_data_fields.all()]
        )

    def _client_ids(self, obj):
        return ", ".join([client_id.client_id for client_id in obj.client_ids.all()])

    @admin.display(boolean=True)
    def _gdpr(self, obj):
        return (
            bool(obj.gdpr_url)
            and bool(obj.gdpr_query_scope)
            and bool(obj.gdpr_delete_scope)
            and bool(obj.gdpr_audience)
        )

    def get_fieldsets(self, request, obj=None):
        fieldsets = [
            (
                _("Translatable texts"),
                {
                    "fields": (
                        "title",
                        "description",
                        "privacy_policy_url",
                        "terms_of_use_url",
                    )
                },
            ),
            (_("Common options"), {"fields": ("name", "allowed_data_fields")}),
        ]
        if obj is None or not obj.is_profile_service:
            fieldsets.append(
                (
                    _("GDPR API"),
                    {
                        "fields": (
                            "gdpr_url",
                            "gdpr_query_scope",
                            "gdpr_delete_scope",
                            "idp",
                            "gdpr_audience",
                        )
                    },
                )
            )

        return fieldsets


@admin.register(AllowedDataField)
class AllowedDataFieldAdmin(TranslatableAdmin, SortableAdmin):
    pass


class ServiceConnectionInline(admin.StackedInline):
    model = ServiceConnection
    extra = 0
    fk_name = "profile"
