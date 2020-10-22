from django.apps import AppConfig


class YouthsConfig(AppConfig):
    name = "youths"

    def ready(self):
        import youths.signals  # noqa isort:skip
