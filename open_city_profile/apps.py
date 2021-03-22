from django.apps import AppConfig
from django.contrib.admin.apps import AdminConfig


class OpenCityProfileConfig(AppConfig):
    name = "open_city_profile"
    verbose_name = "Open City Profile"


class OpenCityProfileAdminConfig(AdminConfig):
    default_site = "open_city_profile.admin_site.AdminSite"
