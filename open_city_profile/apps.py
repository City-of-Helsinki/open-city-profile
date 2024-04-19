from django.apps import AppConfig
from django.contrib.admin.apps import AdminConfig
from django.contrib.staticfiles.apps import StaticFilesConfig


class OpenCityProfileConfig(AppConfig):
    name = "open_city_profile"
    verbose_name = "Open City Profile"

    def ready(self) -> None:
        import open_city_profile.checks  # noqa: F401


class OpenCityProfileAdminConfig(AdminConfig):
    default_site = "open_city_profile.admin_site.AdminSite"


class OpenCityProfileStaticFilesConfig(StaticFilesConfig):
    ignore_patterns = ["README.md", "LICENSE"]
