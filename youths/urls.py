from django.urls import path

from youths.views import YouthProfileGDPRAPIView

app_name = "youths"
urlpatterns = [
    path("<uuid:pk>", YouthProfileGDPRAPIView.as_view(), name="gdpr"),
]
