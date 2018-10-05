from django.contrib import admin
from munigeo.models import AdministrativeDivision

from profiles.models import Profile


class ProfileAdmin(admin.StackedInline):
    model = Profile

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "divisions_of_interest":
            kwargs["queryset"] = AdministrativeDivision.objects.filter(division_of_interest__isnull=False)
        formfield = super().formfield_for_manytomany(db_field, request, **kwargs)
        return formfield
