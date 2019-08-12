import logging

from django.utils.translation import ugettext_lazy as _
from rest_framework import permissions, serializers, viewsets
from rest_framework.exceptions import APIException
from rest_framework.renderers import BrowsableAPIRenderer, JSONRenderer

from youths.models import YouthProfile

logger = logging.getLogger(__name__)


class YouthProfileAlreadyExists(APIException):
    status_code = 409
    default_detail = _("The youth profile for this user already exists.")
    default_code = "profile_already_exists"


class YouthProfileSerializer(serializers.ModelSerializer):
    class Meta:
        exclude = ["id"]
        depth = 1
        model = YouthProfile


class YouthProfileViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = YouthProfile.objects.all()
    serializer_class = YouthProfileSerializer
    lookup_field = "profile__user__uuid"
    renderer_classes = [JSONRenderer, BrowsableAPIRenderer]

    def get_queryset(self):
        if self.request.user.is_superuser:
            return self.queryset
        return self.queryset.filter(profile=self.request.user.profile)

    def perform_create(self, serializer):
        queryset = YouthProfile.objects.filter(profile=self.request.user.profile)
        if queryset.exists():
            raise YouthProfileAlreadyExists()

        serializer.save(profile=self.request.user.profile)
