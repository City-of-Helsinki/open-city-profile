from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.decorators.csrf import csrf_exempt
from graphene_django.views import GraphQLView
from rest_framework import routers
from rest_framework.documentation import include_docs_urls

from profiles.api import BasicProfileViewSet, GeoDivisionViewSet, InterestConceptViewSet
from youths.api import YouthProfileViewSet

router = routers.DefaultRouter()
router.register("profile", BasicProfileViewSet)
router.register("youth-profile", YouthProfileViewSet)
router.register(
    "interest-concept", InterestConceptViewSet, base_name="interest-concept"
)
router.register("geo-division", GeoDivisionViewSet, base_name="geo-division")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("v1/", include(router.urls)),
    path("docs/", include_docs_urls(title="Open City profile")),
    path("accounts/", include("allauth.urls")),
    path("graphql/", csrf_exempt(GraphQLView.as_view(graphiql=True))),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
