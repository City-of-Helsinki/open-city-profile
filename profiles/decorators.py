from functools import wraps

from django.core.exceptions import PermissionDenied
from django.utils.translation import ugettext_lazy as _
from graphql.execution.base import ResolveInfo

from open_city_profile.exceptions import ServiceNotIdentifiedError


def context_helper(f):
    # helper decorator to get the context for the actual decorator
    def decorator(func):
        def wrapper(*args, **kwargs):
            info = next(arg for arg in args if isinstance(arg, ResolveInfo))
            return func(info.context, *args, **kwargs)

        return wrapper

    return decorator


def login_and_service_required(function):
    """Decorator for checking that the user is logged in and service is known"""

    @wraps(function)
    @context_helper(function)
    def wrapper(context, *args, **kwargs):
        if not context.user.is_authenticated:
            raise PermissionDenied(
                _("You do not have permission to perform this action.")
            )

        if not context.service:
            raise ServiceNotIdentifiedError("No service identified")

        return function(*args, **kwargs)

    return wrapper


def staff_required(required_permission="view"):
    """
    Decorator for checking if user has staff permission on profiles for service
    specified in the request. Required permission can be defined as an argument,
    defaults to 'view'.
    """

    def method_wrapper(function):
        @wraps(function)
        @context_helper(function)
        def wrapper(context, *args, **kwargs):
            if required_permission not in ("view", "manage"):
                raise ValueError(
                    "Invalid required_permission given as argument: '{}'".format(
                        required_permission
                    )
                )

            if not context.service:
                raise ServiceNotIdentifiedError(_("No service identified"))

            if context.user.has_perm(
                "can_{}_profiles".format(required_permission), context.service
            ):
                return function(*args, **kwargs)
            else:
                raise PermissionDenied(
                    _("You do not have permission to perform this action.")
                )

        return wrapper

    return method_wrapper
