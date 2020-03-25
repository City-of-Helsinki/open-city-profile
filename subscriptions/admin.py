from adminsortable.admin import SortableAdmin
from django.contrib import admin
from parler.admin import TranslatableAdmin

from .models import Subscription, SubscriptionType, SubscriptionTypeCategory


@admin.register(SubscriptionType)
class SubscriptionTypeAdmin(TranslatableAdmin):
    pass


@admin.register(SubscriptionTypeCategory)
class SubscriptionTypeCategoryAdmin(TranslatableAdmin, SortableAdmin):
    pass


class SubscriptionInline(admin.StackedInline):
    model = Subscription
    extra = 1
    fk_name = "profile"
