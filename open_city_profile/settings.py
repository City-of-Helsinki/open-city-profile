import os
from datetime import datetime

import environ
import sentry_sdk
from corsheaders.defaults import default_headers
from helusers.defaults import SOCIAL_AUTH_PIPELINE as HELUSERS_SOCIAL_AUTH_PIPELINE
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.types import SamplingContext

from open_city_profile import __version__
from open_city_profile.utils import enable_graphql_query_suggestion

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
    DATABASE_PASSWORD=(str, ""),
    CACHE_URL=(str, "locmemcache://"),
    EMAIL_URL=(str, "consolemail://"),
    SENTRY_DSN=(str, ""),
    SENTRY_ENVIRONMENT=(str, "local"),
    SENTRY_PROFILE_SESSION_SAMPLE_RATE=(float, None),
    SENTRY_RELEASE=(str, None),
    SENTRY_TRACES_SAMPLE_RATE=(float, None),
    TOKEN_AUTH_ACCEPTED_AUDIENCE=(list, []),
    TOKEN_AUTH_ACCEPTED_SCOPE_PREFIX=(str, ""),
    TOKEN_AUTH_REQUIRE_SCOPE=(bool, False),
    TOKEN_AUTH_AUTHSERVER_URL=(str, ""),
    ADDITIONAL_AUTHSERVER_URLS=(list, []),
    DEFAULT_FROM_EMAIL=(str, "no-reply@hel.fi"),
    FIELD_ENCRYPTION_KEYS=(list, []),
    SALT_NATIONAL_IDENTIFICATION_NUMBER=(str, None),
    OPENSHIFT_BUILD_COMMIT=(str, ""),
    AUDIT_LOG_TO_DB_ENABLED=(bool, False),
    OPEN_CITY_PROFILE_LOG_LEVEL=(str, None),
    ENABLE_ALLOWED_DATA_FIELDS_RESTRICTION=(bool, False),
    ENABLE_GRAPHIQL=(bool, False),
    ENABLE_GRAPHQL_INTROSPECTION=(bool, False),
    GRAPHQL_QUERY_DEPTH_LIMIT=(int, 12),
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
    KEYCLOAK_BASE_URL=(str, ""),
    KEYCLOAK_REALM=(str, ""),
    KEYCLOAK_CLIENT_ID=(str, ""),
    KEYCLOAK_CLIENT_SECRET=(str, ""),
    KEYCLOAK_GDPR_CLIENT_ID=(str, ""),
    KEYCLOAK_GDPR_CLIENT_SECRET=(str, ""),
    VERIFIED_PERSONAL_INFORMATION_ACCESS_AMR_LIST=(list, []),
    CSP_CONNECT_SRC=(str, None),
    CSP_IMG_SRC=(str, None),
    CSP_STYLE_SRC=(str, None),
    CSP_SCRIPT_SRC=(str, None),
    CSP_REPORT_ONLY=(bool, False),
    CSP_REPORT_URI=(str, None),
    HELUSERS_PASSWORD_LOGIN_DISABLED=(bool, False),
    LOGIN_REDIRECT_URL=(str, "/admin/"),
    LOGOUT_REDIRECT_URL=(str, "/admin/"),
    SOCIAL_AUTH_TUNNISTAMO_KEY=(str, None),
    SOCIAL_AUTH_TUNNISTAMO_SECRET=(str, None),
    SOCIAL_AUTH_TUNNISTAMO_OIDC_ENDPOINT=(str, None),
)
if os.path.exists(env_file):
    env.read_env(env_file)

COMMIT_HASH = env.str("OPENSHIFT_BUILD_COMMIT", "")
VERSION = __version__

SENTRY_TRACES_SAMPLE_RATE = env("SENTRY_TRACES_SAMPLE_RATE")


def sentry_traces_sampler(sampling_context: SamplingContext) -> float:
    # Respect parent sampling decision if one exists. Recommended by Sentry.
    if (parent_sampled := sampling_context.get("parent_sampled")) is not None:
        return float(parent_sampled)

    # Exclude health check endpoints from tracing
    path = sampling_context.get("wsgi_environ", {}).get("PATH_INFO", "")
    if path.rstrip("/") in ["/healthz", "/readiness"]:
        return 0

    # Use configured sample rate for all other requests
    return SENTRY_TRACES_SAMPLE_RATE or 0


if env("SENTRY_DSN"):
    sentry_sdk.init(
        dsn=env("SENTRY_DSN"),
        environment=env("SENTRY_ENVIRONMENT"),
        release=env("SENTRY_RELEASE"),
        integrations=[DjangoIntegration()],
        traces_sampler=sentry_traces_sampler,
        profile_session_sample_rate=env("SENTRY_PROFILE_SESSION_SAMPLE_RATE"),
        profile_lifecycle="trace",
    )


sentry_sdk.integrations.logging.ignore_logger("graphql.execution.utils")

BASE_DIR = str(checkout_dir)

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"
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

if env("DATABASE_PASSWORD"):
    DATABASES["default"]["PASSWORD"] = env("DATABASE_PASSWORD")

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
USE_TZ = True

DEFAULT_FROM_EMAIL = env.str("DEFAULT_FROM_EMAIL")

# Set to True to enable GraphiQL interface, enabled automatically if DEBUG=True
ENABLE_GRAPHIQL = env("ENABLE_GRAPHIQL") or env("DEBUG")
# Enable GraphQL introspection queries, enabled automatically if DEBUG=True
ENABLE_GRAPHQL_INTROSPECTION = env("ENABLE_GRAPHQL_INTROSPECTION") or env("DEBUG")

if not ENABLE_GRAPHQL_INTROSPECTION:
    enable_graphql_query_suggestion(False)

GRAPHQL_QUERY_DEPTH_LIMIT = env("GRAPHQL_QUERY_DEPTH_LIMIT")

ENABLE_ALLOWED_DATA_FIELDS_RESTRICTION = env("ENABLE_ALLOWED_DATA_FIELDS_RESTRICTION")

INSTALLED_APPS = [
    "helusers.apps.HelusersConfig",
    "social_django",
    "open_city_profile.apps.OpenCityProfileAdminConfig",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "open_city_profile.apps.OpenCityProfileStaticFilesConfig",
    "django_filters",
    "parler",
    "corsheaders",
    "audit_log",
    "users",
    "profiles",
    "graphene_django",
    "utils",
    "services",
    "guardian",
    "encrypted_fields",
    "adminsortable",
    "open_city_profile.apps.OpenCityProfileConfig",
    "sanitized_dump",
    "logger_extra",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "logger_extra.middleware.XRequestIdMiddleware",
    "csp.middleware.CSPMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "open_city_profile.middleware.JWTAuthentication",
    "profiles.audit_log.AuditLogMiddleware",
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

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_HEADERS = (
    *default_headers,
    "baggage",
    "sentry-trace",
)

# Authentication

SITE_ID = 1
AUTH_USER_MODEL = "users.User"

OIDC_API_TOKEN_AUTH = {
    "AUDIENCE": env.list("TOKEN_AUTH_ACCEPTED_AUDIENCE"),
    "API_SCOPE_PREFIX": env.str("TOKEN_AUTH_ACCEPTED_SCOPE_PREFIX"),
    "ISSUER": [env.str("TOKEN_AUTH_AUTHSERVER_URL")]
    + env.list("ADDITIONAL_AUTHSERVER_URLS"),
    "REQUIRE_API_SCOPE_FOR_AUTHENTICATION": env.bool("TOKEN_AUTH_REQUIRE_SCOPE"),
}

AUTHENTICATION_BACKENDS = [
    "helusers.tunnistamo_oidc.TunnistamoOIDCAuth",
    "django.contrib.auth.backends.ModelBackend",
    "guardian.backends.ObjectPermissionBackend",
]

ANONYMOUS_USER_NAME = None

HELUSERS_BACK_CHANNEL_LOGOUT_ENABLED = True
HELUSERS_PASSWORD_LOGIN_DISABLED = env("HELUSERS_PASSWORD_LOGIN_DISABLED")
LOGIN_REDIRECT_URL = env("LOGIN_REDIRECT_URL")
LOGOUT_REDIRECT_URL = env("LOGOUT_REDIRECT_URL")
SESSION_SERIALIZER = "helusers.sessions.TunnistamoOIDCSerializer"
SOCIAL_AUTH_PIPELINE = HELUSERS_SOCIAL_AUTH_PIPELINE
SOCIAL_AUTH_TUNNISTAMO_KEY = env("SOCIAL_AUTH_TUNNISTAMO_KEY")
SOCIAL_AUTH_TUNNISTAMO_SECRET = env("SOCIAL_AUTH_TUNNISTAMO_SECRET")
SOCIAL_AUTH_TUNNISTAMO_OIDC_ENDPOINT = env("SOCIAL_AUTH_TUNNISTAMO_OIDC_ENDPOINT")
# Profiles related settings

CONTACT_METHODS = (("email", "Email"), ("sms", "SMS"))

TEMPORARY_PROFILE_READ_ACCESS_TOKEN_VALIDITY_MINUTES = env.int(
    "TEMPORARY_PROFILE_READ_ACCESS_TOKEN_VALIDITY_MINUTES"
)

# List of values of the amr claim that give the staff user access
# to verified personal information. If empty, any amr value grants access.
VERIFIED_PERSONAL_INFORMATION_ACCESS_AMR_LIST = env.list(
    "VERIFIED_PERSONAL_INFORMATION_ACCESS_AMR_LIST"
)

# Django-parler

PARLER_LANGUAGES = {
    1: ({"code": "fi"}, {"code": "en"}, {"code": "sv"}),
    "default": {"fallbacks": ["fi"], "hide_untranslated": False},
}

# Graphene

GRAPHENE = {
    "SCHEMA": "open_city_profile.schema.schema",
    "MIDDLEWARE": [
        # NOTE: Graphene runs its middlewares in reverse order!
        "open_city_profile.graphene.AllowedDataFieldsMiddleware",
        "open_city_profile.graphene.JWTMiddleware",
        "open_city_profile.graphene.GQLDataLoaders",
    ],
}

AUDIT_LOG_TO_DB_ENABLED = env.bool("AUDIT_LOG_TO_DB_ENABLED")


_log_level = env("OPEN_CITY_PROFILE_LOG_LEVEL")
if not _log_level:
    _log_level = "DEBUG" if DEBUG else "INFO"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "context": {
            "()": "logger_extra.filter.LoggerContextFilter",
        }
    },
    "formatters": {
        "json": {
            "()": "logger_extra.formatter.JSONFormatter",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "filters": ["context"],
        },
    },
    "loggers": {
        app_name: {"handlers": ["console"], "level": _log_level, "propagate": True}
        for app_name in (
            "audit_log",
            "open_city_profile",
            "profiles",
            "services",
            "users",
            "utils",
        )
    },
}

GDPR_AUTH_CALLBACK_URL = env("GDPR_AUTH_CALLBACK_URL")
KEYCLOAK_BASE_URL = env("KEYCLOAK_BASE_URL")
KEYCLOAK_REALM = env("KEYCLOAK_REALM")
KEYCLOAK_CLIENT_ID = env("KEYCLOAK_CLIENT_ID")
KEYCLOAK_CLIENT_SECRET = env("KEYCLOAK_CLIENT_SECRET")
KEYCLOAK_GDPR_CLIENT_ID = env("KEYCLOAK_GDPR_CLIENT_ID")
KEYCLOAK_GDPR_CLIENT_SECRET = env("KEYCLOAK_GDPR_CLIENT_SECRET")

# get build time from a file in docker image
APP_BUILD_TIME = datetime.fromtimestamp(os.path.getmtime(__file__))

CSP_CONNECT_SRC = env.str("CSP_CONNECT_SRC")
CSP_IMG_SRC = env.str("CSP_IMG_SRC")
CSP_STYLE_SRC = env.str("CSP_STYLE_SRC")
CSP_SCRIPT_SRC = env.str("CSP_SCRIPT_SRC")
CSP_REPORT_ONLY = env.bool("CSP_REPORT_ONLY")
CSP_REPORT_URI = env.str("CSP_REPORT_URI")
