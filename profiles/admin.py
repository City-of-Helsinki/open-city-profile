import json
from functools import reduce

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.forms.models import ModelForm
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import path
from django.utils.decorators import method_decorator

from profiles.models import (
    Address,
    ClaimToken,
    Email,
    Phone,
    Profile,
    SensitiveData,
    TemporaryReadAccessToken,
    VerifiedPersonalInformation,
)
from services.admin import ServiceConnectionInline
from services.models import Service


def superuser_required(function):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_superuser:
            raise PermissionDenied
        return function(request, *args, **kwargs)

    return wrapper


class AlwaysChangedModelForm(ModelForm):
    def has_changed(self):
        """Return always True to enable "empty" objects"""
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
        if count > 1:
            raise forms.ValidationError(
                "Profile must have zero or one primary email(s)"
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


class VerifiedPersonalInformationAdminInline(admin.StackedInline):
    model = VerifiedPersonalInformation
    exclude = ("_national_identification_number_data",)
    readonly_fields = (
        "get_permanent_address",
        "get_temporary_address",
        "get_permanent_foreign_address",
    )
    extra = 0

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Permanent address")
    def get_permanent_address(self, obj):
        return "{}, {} {}\n".format(
            obj.permanent_address.street_address,
            obj.permanent_address.postal_code,
            obj.permanent_address.post_office,
        )

    @admin.display(description="Temporary address")
    def get_temporary_address(self, obj):
        return "{}, {} {}\n".format(
            obj.temporary_address.street_address,
            obj.temporary_address.postal_code,
            obj.temporary_address.post_office,
        )

    @admin.display(description="Permanent foreign address")
    def get_permanent_foreign_address(self, obj):
        return "{}, {}, {}\n".format(
            obj.permanent_foreign_address.street_address,
            obj.permanent_foreign_address.additional_address,
            obj.permanent_foreign_address.country_code,
        )


class ImportProfilesFromJsonForm(forms.Form):
    json_file = forms.FileField(required=True, label="Please select a json file")
    service = forms.ModelChoiceField(
        required=False,
        queryset=Service.objects.all(),
        to_field_name="name",
        label="Connect imported profiles to service",
    )


@admin.register(Profile)
class ExtendedProfileAdmin(admin.ModelAdmin):
    inlines = [
        VerifiedPersonalInformationAdminInline,
        SensitiveDataAdminInline,
        ServiceConnectionInline,
        ClaimTokenInline,
        TemporaryReadAccessTokenInline,
        EmailAdminInline,
        PhoneAdminInline,
        AddressAdminInline,
    ]
    change_list_template = "admin/profiles/profiles_changelist.html"
    list_filter = ("service_connections__service",)
    autocomplete_fields = ("user",)
    search_fields = (
        "id",
        "first_name",
        "last_name",
        "verified_personal_information__first_name",
        "verified_personal_information__last_name",
    )

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [path("upload-json/", self.upload_json, name="upload-json")]
        return my_urls + urls

    @method_decorator(superuser_required, name="dispatch")
    def upload_json(self, request):
        try:
            if request.method == "POST":
                form = ImportProfilesFromJsonForm(request.POST, request.FILES)
                if form.is_valid():
                    data = json.loads(request.FILES["json_file"].read())
                    service = form.cleaned_data["service"]
                    result = Profile.import_customer_data(data, service)
                    response = JsonResponse(result)
                    response["Content-Disposition"] = "attachment; filename=export.json"

                    return response
                else:
                    raise ValidationError(form.errors.as_text())
            else:
                form = ImportProfilesFromJsonForm()
                return render(
                    request, "admin/profiles/upload_json.html", {"form": form}
                )
        except Exception as err:
            messages.error(request, err)
            form = ImportProfilesFromJsonForm()
            return render(request, "admin/profiles/upload_json.html", {"form": form})

    def delete_model(self, request, obj):
        user = obj.user
        super().delete_model(request, obj)
        if user and request.POST.get("delete-user"):
            user.delete()
