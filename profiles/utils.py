import functools
from enum import Enum
from typing import Type, TypeVar

from django.conf import settings

_EnumType = TypeVar("_EnumType", bound=Type[Enum])


def requester_has_service_permission(request, permission):
    service = getattr(request, "service", None)

    if not service:
        return False

    if not hasattr(request, "_service_permission_cache"):
        request._service_permission_cache = dict()

    cache_key = f"{request.user.id}:{service.name}:{permission}"

    result = request._service_permission_cache.get(cache_key)

    if result is None:
        result = request.user.has_perm(permission, service)
        request._service_permission_cache[cache_key] = result

    return result


def requester_can_view_verified_personal_information(request):
    return requester_has_service_permission(
        request, "can_view_verified_personal_information"
    ) and (
        not settings.VERIFIED_PERSONAL_INFORMATION_ACCESS_AMR_LIST
        or request.user_auth.data.get("amr")
        in settings.VERIFIED_PERSONAL_INFORMATION_ACCESS_AMR_LIST
    )


def requester_has_sufficient_loa_to_perform_gdpr_request(request):
    user = request.user
    profile = user.profile
    if not profile:
        return False
    loa = request.user_auth.data.get("loa")
    return not hasattr(profile, "verified_personal_information") or loa in [
        "substantial",
        "high",
    ]


def force_list(value) -> list:
    """
    Ensure that the given value is a list. If the value is None, return an empty list.
    """
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


@functools.cache
def enum_values(enum: _EnumType) -> list:
    """
    Return a list of values from the given enum.
    """
    return [e.value for e in enum]
