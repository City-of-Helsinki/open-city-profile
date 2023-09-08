import urllib.parse
from string import Template

from adminsortable.models import SortableMixin
from django import forms
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import Max, Q
from enumfields import EnumField
from parler.models import TranslatableModel, TranslatedFields

from utils.models import SerializableMixin

from .enums import ServiceIdp, ServiceType


def get_next_data_field_order():
    try:
        return AllowedDataField.objects.all().aggregate(Max("order"))["order__max"] + 1
    except TypeError:
        return 1


class AllowedDataField(TranslatableModel, SortableMixin):
    field_name = models.CharField(max_length=30, unique=True)
    translations = TranslatedFields(label=models.CharField(max_length=64))
    order = models.PositiveIntegerField(
        default=get_next_data_field_order, editable=False, db_index=True
    )

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.safe_translation_getter("label", super().__str__())


class ChoiceArrayField(ArrayField):
    """Arrayfield where the widget in model forms (e.g. in the admin) is changed

    The default widget for ArrayField is a simple text input. This modification
    changes the widget to multiple checkboxes.

    from https://stackoverflow.com/a/66059615"""

    def formfield(self, **kwargs):
        kwargs.update(
            {
                "form_class": forms.TypedMultipleChoiceField,
                "choices": self.base_field.choices,
                "coerce": self.base_field.to_python,
                "widget": forms.CheckboxSelectMultiple,
            }
        )
        return super(ArrayField, self).formfield(**kwargs)


class Service(TranslatableModel):
    service_type = EnumField(
        ServiceType, max_length=32, blank=False, null=True, unique=True
    )
    name = models.CharField(max_length=200, blank=False, null=False, unique=True)
    translations = TranslatedFields(
        title=models.CharField(max_length=64),
        description=models.TextField(max_length=500, blank=True),
    )
    allowed_data_fields = models.ManyToManyField(AllowedDataField)
    created_at = models.DateTimeField(auto_now_add=True)
    # The idp field is only temporary as long as we have services that use both
    # Tunnistamo and/or Keycloak. After all the services are moved to Keycloak we
    # can remove the idp field altogether.
    idp = ChoiceArrayField(
        EnumField(ServiceIdp, max_length=32),
        blank=True,
        null=True,
        help_text="Identity providers the service supports. Tunnistamo is implied If none selected.",
    )
    gdpr_url = models.CharField(
        max_length=2000,
        blank=True,
        help_text=(
            'The URL of the Service\'s GDPR endpoint. Tokens "$profile_id" or'
            ' "$user_uuid" will be replaced with the corresponding value.'
            " Otherwise the Profile ID will be automatically appended to the url."
        ),
    )
    gdpr_query_scope = models.CharField(
        max_length=200, blank=True, help_text="GDPR API query operation scope"
    )
    gdpr_delete_scope = models.CharField(
        max_length=200, blank=True, help_text="GDPR API delete operation scope"
    )
    gdpr_audience = models.CharField(
        max_length=200,
        blank=True,
        help_text="Audience of the GDPR API. Must be filled if the API accepts tokens from Keycloak",
    )
    is_profile_service = models.BooleanField(
        default=False,
        help_text="Identifies the profile service itself. Only one Service can have this property.",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["is_profile_service"],
                condition=Q(is_profile_service=True),
                name="unique_is_profile_service",
            )
        ]
        ordering = ["id"]
        permissions = (
            ("can_manage_profiles", "Can manage profiles"),
            ("can_view_profiles", "Can view profiles"),
            ("can_manage_sensitivedata", "Can manage sensitive data"),
            ("can_view_sensitivedata", "Can view sensitive data"),
            (
                "can_view_verified_personal_information",
                "Can view verified personal information",
            ),
        )

    def save(self, *args, **kwargs):
        # Convenience for saving Services with only service_type and no name.
        # When service_type is removed from the code base, this should be
        # removed as well and every Service creation requires a name at that point.
        if not self.name and self.service_type:
            self.name = self.service_type.value

        return super().save(*args, **kwargs)

    def __str__(self):
        return self.safe_translation_getter("title", super().__str__())

    def has_connection_to_profile(self, profile):
        return (
            self.is_profile_service
            or self.serviceconnection_set.filter(profile=profile).exists()
        )

    def get_gdpr_url_for_profile(self, profile):
        if not self.gdpr_url or not profile:
            return None

        url_template = Template(self.gdpr_url)
        mapping = {"profile_id": profile.id}
        if profile.user:
            mapping["user_uuid"] = profile.user.uuid
        else:
            # If the template has a reference to user_uuid and there is no user
            # the GDPR URL cannot be generated.
            for match in url_template.pattern.finditer(url_template.template):
                if (
                    match.group("named") == "user_uuid"
                    or match.group("braced") == "user_uuid"
                ):
                    return None

        gdpr_url = url_template.safe_substitute(mapping)

        if gdpr_url == self.gdpr_url:
            return urllib.parse.urljoin(self.gdpr_url, str(profile.pk))

        return gdpr_url

    @property
    def is_pure_keycloak(self):
        return bool(self.idp and {ServiceIdp.KEYCLOAK} == set(self.idp))


class ServiceClientId(models.Model):
    service = models.ForeignKey(
        Service, on_delete=models.CASCADE, related_name="client_ids"
    )
    client_id = models.CharField(max_length=256, null=False, blank=False, unique=True)


class ServiceConnection(SerializableMixin):
    profile = models.ForeignKey(
        "profiles.Profile", on_delete=models.CASCADE, related_name="service_connections"
    )
    service = models.ForeignKey(Service, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    enabled = models.BooleanField(default=True)

    class Meta:
        unique_together = ("profile", "service")
        ordering = ["id"]

    def __str__(self):
        return "{} {} - {}".format(
            self.profile.first_name, self.profile.last_name, self.service
        )

    serialize_fields = (
        {"name": "service", "accessor": lambda x: getattr(x, "name")},
        {"name": "created_at", "accessor": lambda x: x.strftime("%Y-%m-%d")},
    )

    def get_gdpr_url(self):
        return self.service.get_gdpr_url_for_profile(self.profile)
