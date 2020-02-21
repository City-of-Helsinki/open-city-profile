from functools import wraps

from django.core.exceptions import PermissionDenied
from django.utils.translation import ugettext_lazy as _
from graphql.execution.base import ResolveInfo

from services.models import Service


def context(f):
    # helper decorator to get the context for the actual decorator
    def decorator(func):
        def wrapper(*args, **kwargs):
            info = next(arg for arg in args if isinstance(arg, ResolveInfo))
            return func(info.context, *args, **kwargs)

        return wrapper

    return decorator


def staff_required(required_permission="view"):
    """
    Decorator for checking if user has staff permission on profiles for service
    specified in the request. Required permission can be defined as an argument,
    defaults to 'view'.
    """

    def method_wrapper(function):
        @wraps(function)
        @context(function)
        def wrapper(context, *args, **kwargs):
            if required_permission not in ("view", "manage"):
                raise ValueError(
                    "Invalid required_permission given as argument: '{}'".format(
                        required_permission
                    )
                )
            service = Service.objects.get(service_type=kwargs["service_type"])
            if context.user.has_perm(
                "can_{}_profiles".format(required_permission), service
            ):
                return function(*args, **kwargs)
            else:
                raise PermissionDenied(
                    _("You do not have permission to perform this action.")
                )

        return wrapper

    return method_wrapper
