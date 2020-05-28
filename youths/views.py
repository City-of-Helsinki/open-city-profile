from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from youths.models import YouthProfile


class YouthProfileGDPRAPIView(APIView):
    # TODO: Add authentication and security

    def dispatch(self, request, *args, **kwargs):
        if not settings.GDPR_API_ENABLED:
            return HttpResponse(status=404)
        return super().dispatch(request, *args, **kwargs)

    def get_object(self) -> YouthProfile:
        return get_object_or_404(YouthProfile, profile__pk=self.kwargs["pk"])

    def get(self, request, *args, **kwargs):
        """Retrieve all youth profile data related to the given id."""
        return Response(self.get_object().serialize(), status=status.HTTP_200_OK)
