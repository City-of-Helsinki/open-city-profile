import threading

from graphql_relay.node.node import from_global_id

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
