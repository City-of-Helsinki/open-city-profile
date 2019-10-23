from django.contrib import admin
from munigeo.models import AdministrativeDivision
from reversion.admin import VersionAdmin

from profiles.models import BasicProfile, LegalRelationship
from youths.admin import YouthProfileAdminInline


class RepresentativeAdmin(admin.StackedInline):
    model = LegalRelationship
    extra = 0
    fk_name = "representative"
    verbose_name = "Representative"
    verbose_name_plural = "Representing"


class RepresenteeAdmin(admin.StackedInline):
    model = LegalRelationship
    extra = 0
    fk_name = "representee"
    verbose_name = "Representative"
    verbose_name_plural = "Represented by"


# @admin.register(DataType)
# class DataTypeAdmin(admin.ModelAdmin):
#     model = DataType


@admin.register(BasicProfile)
class ExtendedProfileAdmin(admin.ModelAdmin):
    readonly_fields = ("uuid",)
    inlines = [RepresentativeAdmin, RepresenteeAdmin, YouthProfileAdminInline]

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "divisions_of_interest":
            kwargs["queryset"] = AdministrativeDivision.objects.filter(
                division_of_interest__isnull=False
            )
        formfield = super().formfield_for_manytomany(db_field, request, **kwargs)
        return formfield


class ProfileAdminInline(admin.StackedInline):
    model = BasicProfile

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "divisions_of_interest":
            kwargs["queryset"] = AdministrativeDivision.objects.filter(
                division_of_interest__isnull=False
            )
        formfield = super().formfield_for_manytomany(db_field, request, **kwargs)
        return formfield
