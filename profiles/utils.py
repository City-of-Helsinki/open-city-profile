from django.conf import settings


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
