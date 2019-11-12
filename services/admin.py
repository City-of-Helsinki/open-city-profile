from django.contrib import admin
from guardian.admin import GuardedModelAdmin

from .models import Service


@admin.register(Service)
class ServiceAdmin(GuardedModelAdmin):
    pass
