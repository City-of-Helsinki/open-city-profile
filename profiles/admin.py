import json
from functools import reduce

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.forms.models import ModelForm
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import path
from django.utils.decorators import method_decorator
from munigeo.models import AdministrativeDivision
from reversion.admin import VersionAdmin

from profiles.models import (
    Address,
    ClaimToken,
    Email,
    LegalRelationship,
    Phone,
    Profile,
    SensitiveData,
    TemporaryReadAccessToken,
)
from services.admin import ServiceConnectionInline
from subscriptions.admin import SubscriptionInline
from youths.admin import YouthProfileAdminInline


def superuser_required(function):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_superuser:
            raise PermissionDenied
        return function(request, *args, **kwargs)

    return wrapper


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


class TemporaryReadAccessTokenInline(admin.StackedInline):
    model = TemporaryReadAccessToken
    extra = 0
    readonly_fields = ("created_at", "validity_duration", "token")
    form = AlwaysChangedModelForm


class SensitiveDataAdminInline(admin.StackedInline):
    model = SensitiveData
    fk_name = "profile"
    extra = 0


class EmailFormSet(forms.models.BaseInlineFormSet):
    def clean(self):
        count = reduce(
            lambda current, form: current + form.cleaned_data.get("primary"),
            self.forms,
            0,
        )
        if count != 1:
            raise forms.ValidationError(
                "Profile must have one exactly one primary email"
            )


class EmailAdminInline(admin.StackedInline):
    model = Email
    formset = EmailFormSet
    extra = 0


class PhoneAdminInline(admin.StackedInline):
    model = Phone
    extra = 0


class AddressAdminInline(admin.StackedInline):
    model = Address
    extra = 0


class ImportProfilesFromJsonForm(forms.Form):
    json_file = forms.FileField(required=True, label="Please select a json file")


@admin.register(Profile)
class ExtendedProfileAdmin(VersionAdmin):
    inlines = [
        SensitiveDataAdminInline,
        RepresenteeAdmin,
        RepresentativeAdmin,
        YouthProfileAdminInline,
        ServiceConnectionInline,
        SubscriptionInline,
        ClaimTokenInline,
        TemporaryReadAccessTokenInline,
        EmailAdminInline,
        PhoneAdminInline,
        AddressAdminInline,
    ]
    change_list_template = "admin/profiles/profiles_changelist.html"
    list_filter = ("service_connections__service",)

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [path("upload-json/", self.upload_json, name="upload-json")]
        return my_urls + urls

    @method_decorator(superuser_required, name="dispatch")
    def upload_json(self, request):
        try:
            if request.method == "POST":
                data = json.loads(request.FILES["json_file"].read())
                result = Profile.import_customer_data(data)
                response = JsonResponse(result)
                response["Content-Disposition"] = "attachment; filename=export.json"
                return response
            else:
                form = ImportProfilesFromJsonForm()
                return render(
                    request, "admin/profiles/upload_json.html", {"form": form}
                )
        except Exception as err:
            messages.error(request, err)
            form = ImportProfilesFromJsonForm()
            return render(request, "admin/profiles/upload_json.html", {"form": form})

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
