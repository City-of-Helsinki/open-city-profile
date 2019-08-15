from django.apps import AppConfig
from django.conf import settings


class ProfilesConfig(AppConfig):
    name = "profiles"

    def __init__(self, *args, **kwargs):
        super(ProfilesConfig, self).__init__(*args, **kwargs)
        import profiles.notifications  # noqa isort:skip

    def ready(self):
        if settings.NOTIFICATIONS_ENABLED:
            import profiles.signals  # noqa isort:skip
