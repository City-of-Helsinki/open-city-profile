import json
import logging
import threading
from datetime import datetime, timezone

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.text import camel_case_to_spaces

from .models import Profile
from .utils import (
    get_current_client_id,
    get_current_request,
    get_current_service,
    get_current_user,
    get_original_client_ip,
)

User = get_user_model()


_thread_locals = threading.local()


def should_audit(model):
    if hasattr(model, "audit_log") and model.audit_log:
        return True
    return False


def _resolve_role(current_user, profile_user):
    if profile_user and current_user and profile_user.uuid == current_user.uuid:
        return "OWNER"
    elif current_user is not None:
        return "ADMIN"
    else:
        return "SYSTEM"


def _profile_part(instance):
    class_name = instance.__class__.__name__

    if class_name == "Profile":
        return "base profile"

    return camel_case_to_spaces(class_name)


def _format_user_data(audit_event, field_name, user):
    if user:
        audit_event[field_name]["user_id"] = (
            str(user.uuid) if hasattr(user, "uuid") else None
        )


def log(action, instance):
    request = get_current_request()
    if request is None or getattr(_thread_locals, "pause", False):
        return

    if (
        settings.AUDIT_LOGGING_ENABLED
        and should_audit(instance.__class__)
        and instance.pk
    ):
        profile = (
            instance.profile
            if hasattr(instance, "profile")
            else instance.resolve_profile()
        )

        profile_part = _profile_part(instance)

        loggables = request.audit_loggables[profile.pk]
        if action == "DELETE" and isinstance(instance, Profile):
            # If the Profile is about to get deleted,
            # need to store the User before it gets deleted too.
            loggables["user"] = profile.user
        loggables["profile"] = profile
        loggables["parts"].add((action, profile_part))


def _produce_json_logs(
    current_user, current_time, service, client_id, ip_address, audit_loggables
):
    logger = logging.getLogger("audit")
    date_time_epoch = int(current_time.timestamp() * 1000)
    date_time = f"{current_time.replace(tzinfo=None).isoformat(sep='T', timespec='milliseconds')}Z"

    for profile_id, data in audit_loggables.items():
        profile_user = data.get("user")

        for action, profile_part in data["parts"]:
            message = {
                "audit_event": {
                    "origin": "PROFILE-BE",
                    "status": "SUCCESS",
                    "date_time_epoch": date_time_epoch,
                    "date_time": date_time,
                    "actor": {"role": _resolve_role(current_user, profile_user)},
                    "operation": action,
                    "target": {"id": str(profile_id), "type": profile_part},
                }
            }

            _format_user_data(message["audit_event"], "actor", current_user)

            _format_user_data(message["audit_event"], "target", profile_user)

            if service:
                message["audit_event"]["actor"]["service_name"] = service.name

            if client_id:
                message["audit_event"]["actor"]["client_id"] = client_id

            if ip_address:
                message["audit_event"]["actor"]["ip_address"] = ip_address

            logger.info(json.dumps(message))


def save_audit_logs():
    _thread_locals.pause = True

    try:
        current_time = datetime.now(tz=timezone.utc)
        current_user = get_current_user()

        service = get_current_service()
        client_id = get_current_client_id()
        ip_address = get_original_client_ip()

        audit_loggables = get_current_request().audit_loggables

        profiles = []
        for data in audit_loggables.values():
            profiles.append(data["profile"])
        for user in (
            User.objects.select_related("profile").filter(profile__in=profiles).all()
        ):
            audit_loggables[user.profile.id]["user"] = user

        _produce_json_logs(
            current_user, current_time, service, client_id, ip_address, audit_loggables
        )
    finally:
        _thread_locals.pause = False
