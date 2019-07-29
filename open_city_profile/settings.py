import os
import subprocess

import environ
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

checkout_dir = environ.Path(__file__) - 2
assert os.path.exists(checkout_dir("manage.py"))

parent_dir = checkout_dir.path("..")
if os.path.isdir(parent_dir("etc")):
    env_file = parent_dir("etc/env")
    default_var_root = parent_dir("var")
else:
    env_file = checkout_dir(".env")
    default_var_root = checkout_dir("var")

env = environ.Env(
    DEBUG=(bool, True),
    TIER=(str, "dev"),  # one of: prod, qa, stage, test, dev
    SECRET_KEY=(str, ""),
    VAR_ROOT=(str, default_var_root),
    MEDIA_URL=(str, "/media/"),
    STATIC_URL=(str, "/static/"),
    ALLOWED_HOSTS=(list, []),
    DATABASE_URL=(
        str,
        "postgres://open_city_profile:open_city_profile@localhost/open_city_profile",
    ),
    CACHE_URL=(str, "locmemcache://"),
    EMAIL_URL=(str, "consolemail://"),
    SENTRY_DSN=(str, ""),
    OIDC_CLIENT_ID=(str, ""),
    OIDC_ENDPOINT=(str, ""),
    OIDC_SECRET=(str, ""),
    API_SCOPE_PREFIX=(str, ""),
)
if os.path.exists(env_file):
    env.read_env(env_file)

version = subprocess.check_output(["git", "describe", "--always"]).strip()
sentry_sdk.init(
    dsn=env.str("SENTRY_DSN", ""),
    release=version,
    environment=env.str("SENTRY_ENVIRONMENT", "development"),
    integrations=[DjangoIntegration()],
)

BASE_DIR = str(checkout_dir)
DEBUG = env.bool("DEBUG")
TIER = env.str("TIER")
SECRET_KEY = env.str("SECRET_KEY")
if DEBUG and not SECRET_KEY:
    SECRET_KEY = "xxx"

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")

DATABASES = {"default": env.db()}
# Ensure postgis engine
DATABASES["default"]["ENGINE"] = "django.contrib.gis.db.backends.postgis"

CACHES = {"default": env.cache()}
vars().update(env.email_url())  # EMAIL_BACKEND etc.

var_root = env.path("VAR_ROOT")
MEDIA_ROOT = var_root("media")
STATIC_ROOT = var_root("static")
MEDIA_URL = env.str("MEDIA_URL")
STATIC_URL = env.str("STATIC_URL")

ROOT_URLCONF = "open_city_profile.urls"
WSGI_APPLICATION = "open_city_profile.wsgi.application"

LANGUAGES = (("fi", "Finnish"), ("en", "English"), ("sv", "Swedish"))

LANGUAGE_CODE = "fi"
TIME_ZONE = "Europe/Helsinki"
USE_I18N = True
USE_L10N = True
USE_TZ = True

INSTALLED_APPS = [
    "helusers",
    "helusers.providers.helsinki_oidc",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "rest_framework",
    "django_filters",
    "parler",
    "parler_rest",
    "thesaurus",
    "corsheaders",
    "mptt",
    "munigeo",
    "users",
    "profiles",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

FILE_UPLOAD_MAX_MEMORY_SIZE = 52428800

CORS_ORIGIN_ALLOW_ALL = True

# Authentication

SITE_ID = 1
AUTH_USER_MODEL = "users.User"
SOCIALACCOUNT_PROVIDERS = {"helsinki_oidc": {"VERIFIED_EMAIL": True}}
LOGIN_REDIRECT_URL = "/"
ACCOUNT_LOGOUT_ON_GET = True
SOCIALACCOUNT_ADAPTER = "helusers.adapter.SocialAccountAdapter"
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_EMAIL_REQUIRED = True
SOCIALACCOUNT_AUTO_SIGNUP = True

OIDC_API_TOKEN_AUTH = {
    "AUDIENCE": env.str("OIDC_CLIENT_ID"),
    "API_SCOPE_PREFIX": env.str("API_SCOPE_PREFIX"),
    "REQUIRE_API_SCOPE_FOR_AUTHENTICATION": True,
    "ISSUER": env.str("OIDC_ENDPOINT"),
}

SOCIAL_AUTH_TUNNISTAMO_KEY = env.str("OIDC_CLIENT_ID")
SOCIAL_AUTH_TUNNISTAMO_SECRET = env.str("OIDC_SECRET")
SOCIAL_AUTH_TUNNISTAMO_OIDC_ENDPOINT = env.str("OIDC_ENDPOINT")

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ("helusers.oidc.ApiTokenAuthentication",),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 100,
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ),
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
}

# Profiles related settings

CONTACT_METHODS = (("email", "Email"), ("sms", "SMS"))

# Django-parler

PARLER_LANGUAGES = {
    1: ({"code": "fi"}, {"code": "en"}, {"code": "sv"}),
    "default": {"fallbacks": ["fi"], "hide_untranslated": False},
}

if "SECRET_KEY" not in locals():
    secret_file = os.path.join(BASE_DIR, ".django_secret")
    try:
        with open(secret_file) as f:
            SECRET_KEY = f.read().strip()
    except IOError:
        import random

        system_random = random.SystemRandom()
        try:
            SECRET_KEY = "".join(
                [
                    system_random.choice(
                        "abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)"
                    )
                    for i in range(64)
                ]
            )
            with open(secret_file, "w") as f:
                import os

                os.fchmod(f.fileno(), 0o0600)
                f.write(SECRET_KEY)
                f.close()
        except IOError:
            Exception(
                "Please create a %s file with random characters to generate your secret key!"
                % secret_file
            )
