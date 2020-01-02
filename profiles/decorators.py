from django.core.exceptions import PermissionDenied
from django.utils.translation import ugettext_lazy as _

from services.models import Service


def staff_required(required_permission="view"):
    """
    Decorator for checking if user has staff permission on profiles for service
    specified in the request. Required permission can be defined as an argument,
    defaults to 'view'.
    """

    def method_wrapper(function):
        def wrapper(self, info, **kwargs):
            if required_permission not in ("view", "manage"):
                raise ValueError(
                    "Invalid required_permission given as argument: '{}'".format(
                        required_permission
                    )
                )
            service = Service.objects.get(service_type=kwargs["serviceType"])
            if info.context.user.has_perm(
                "can_{}_profiles".format(required_permission), service
            ):
                return function(self, info, **kwargs)
            else:
                raise PermissionDenied(
                    _("You do not have permission to perform this action.")
                )

        return wrapper

    return method_wrapper
