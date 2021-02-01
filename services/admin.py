from adminsortable.admin import SortableAdmin
from django.contrib import admin
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
    inlines = [ServiceClientIdInline]


@admin.register(AllowedDataField)
class AllowedDataFieldAdmin(TranslatableAdmin, SortableAdmin):
    pass


class ServiceConnectionInline(admin.StackedInline):
    model = ServiceConnection
    extra = 0
    fk_name = "profile"
