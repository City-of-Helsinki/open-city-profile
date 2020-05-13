from django.conf import settings
from django.http import HttpResponse, JsonResponse

from youths.models import YouthProfile


def profiles(request, *args, **kwargs):
    if settings.GDPR_API_ENABLED:
        # TODO: Add authentication and security
        if request.method == "GET":
            youth_profile = YouthProfile.objects.get(profile__pk=kwargs["id"])
            return JsonResponse(youth_profile.serialize(), safe=False)
        else:
            return HttpResponse(status=405)
    else:
        return HttpResponse(status=404)
