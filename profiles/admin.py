from django.contrib import admin
from django.forms.models import ModelForm
from munigeo.models import AdministrativeDivision
from reversion.admin import VersionAdmin

from profiles.models import ClaimToken, LegalRelationship, Profile, SensitiveData
from services.admin import ServiceConnectionInline
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


class AlwaysChangedModelForm(ModelForm):
    def has_changed(self):
        """ Return always True to enable "empty" objects """
        return True


class ClaimTokenInline(admin.StackedInline):
    model = ClaimToken
    extra = 0
    fk_name = "profile"
    readonly_fields = ("token",)
    form = AlwaysChangedModelForm


class SensitiveDataAdminInline(admin.StackedInline):
    model = SensitiveData
    fk_name = "profile"
    extra = 0


@admin.register(Profile)
class ExtendedProfileAdmin(VersionAdmin):
    inlines = [
        SensitiveDataAdminInline,
        RepresenteeAdmin,
        RepresentativeAdmin,
        YouthProfileAdminInline,
        ServiceConnectionInline,
        ClaimTokenInline,
    ]

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "divisions_of_interest":
            kwargs["queryset"] = AdministrativeDivision.objects.filter(
                division_of_interest__isnull=False
            )
        formfield = super().formfield_for_manytomany(db_field, request, **kwargs)
        return formfield


class ProfileAdminInline(admin.StackedInline):
    model = Profile

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "divisions_of_interest":
            kwargs["queryset"] = AdministrativeDivision.objects.filter(
                division_of_interest__isnull=False
            )
        formfield = super().formfield_for_manytomany(db_field, request, **kwargs)
        return formfield
