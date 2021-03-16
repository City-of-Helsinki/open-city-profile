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
    TOKEN_AUTH_ACCEPTED_AUDIENCE=(list, []),
    TOKEN_AUTH_ACCEPTED_SCOPE_PREFIX=(str, ""),
    TOKEN_AUTH_REQUIRE_SCOPE=(bool, False),
    TOKEN_AUTH_AUTHSERVER_URL=(str, ""),
    ADDITIONAL_AUTHSERVER_URLS=(list, []),
    OIDC_CLIENT_ID=(str, ""),
    OIDC_CLIENT_SECRET=(str, ""),
    TUNNISTAMO_API_TOKENS_URL=(str, ""),
    MAILER_EMAIL_BACKEND=(str, "django.core.mail.backends.console.EmailBackend"),
    DEFAULT_FROM_EMAIL=(str, "no-reply@hel.fi"),
    MAIL_MAILGUN_KEY=(str, ""),
    MAIL_MAILGUN_DOMAIN=(str, ""),
    MAIL_MAILGUN_API=(str, ""),
    NOTIFICATIONS_ENABLED=(bool, False),
    FIELD_ENCRYPTION_KEYS=(list, []),
    SALT_NATIONAL_IDENTIFICATION_NUMBER=(str, None),
    VERSION=(str, None),
    AUDIT_LOGGING_ENABLED=(bool, False),
    AUDIT_LOG_FILENAME=(str, ""),
    ENABLE_GRAPHIQL=(bool, False),
    FORCE_SCRIPT_NAME=(str, ""),
    CSRF_COOKIE_NAME=(str, ""),
    CSRF_COOKIE_PATH=(str, ""),
    CSRF_COOKIE_SECURE=(bool, None),
    SESSION_COOKIE_NAME=(str, ""),
    SESSION_COOKIE_PATH=(str, ""),
    SESSION_COOKIE_SECURE=(bool, None),
    USE_X_FORWARDED_FOR=(bool, False),
    USE_X_FORWARDED_HOST=(bool, None),
    CSRF_TRUSTED_ORIGINS=(list, []),
    TEMPORARY_PROFILE_READ_ACCESS_TOKEN_VALIDITY_MINUTES=(int, 2 * 24 * 60),
    GDPR_AUTH_CALLBACK_URL=(str, ""),
    USE_HELUSERS_REQUEST_JWT_AUTH=(bool, False),
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

USE_X_FORWARDED_FOR = env.bool("USE_X_FORWARDED_FOR")

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
SALT_NATIONAL_IDENTIFICATION_NUMBER = env.str("SALT_NATIONAL_IDENTIFICATION_NUMBER")
if not SALT_NATIONAL_IDENTIFICATION_NUMBER and DEBUG:
    SALT_NATIONAL_IDENTIFICATION_NUMBER = "DEBUG_SALT"

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
    "helusers.apps.HelusersConfig",
    "helusers.apps.HelusersAdminConfig",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",
    "django_filters",
    "parler",
    "thesaurus",
    "corsheaders",
    "mptt",
    "munigeo",
    "users",
    "profiles",
    "reversion",
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
    "open_city_profile.apps.OpenCityProfileConfig",
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
    "open_city_profile.middleware.JWTAuthentication",
    "profiles.middleware.SetCurrentRequest",
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

USE_HELUSERS_REQUEST_JWT_AUTH = env.bool("USE_HELUSERS_REQUEST_JWT_AUTH")

OIDC_API_TOKEN_AUTH = {
    "AUDIENCE": env.list("TOKEN_AUTH_ACCEPTED_AUDIENCE"),
    "API_SCOPE_PREFIX": env.str("TOKEN_AUTH_ACCEPTED_SCOPE_PREFIX"),
    "ISSUER": [env.str("TOKEN_AUTH_AUTHSERVER_URL")]
    + env.list("ADDITIONAL_AUTHSERVER_URLS"),
    "REQUIRE_API_SCOPE_FOR_AUTHENTICATION": env.bool("TOKEN_AUTH_REQUIRE_SCOPE"),
}
if not USE_HELUSERS_REQUEST_JWT_AUTH:

    def _list_to_string(value):
        return value[0] if len(value) > 0 else ""

    OIDC_API_TOKEN_AUTH["AUDIENCE"] = _list_to_string(OIDC_API_TOKEN_AUTH["AUDIENCE"])
    OIDC_API_TOKEN_AUTH["ISSUER"] = _list_to_string(OIDC_API_TOKEN_AUTH["ISSUER"])

OIDC_AUTH = {"OIDC_LEEWAY": 60 * 60}

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "guardian.backends.ObjectPermissionBackend",
]
if not USE_HELUSERS_REQUEST_JWT_AUTH:
    AUTHENTICATION_BACKENDS.insert(
        1, "open_city_profile.oidc.GraphQLApiTokenAuthentication"
    )

# Profiles related settings

CONTACT_METHODS = (("email", "Email"), ("sms", "SMS"))

TEMPORARY_PROFILE_READ_ACCESS_TOKEN_VALIDITY_MINUTES = env.int(
    "TEMPORARY_PROFILE_READ_ACCESS_TOKEN_VALIDITY_MINUTES"
)

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
    "MIDDLEWARE": [
        "open_city_profile.graphene.JWTMiddleware"
        if USE_HELUSERS_REQUEST_JWT_AUTH
        else "graphql_jwt.middleware.JSONWebTokenMiddleware",
        "open_city_profile.graphene.GQLDataLoaders",
    ],
}

if not USE_HELUSERS_REQUEST_JWT_AUTH:
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

AUDIT_LOGGING_ENABLED = env.bool("AUDIT_LOGGING_ENABLED")
AUDIT_LOG_FILENAME = env("AUDIT_LOG_FILENAME")

if AUDIT_LOG_FILENAME:
    _audit_log_handler = {
        "level": "INFO",
        "class": "logging.handlers.RotatingFileHandler",
        "filename": AUDIT_LOG_FILENAME,
        "maxBytes": 100_000_000,
        "backupCount": 1,
    }
else:
    _audit_log_handler = {
        "level": "INFO",
        "class": "logging.StreamHandler",
        "stream": stdout,
    }

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"audit": _audit_log_handler},
    "loggers": {"audit": {"handlers": ["audit"], "level": "INFO", "propagate": True}},
}

GDPR_AUTH_CALLBACK_URL = env("GDPR_AUTH_CALLBACK_URL")
TUNNISTAMO_CLIENT_ID = env("OIDC_CLIENT_ID")
TUNNISTAMO_CLIENT_SECRET = env("OIDC_CLIENT_SECRET")
TUNNISTAMO_OIDC_ENDPOINT = env("TOKEN_AUTH_AUTHSERVER_URL")
TUNNISTAMO_API_TOKENS_URL = env("TUNNISTAMO_API_TOKENS_URL")
