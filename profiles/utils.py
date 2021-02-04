import threading
from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from graphql_relay.node.node import from_global_id

from open_city_profile.exceptions import InvalidEmailFormatError

if TYPE_CHECKING:
    import profiles.models
    import users.models


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


def set_current_service(service):
    _thread_locals.service = service


def get_current_user():
    request = getattr(_thread_locals, "request", None)
    return getattr(request, "user", None) if request else None


def get_current_service():
    return getattr(_thread_locals, "service", None)


def user_has_staff_perms_to_view_profile(
    user: "users.models.User", profile: "profiles.models.Profile"
) -> bool:
    """
    Checks is passed user has "can_view_profiles" permissions
    for any service connected to the passed profile.
    """

    service_conns = profile.service_connections.all()
    return any(
        [
            user.has_perm("can_view_profiles", service_conn.service)
            for service_conn in service_conns
        ]
    )
