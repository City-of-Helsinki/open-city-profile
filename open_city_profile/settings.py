import os

import environ
import raven

checkout_dir = environ.Path(__file__) - 2
assert os.path.exists(checkout_dir('manage.py'))

parent_dir = checkout_dir.path('..')
if os.path.isdir(parent_dir('etc')):
    env_file = parent_dir('etc/env')
    default_var_root = parent_dir('var')
else:
    env_file = checkout_dir('.env')
    default_var_root = checkout_dir('var')

env = environ.Env(
    DEBUG=(bool, False),
    TIER=(str, 'dev'),  # one of: prod, qa, stage, test, dev
    SECRET_KEY=(str, ''),
    VAR_ROOT=(str, default_var_root),
    ALLOWED_HOSTS=(list, []),
    DATABASE_URL=(str, 'postgres://open_city_profile:open_city_profile@localhost/open_city_profile'),
    CACHE_URL=(str, 'locmemcache://'),
    EMAIL_URL=(str, 'consolemail://'),
    SENTRY_DSN=(str, ''),
    OIDC_API_TOKEN_AUDIENCE=(str, 'AUDIENCE_UNSET'),
    OIDC_API_TOKEN_API_SCOPE_PREFIX=(str, 'API_SCOPE_PREFIX_UNSET'),
    OIDC_API_TOKEN_REQUIRE_API_SCOPE_FOR_AUTHENTICATION=(str, True),
    OIDC_API_TOKEN_ISSUER=(str, 'ISSUER_UNSET'),
)
if os.path.exists(env_file):
    env.read_env(env_file)

try:
    version = raven.fetch_git_sha(checkout_dir())
except Exception:
    version = None

DEBUG = env.bool('DEBUG')
TIER = env.str('TIER')
SECRET_KEY = env.str('SECRET_KEY')
if DEBUG and not SECRET_KEY:
    SECRET_KEY = 'xxx'

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS')

DATABASES = {'default': env.db()}
CACHES = {'default': env.cache()}
vars().update(env.email_url())  # EMAIL_BACKEND etc.
RAVEN_CONFIG = {'dsn': env.str('SENTRY_DSN'), 'release': version}

var_root = env.path('VAR_ROOT')
MEDIA_ROOT = var_root('media')
STATIC_ROOT = var_root('static')
MEDIA_URL = "/media/"
STATIC_URL = "/static/"

ROOT_URLCONF = 'open_city_profile.urls'
WSGI_APPLICATION = 'open_city_profile.wsgi.application'

LANGUAGE_CODE = 'fi'
TIME_ZONE = 'Europe/Helsinki'
USE_I18N = True
USE_L10N = True
USE_TZ = True


INSTALLED_APPS = [
    'helusers',
    'helusers.providers.helsinki_oidc',

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'raven.contrib.django.raven_compat',

    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'rest_framework',
    'django_filters',
    'parler',
    'thesaurus',

    'users',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Authentication

SITE_ID = 1
AUTH_USER_MODEL = 'users.User'
SOCIALACCOUNT_PROVIDERS = {
    'helsinki_oidc': {
        'VERIFIED_EMAIL': True
    }
}
LOGIN_REDIRECT_URL = '/'
ACCOUNT_LOGOUT_ON_GET = True
SOCIALACCOUNT_ADAPTER = 'helusers.adapter.SocialAccountAdapter'
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_EMAIL_REQUIRED = True
SOCIALACCOUNT_AUTO_SIGNUP = True

OIDC_API_TOKEN_AUTH = {
    'AUDIENCE': env.str('OIDC_API_TOKEN_AUDIENCE'),
    'API_SCOPE_PREFIX': env.str('OIDC_API_TOKEN_API_SCOPE_PREFIX'),
    'REQUIRE_API_SCOPE_FOR_AUTHENTICATION': env.str('OIDC_API_TOKEN_REQUIRE_API_SCOPE_FOR_AUTHENTICATION'),
    'ISSUER': env.str('OIDC_API_TOKEN_ISSUER'),
}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'helusers.oidc.ApiTokenAuthentication',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 100,
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
    ),
}
