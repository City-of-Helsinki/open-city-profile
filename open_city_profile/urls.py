from django.contrib import admin
from django.urls import include, path
from rest_framework import routers
from rest_framework.documentation import include_docs_urls

from profiles.api import ProfileViewSet

router = routers.DefaultRouter()
router.register('profile', ProfileViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('v1/', include(router.urls)),
    path('docs/', include_docs_urls(title='Open City profile')),
    path('accounts/', include('allauth.urls')),
]
