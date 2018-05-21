from django.contrib import admin
from django.urls import include, path
from rest_framework import routers
from rest_framework.documentation import include_docs_urls


router = routers.DefaultRouter()

urlpatterns = [
    path('admin/', admin.site.urls),
    path('v1/', include(router.urls)),
    path('docs/', include_docs_urls(title='Open City profile')),
]
