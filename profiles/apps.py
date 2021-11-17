from django.apps import AppConfig


class ProfilesConfig(AppConfig):
    name = "profiles"

    def __init__(self, *args, **kwargs):
        super(ProfilesConfig, self).__init__(*args, **kwargs)
        import profiles.notifications  # noqa isort:skip

    def ready(self):
        import profiles.log_signals  # noqa isort:skip
        import profiles.signals  # noqa isort:skip
