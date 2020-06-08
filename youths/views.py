from django.conf import settings
from django.db import DatabaseError, transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.exceptions import APIException
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from utils.models import SerializableMixin
from youths.models import YouthProfile


class DeletionNotAllowed(APIException):
    status_code = 403
    default_detail = "Profile cannot be deleted."
    default_code = "deletion_not_allowed"


class DryRunException(Exception):
    """Indicate that request is being done as a dry run."""


class DryRunSerializer(serializers.Serializer):
    dry_run = serializers.BooleanField(required=False, default=False)


class YouthProfileGDPRAPIView(APIView):
    # TODO: Add authentication and security

    model = YouthProfile
    renderer_classes = [JSONRenderer]

    def dispatch(self, request, *args, **kwargs):
        if not settings.GDPR_API_ENABLED:
            return HttpResponse(status=404)
        return super().dispatch(request, *args, **kwargs)

    def get_object(self) -> SerializableMixin:
        return get_object_or_404(self.model, profile__pk=self.kwargs["pk"])

    def check_dry_run(self):
        """Check if parameters provided to the view indicate it's being used for dry_run."""
        data = DryRunSerializer(data=self.request.data)
        query = DryRunSerializer(data=self.request.query_params)
        data.is_valid()
        query.is_valid()

        if data.validated_data["dry_run"] or query.validated_data["dry_run"]:
            raise DryRunException()

    def get(self, request, *args, **kwargs):
        """Retrieve all profile data related to the given id."""
        return Response(self.get_object().serialize(), status=status.HTTP_200_OK)

    def delete(self, request, *args, **kwargs):
        """Delete all data related to the given profile.

        Deletes all data related to the given profile id, or just checks if the data can be deleted,
        depending on the `dry_run` parameter. Raises DeletionNotAllowed if the item

        Dry run delete is expected to always give the same end result as the proper delete i.e. if
        dry run indicated deleting is OK, the proper delete should be OK too.
        """
        try:
            with transaction.atomic():
                self.get_object().delete()
                self.check_dry_run()
        except DryRunException:
            # Deletion is possible. Due to dry run, transaction is rolled back.
            pass
        except DatabaseError:
            raise DeletionNotAllowed()

        return Response(status=status.HTTP_204_NO_CONTENT)
