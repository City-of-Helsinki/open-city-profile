from adminsortable.admin import SortableAdmin
from django.contrib import admin
from import_export import resources
from import_export.admin import ExportActionMixin
from import_export.fields import Field
from parler.admin import TranslatableAdmin

from profiles.models import Profile

from .models import Subscription, SubscriptionType, SubscriptionTypeCategory


class ProfileResource(resources.ModelResource):
    email = Field()
    phone = Field()

    class Meta:
        model = Profile
        fields = ("email", "phone", "language")

    def dehydrate_email(self, profile):
        return profile.get_primary_email_value()

    def dehydrate_phone(self, profile):
        return profile.get_primary_phone_value()


@admin.register(SubscriptionType)
class SubscriptionTypeAdmin(ExportActionMixin, TranslatableAdmin, SortableAdmin):
    resource_class = ProfileResource

    def get_export_data(self, file_format, queryset, *args, **kwargs):
        profiles = Profile.objects.filter(
            subscriptions__subscription_type__in=queryset
        ).distinct()
        return super().get_export_data(file_format, profiles, *args, **kwargs)


@admin.register(SubscriptionTypeCategory)
class SubscriptionTypeCategoryAdmin(TranslatableAdmin, SortableAdmin):
    pass


class SubscriptionInline(admin.StackedInline):
    model = Subscription
    extra = 1
    fk_name = "profile"
