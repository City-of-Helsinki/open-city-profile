import threading
from typing import TYPE_CHECKING

from graphql_relay.node.node import from_global_id

if TYPE_CHECKING:
    import profiles.models
    import users.models


_thread_locals = threading.local()


def create_nested(model, profile, data):
    for add_input in data:
        if add_input:
            item = model(profile=profile)
            for field, value in add_input.items():
                if field == "primary" and value is True:
                    model.objects.filter(profile=profile).update(primary=False)
                setattr(item, field, value)
            item.save()


def update_nested(model, profile, data):
    for update_input in data:
        if update_input:
            id = update_input.pop("id")
            item = model.objects.get(profile=profile, pk=from_global_id(id)[1])
            for field, value in update_input.items():
                if field == "primary" and value is True:
                    model.objects.filter(profile=profile).update(primary=False)
                setattr(item, field, value)
            item.save()


def delete_nested(model, profile, data):
    for remove_id in data:
        model.objects.get(profile=profile, pk=from_global_id(remove_id)[1]).delete()


def set_current_user(user):
    _thread_locals.user = user


def set_current_service(service):
    _thread_locals.service = service


def get_current_user():
    return getattr(_thread_locals, "user", None)


def get_current_service():
    return getattr(_thread_locals, "service", None)


def user_has_staff_perms_to_view_profile(
    user: "users.models.User", profile: "profiles.models.Profile"
) -> bool:
    """
    Checks is passed user has "can_view_profiles" permissions
    for any service connected to the passed profile.
    """

    service_conns = profile.service_connections.filter(enabled=True)
    return any(
        [
            user.has_perm("can_view_profiles", service_conn.service)
            for service_conn in service_conns
        ]
    )
