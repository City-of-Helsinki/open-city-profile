import os
import subprocess
from sys import stdout

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
    TOKEN_AUTH_ACCEPTED_AUDIENCE=(str, ""),
    TOKEN_AUTH_ACCEPTED_SCOPE_PREFIX=(str, ""),
    TOKEN_AUTH_REQUIRE_SCOPE=(bool, False),
    TOKEN_AUTH_AUTHSERVER_URL=(str, ""),
    MAILER_EMAIL_BACKEND=(str, "django.core.mail.backends.console.EmailBackend"),
    DEFAULT_FROM_EMAIL=(str, "no-reply@hel.fi"),
    MAIL_MAILGUN_KEY=(str, ""),
    MAIL_MAILGUN_DOMAIN=(str, ""),
    MAIL_MAILGUN_API=(str, ""),
    NOTIFICATIONS_ENABLED=(bool, False),
    FIELD_ENCRYPTION_KEYS=(list, []),
    VERSION=(str, None),
    AUDIT_LOGGING_ENABLED=(bool, False),
    AUDIT_LOG_USERNAME=(bool, False),
    GDPR_API_ENABLED=(bool, False),
    ENABLE_GRAPHIQL=(bool, False),
    FORCE_SCRIPT_NAME=(str, ""),
    CSRF_COOKIE_NAME=(str, ""),
    CSRF_COOKIE_PATH=(str, ""),
    CSRF_COOKIE_SECURE=(bool, None),
    SESSION_COOKIE_NAME=(str, ""),
    SESSION_COOKIE_PATH=(str, ""),
    SESSION_COOKIE_SECURE=(bool, None),
    USE_X_FORWARDED_HOST=(bool, None),
    CSRF_TRUSTED_ORIGINS=(list, []),
)
if os.path.exists(env_file):
    env.read_env(env_file)

version = env.str("VERSION")
if version is None:
    try:
        version = subprocess.check_output(["git", "describe", "--always"]).strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        version = None

sentry_sdk.init(
    dsn=env.str("SENTRY_DSN", ""),
    release=version,
    environment=env.str("SENTRY_ENVIRONMENT", "development"),
    integrations=[DjangoIntegration()],
)

sentry_sdk.integrations.logging.ignore_logger("graphql.execution.utils")

BASE_DIR = str(checkout_dir)
DEBUG = env.bool("DEBUG")
TIER = env.str("TIER")
SECRET_KEY = env.str("SECRET_KEY")
if DEBUG and not SECRET_KEY:
    SECRET_KEY = "xxx"

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")

if env("CSRF_COOKIE_NAME"):
    CSRF_COOKIE_NAME = env.str("CSRF_COOKIE_NAME")

if env("CSRF_COOKIE_PATH"):
    CSRF_COOKIE_PATH = env.str("CSRF_COOKIE_PATH")

if env("CSRF_COOKIE_SECURE") is not None:
    CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE")

if env("SESSION_COOKIE_NAME"):
    SESSION_COOKIE_NAME = env.str("SESSION_COOKIE_NAME")

if env("SESSION_COOKIE_PATH"):
    SESSION_COOKIE_PATH = env.str("SESSION_COOKIE_PATH")

if env("SESSION_COOKIE_SECURE") is not None:
    SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE")

if env("USE_X_FORWARDED_HOST") is not None:
    USE_X_FORWARDED_HOST = env.bool("USE_X_FORWARDED_HOST")

if env("CSRF_TRUSTED_ORIGINS"):
    CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS")

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
FIELD_ENCRYPTION_KEYS = env.list("FIELD_ENCRYPTION_KEYS")

ROOT_URLCONF = "open_city_profile.urls"
WSGI_APPLICATION = "open_city_profile.wsgi.application"

if env.str("FORCE_SCRIPT_NAME"):
    FORCE_SCRIPT_NAME = env.str("FORCE_SCRIPT_NAME")

LANGUAGES = (("fi", "Finnish"), ("en", "English"), ("sv", "Swedish"))

LANGUAGE_CODE = "fi"
TIME_ZONE = "Europe/Helsinki"
USE_I18N = True
USE_L10N = True
USE_TZ = True
# Set to True to enable GraphiQL interface, this will overriden to True if DEBUG=True
ENABLE_GRAPHIQL = env("ENABLE_GRAPHIQL")

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
    "django_filters",
    "parler",
    "thesaurus",
    "corsheaders",
    "mptt",
    "munigeo",
    "users",
    "profiles",
    "reversion",
    "youths",
    "django_ilmoitin",
    "mailer",
    "graphene_django",
    "utils",
    "services",
    "guardian",
    "encrypted_fields",
    "adminsortable",
    "subscriptions",
    "import_export",
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
    "reversion.middleware.RevisionMiddleware",
    "profiles.middleware.SetUser",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates"
            )
        ],
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
    "AUDIENCE": env.str("TOKEN_AUTH_ACCEPTED_AUDIENCE"),
    "API_SCOPE_PREFIX": env.str("TOKEN_AUTH_ACCEPTED_SCOPE_PREFIX"),
    "ISSUER": env.str("TOKEN_AUTH_AUTHSERVER_URL"),
    "REQUIRE_API_SCOPE_FOR_AUTHENTICATION": env.bool("TOKEN_AUTH_REQUIRE_SCOPE"),
}

OIDC_AUTH = {"OIDC_LEEWAY": 60 * 60}

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "open_city_profile.oidc.GraphQLApiTokenAuthentication",
    "guardian.backends.ObjectPermissionBackend",
]

# Profiles related settings

CONTACT_METHODS = (("email", "Email"), ("sms", "SMS"))

# Django-parler

PARLER_LANGUAGES = {
    1: ({"code": "fi"}, {"code": "en"}, {"code": "sv"}),
    "default": {"fallbacks": ["fi"], "hide_untranslated": False},
}

# Notification settings

NOTIFICATIONS_ENABLED = True
DEFAULT_FROM_EMAIL = env.str("DEFAULT_FROM_EMAIL")
if env("MAIL_MAILGUN_KEY"):
    ANYMAIL = {
        "MAILGUN_API_KEY": env("MAIL_MAILGUN_KEY"),
        "MAILGUN_SENDER_DOMAIN": env("MAIL_MAILGUN_DOMAIN"),
        "MAILGUN_API_URL": env("MAIL_MAILGUN_API"),
    }
EMAIL_BACKEND = "mailer.backend.DbBackend"
MAILER_EMAIL_BACKEND = env.str("MAILER_EMAIL_BACKEND")

# Graphene

GRAPHENE = {
    "SCHEMA": "open_city_profile.schema.schema",
    "MIDDLEWARE": ["graphql_jwt.middleware.JSONWebTokenMiddleware"],
}

GRAPHQL_JWT = {"JWT_AUTH_HEADER_PREFIX": "Bearer"}

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

# A youth membership number is the youth profile's PK padded with zeroes.
# This value tells what length the number will be padded to.
# For example, PK 123, length 6 --> 000123.
YOUTH_MEMBERSHIP_NUMBER_LENGTH = 6

# Date (day, month) for when the memberships are set to expire
YOUTH_MEMBERSHIP_SEASON_END_DATE = 31, 8

# Month from which on the membership will last until the next year, instead of ending in the current year
YOUTH_MEMBERSHIP_FULL_SEASON_START_MONTH = 5

AUDIT_LOGGING_ENABLED = env.bool("AUDIT_LOGGING_ENABLED")
AUDIT_LOG_USERNAME = env.bool("AUDIT_LOG_USERNAME")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "audit": {"level": "INFO", "class": "logging.StreamHandler", "stream": stdout}
    },
    "loggers": {"audit": {"handlers": ["audit"], "level": "INFO", "propagate": True}},
}

GDPR_API_ENABLED = env.bool("GDPR_API_ENABLED")
