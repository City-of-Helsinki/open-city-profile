import json

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path
from django.views.decorators.csrf import csrf_exempt

from open_city_profile.views import GraphQLView
from youths.views import profiles

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path(
        "graphql/",
        csrf_exempt(
            GraphQLView.as_view(graphiql=settings.ENABLE_GRAPHIQL or settings.DEBUG)
        ),
    ),
]

if settings.GDPR_API_ENABLED:
    urlpatterns += [
        path("profiles/<uuid:id>", profiles)
    ]  # TODO: This will go to youth backend

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


#
# Kubernetes liveness & readiness probes
#
def healthz(*args, **kwargs):
    return HttpResponse(status=200)


def readiness(*args, **kwargs):
    return HttpResponse(status=200)


def thisisthemostsecretsettingsprintendpointandyoushouldnothavefoundit(*args, **kwargs):
    context = {}
    for setting in dir(settings):
        if setting.isupper() and setting in (
            "ALLOWED_HOSTS",
            "DEBUG",
            "SENTRY_DSN",
            "SENTRY_ENVIRONMENT",
            "SKIP_DATABASE_CHECK",
            "TOKEN_AUTH_ACCEPTED_AUDIENCE",
            "TOKEN_AUTH_ACCEPTED_SCOPE_PREFIX",
            "TOKEN_AUTH_AUTHSERVER_URL",
            "TOKEN_AUTH_REQUIRE_SCOPE",
            "VERSION",
            "DEFAULT_FROM_EMAIL",
            "FORCE_SCRIPT_NAME",
            "MEDIA_URL",
            "STATIC_URL",
            "CSRF_COOKIE_NAME",
            "CSRF_COOKIE_PATH",
            "CSRF_COOKIE_SECURE",
            "SESSION_COOKIE_NAME",
            "SESSION_COOKIE_PATH",
            "SESSION_COOKIE_SECURE",
            "USE_X_FORWARDED_HOST",
        ):
            context[setting] = getattr(settings, setting)

    return HttpResponse(json.dumps(context, indent=4), content_type="application/json")


urlpatterns += [
    path("healthz", healthz),
    path("readiness", readiness),
    path(
        "thisisthemostsecretsettingsprintendpointandyoushouldnothavefoundit",
        thisisthemostsecretsettingsprintendpointandyoushouldnothavefoundit,
    ),
]
