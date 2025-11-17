from functools import wraps

from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext_lazy as _
from graphql.type import GraphQLResolveInfo

from open_city_profile.exceptions import ServiceNotIdentifiedError


def _use_context_tests(*test_funcs):
    """
    Decorator for running context tests before the decorated function.

    E.g. to create a decorator that checks that the user is authenticated::

        def _require_authenticated(context):
            # Check that the user is authenticated
            ...

        @_use_context_tests(_require_authenticated)
        def login_required():
            pass
    """

    def decorator(decorator_function):
        @wraps(decorator_function)
        def wrapper(function):
            @wraps(function)
            def context_tester(*args, **kwargs):
                info = next(arg for arg in args if isinstance(arg, GraphQLResolveInfo))
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
    if not getattr(context, "service", None):
        raise ServiceNotIdentifiedError("No service identified")


def _require_permission(permission_name):
    def permission_checker(context):
        if not context.user.has_perm(permission_name):
            raise PermissionDenied(
                _("You do not have permission to perform this action.")
            )

    return permission_checker


def _require_service_permission(permission_name):
    def permission_checker(context):
        _require_service(context)

        if not context.user.has_perm(permission_name, context.service):
            raise PermissionDenied(
                _("You do not have permission to perform this action.")
            )

    return permission_checker


@_use_context_tests(_require_authenticated)
def login_required(*_, **__):
    """Decorator for checking that the user is logged in"""


@_use_context_tests(_require_authenticated, _require_service)
def login_and_service_required(*_, **__):
    """Decorator for checking that the user is logged in and service is known"""


def staff_required(required_permission="view"):
    """
    Returns a decorator that checks if user has staff permission on profiles for service
    specified in the request. Required permission can be defined as an argument,
    defaults to 'view'.
    """

    if required_permission not in ("view", "manage"):
        raise ValueError(
            f"Invalid required_permission given as argument: '{required_permission}'"
        )

    @_use_context_tests(
        _require_service_permission(f"can_{required_permission}_profiles")
    )
    def check_permission():
        """Decorator that checks for can_{required_permission}_profiles permission."""

    return check_permission


def permission_required(permission_name):
    """Returns a decorator for checking that the user has the specified permission"""

    @_use_context_tests(_require_permission(permission_name))
    def check_permission():
        """Decorator that checks for {permission_name} permission."""

    return check_permission
