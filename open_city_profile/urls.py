from csp.decorators import csp_exempt
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponse, JsonResponse
from django.urls import include, path
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView
from graphql_sync_dataloaders import DeferredExecutionContext

from open_city_profile import __version__
from open_city_profile.views import GraphQLView

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "graphql/",
        csp_exempt(
            csrf_exempt(
                GraphQLView.as_view(
                    graphiql=settings.ENABLE_GRAPHIQL or settings.DEBUG,
                    execution_context_class=DeferredExecutionContext,
                )
            )
        ),
    ),
    path("auth/", include("helusers.urls")),
    path(
        "docs/gdpr-api/",
        TemplateView.as_view(
            template_name="swagger-ui.html",
            extra_context={
                "title": _("Open-city-profile GDPR API specification"),
                "openapi_url": "open-city-profile/gdpr-api-openapi.yaml",
            },
        ),
        name="gdpr-api-docs",
    ),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


#
# Kubernetes liveness & readiness probes
#
def healthz(*args, **kwargs):
    return HttpResponse(status=200)


def readiness(*args, **kwargs):
    response_json = {
        "status": "ok",
        "packageVersion": __version__,
        "commitHash": settings.COMMIT_HASH,
        "buildTime": settings.APP_BUILD_TIME.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
    }
    return JsonResponse(response_json, status=200)


urlpatterns += [path("healthz", healthz), path("readiness", readiness)]
