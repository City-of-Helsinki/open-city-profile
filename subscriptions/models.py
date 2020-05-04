from adminsortable.models import SortableMixin
from django.db import models
from django.db.models import Max
from parler.models import TranslatableModel, TranslatedFields

from utils.models import SerializableMixin


def get_next_subscription_type_category_order():
    order_max = SubscriptionTypeCategory.objects.aggregate(Max("order"))["order__max"]
    return order_max + 1 if order_max else 1


def get_next_subscription_type_order():
    order_max = SubscriptionType.objects.aggregate(Max("order"))["order__max"]
    return order_max + 1 if order_max else 1


class SubscriptionTypeCategory(TranslatableModel, SortableMixin):
    code = models.CharField(max_length=32, unique=True)
    translations = TranslatedFields(label=models.CharField(max_length=255))
    created_at = models.DateTimeField(auto_now_add=True)
    order = models.PositiveIntegerField(
        default=get_next_subscription_type_category_order, editable=False, db_index=True
    )

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.code


class SubscriptionType(TranslatableModel, SortableMixin):
    subscription_type_category = models.ForeignKey(
        SubscriptionTypeCategory,
        on_delete=models.CASCADE,
        related_name="subscription_types",
    )
    code = models.CharField(max_length=32, unique=True)
    translations = TranslatedFields(label=models.CharField(max_length=255))
    created_at = models.DateTimeField(auto_now_add=True)
    order = models.PositiveIntegerField(
        default=get_next_subscription_type_order, editable=False, db_index=True
    )

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.code


class Subscription(SerializableMixin):
    profile = models.ForeignKey(
        "profiles.Profile", on_delete=models.CASCADE, related_name="subscriptions"
    )
    subscription_type = models.ForeignKey(
        SubscriptionType, on_delete=models.CASCADE, related_name="subscriptions"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    enabled = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.subscription_type.code}: {self.enabled}"

    serialize_fields = (
        {"name": "subscription_type", "accessor": lambda x: getattr(x, "code")},
        {"name": "created_at", "accessor": lambda x: x.strftime("%Y-%m-%d")},
        {"name": "enabled"},
    )
