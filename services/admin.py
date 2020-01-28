from adminsortable.admin import SortableAdmin
from django.contrib import admin
from guardian.admin import GuardedModelAdmin
from parler.admin import TranslatableAdmin

from .models import AllowedDataField, Service, ServiceConnection


@admin.register(Service)
class ServiceAdmin(TranslatableAdmin, GuardedModelAdmin):
    pass


@admin.register(AllowedDataField)
class AllowedDataFieldAdmin(TranslatableAdmin, SortableAdmin):
    pass


class ServiceConnectionInline(admin.StackedInline):
    model = ServiceConnection
    extra = 1
    fk_name = "profile"
