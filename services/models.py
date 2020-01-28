from adminsortable.models import SortableMixin
from django.db import models
from django.db.models import Max
from enumfields import EnumField
from parler.models import TranslatableModel, TranslatedFields

from profiles.models import Profile

from .enums import ServiceType


def get_next_data_field_order():
    try:
        return AllowedDataField.objects.all().aggregate(Max("order"))["order__max"] + 1
    except TypeError:
        return 1


class AllowedDataField(TranslatableModel, SortableMixin):
    field_name = models.CharField(max_length=30)
    translations = TranslatedFields(label=models.CharField(max_length=64))
    order = models.PositiveIntegerField(
        default=get_next_data_field_order, editable=False, db_index=True
    )

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.safe_translation_getter("label", super().__str__())


class Service(TranslatableModel):
    service_type = EnumField(ServiceType, max_length=32, blank=False, unique=True)
    translations = TranslatedFields(
        title=models.CharField(max_length=64),
        description=models.TextField(max_length=200, blank=True),
    )
    allowed_data_fields = models.ManyToManyField(AllowedDataField)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        permissions = (
            ("can_manage_profiles", "Can manage profiles"),
            ("can_view_profiles", "Can view profiles"),
        )

    def __str__(self):
        return self.safe_translation_getter("title", super().__str__())


class ServiceConnection(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    enabled = models.BooleanField(default=True)

    class Meta:
        unique_together = ("profile", "service")

    def __str__(self):
        return "{} {} - {}".format(
            self.profile.first_name, self.profile.last_name, self.service
        )
