from django.conf import settings
from django.core.signals import setting_changed
from django.dispatch import receiver

from open_city_profile.utils import enable_graphql_query_suggestion


@receiver(setting_changed)
def reload_graphql_introspection_settings(setting, **kwargs):
    if setting == "ENABLE_GRAPHQL_INTROSPECTION":
        enable_graphql_query_suggestion(settings.ENABLE_GRAPHQL_INTROSPECTION)
