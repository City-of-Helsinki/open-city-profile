from functools import wraps

from django.core.exceptions import PermissionDenied
from django.utils.translation import ugettext_lazy as _
from graphql.execution.base import ResolveInfo

from open_city_profile.exceptions import ServiceNotIdentifiedError


def _use_context_tests(*test_funcs):
    def decorator(decorator_function):
        @wraps(decorator_function)
        def wrapper(function):
            @wraps(function)
            def context_tester(*args, **kwargs):
                info = next(arg for arg in args if isinstance(arg, ResolveInfo))
                context = info.context

                for test_func in test_funcs:
                    test_func(context)

                return function(*args, **kwargs)

            return context_tester

        return wrapper

    return decorator


def _require_authenticated(context):
    if not context.user.is_authenticated:
        raise PermissionDenied(_("You do not have permission to perform this action."))


def _require_service(context):
    if not context.service:
        raise ServiceNotIdentifiedError("No service identified")


def _require_service_permission(permission_name):
    def permission_checker(context):
        _require_service(context)

        if not context.user.has_perm(permission_name, context.service):
            raise PermissionDenied(
                _("You do not have permission to perform this action.")
            )

    return permission_checker


@_use_context_tests(_require_authenticated, _require_service)
def login_and_service_required():
    """Decorator for checking that the user is logged in and service is known"""


def staff_required(required_permission="view"):
    """
    Returns a decorator that checks if user has staff permission on profiles for service
    specified in the request. Required permission can be defined as an argument,
    defaults to 'view'.
    """

    if required_permission not in ("view", "manage"):
        raise ValueError(
            "Invalid required_permission given as argument: '{}'".format(
                required_permission
            )
        )

    @_use_context_tests(
        _require_service_permission("can_{}_profiles".format(required_permission))
    )
    def check_permission():
        f"""Decorator that checks for can_{required_permission}_profiles permission."""

    return check_permission
