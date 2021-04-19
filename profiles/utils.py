import threading

from django.conf import settings
from django.core.exceptions import ValidationError
from graphql_relay.node.node import from_global_id

from open_city_profile.exceptions import InvalidEmailFormatError

_thread_locals = threading.local()


def create_nested(model, profile, data):
    for add_input in filter(None, data):
        item = model(profile=profile)
        for field, value in add_input.items():
            if field == "primary" and value is True:
                model.objects.filter(profile=profile).update(primary=False)
            setattr(item, field, value)
        try:
            item.save()
        except ValidationError:
            if model.__name__ == "Email":
                raise InvalidEmailFormatError("Email must be in valid email format")
            else:
                raise


def update_nested(model, profile, data):
    for update_input in filter(None, data):
        id = update_input.pop("id")
        item = model.objects.get(profile=profile, pk=from_global_id(id)[1])
        for field, value in update_input.items():
            if field == "primary" and value is True:
                model.objects.filter(profile=profile).update(primary=False)
            setattr(item, field, value)
        try:
            item.save()
        except ValidationError:
            if model.__name__ == "Email":
                raise InvalidEmailFormatError("Email must be in valid email format")
            else:
                raise


def delete_nested(model, profile, data):
    for remove_id in filter(None, data):
        model.objects.get(profile=profile, pk=from_global_id(remove_id)[1]).delete()


def set_current_request(request):
    _thread_locals.request = request


def clear_thread_locals():
    _thread_locals.__dict__.clear()


def get_current_request():
    return getattr(_thread_locals, "request", None)


def _get_current_request_attr(attrname):
    request = get_current_request()
    return getattr(request, attrname, None) if request else None


def get_current_user():
    return _get_current_request_attr("user")


def get_original_client_ip():
    client_ip = None

    request = get_current_request()
    if request:
        if settings.USE_X_FORWARDED_FOR:
            forwarded_for = request.headers.get("x-forwarded-for", "")
            client_ip = forwarded_for.split(",")[0] or None

        if not client_ip:
            client_ip = request.META.get("REMOTE_ADDR")

    return client_ip


def get_current_service():
    return _get_current_request_attr("service")


def get_current_client_id():
    return _get_current_request_attr("client_id")


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
