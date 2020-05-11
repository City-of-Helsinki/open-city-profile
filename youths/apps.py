from django.apps import AppConfig


class YouthsConfig(AppConfig):
    name = "youths"

    def __init__(self, *args, **kwargs):
        super(YouthsConfig, self).__init__(*args, **kwargs)
        import youths.notifications  # noqa isort:skip

    def ready(self):
        import youths.signals  # noqa isort:skip
