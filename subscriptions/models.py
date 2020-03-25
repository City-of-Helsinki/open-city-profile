from django.db import models
from django.db.models import Max
from parler.models import TranslatableModel, TranslatedFields


def get_next_subscription_type_category_order():
    try:
        return (
            SubscriptionTypeCategory.objects.all().aggregate(Max("order"))["order__max"]
            + 1
        )
    except TypeError:
        return 1


def get_next_subscription_type_order():
    try:
        return SubscriptionType.objects.all().aggregate(Max("order"))["order__max"] + 1
    except TypeError:
        return 1


class SubscriptionTypeCategory(TranslatableModel):
    code = models.CharField(max_length=32)
    translations = TranslatedFields(label=models.CharField(max_length=255))
    created_at = models.DateTimeField(auto_now_add=True)
    order = models.PositiveIntegerField(
        default=get_next_subscription_type_category_order, editable=False, db_index=True
    )

    def __str__(self):
        return self.code


class SubscriptionType(TranslatableModel):
    subscription_type_category = models.ForeignKey(
        SubscriptionTypeCategory,
        on_delete=models.CASCADE,
        related_name="subscription_types",
    )
    code = models.CharField(max_length=32)
    translations = TranslatedFields(label=models.CharField(max_length=255))
    created_at = models.DateTimeField(auto_now_add=True)
    order = models.PositiveIntegerField(
        default=get_next_subscription_type_order, editable=False, db_index=True
    )

    def __str__(self):
        return self.code


class Subscription(models.Model):
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
