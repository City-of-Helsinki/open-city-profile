from django.contrib import admin
from guardian.admin import GuardedModelAdmin

from .models import Service, ServiceConnection


@admin.register(Service)
class ServiceAdmin(GuardedModelAdmin):
    pass


class ServiceConnectionInline(admin.StackedInline):
    model = ServiceConnection
    extra = 1
    fk_name = "profile"
