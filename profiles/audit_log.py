import json
import logging
import threading
from datetime import datetime, timezone

from django.conf import settings

from .utils import get_current_service, get_current_user, get_original_client_ip

_thread_locals = threading.local()


def _should_audit(model):
    if hasattr(model, "audit_log") and model.audit_log:
        return True
    return False


def add_loggable(action, instance):
    if (
        settings.AUDIT_LOGGING_ENABLED
        and _should_audit(instance.__class__)
        and instance.pk
    ):
        current_time = datetime.now(tz=timezone.utc)

        if not hasattr(_thread_locals, "loggables"):
            _thread_locals.loggables = list()
        _thread_locals.loggables.append((current_time, action, instance))


def _resolve_role(current_user, profile):
    if profile.user == current_user:
        return "OWNER"
    elif current_user is not None:
        return "ADMIN"
    else:
        return "SYSTEM"


def _format_user_data(audit_event, field_name, user):
    if user:
        audit_event[field_name]["user_id"] = (
            str(user.uuid) if hasattr(user, "uuid") else None
        )
        if settings.AUDIT_LOG_USERNAME:
            audit_event[field_name]["user_name"] = (
                user.username if hasattr(user, "username") else None
            )


def flush_audit_log():
    profile_parts = {
        "Profile": "base profile",
        "SensitiveData": "sensitive data",
    }

    logger = logging.getLogger("audit")

    for event_time, action, instance in getattr(_thread_locals, "loggables", list()):
        current_user = get_current_user()
        profile = instance.resolve_profile()
        profile_id = str(profile.pk) if profile else None
        target_user = profile.user if profile and profile.user else None

        message = {
            "audit_event": {
                "origin": "PROFILE-BE",
                "status": "SUCCESS",
                "date_time_epoch": int(event_time.timestamp()),
                "date_time": f"{event_time.replace(tzinfo=None).isoformat(sep='T', timespec='milliseconds')}Z",
                "actor": {"role": _resolve_role(current_user, profile)},
                "operation": action,
                "target": {
                    "profile_id": profile_id,
                    "profile_part": profile_parts[instance.__class__.__name__],
                },
            }
        }

        _format_user_data(message["audit_event"], "actor", current_user)

        _format_user_data(message["audit_event"], "target", target_user)

        service = get_current_service()
        if service:
            message["audit_event"]["actor_service"] = {
                "id": str(service.name),
                "name": str(service.label),
            }

        ip_address = get_original_client_ip()
        if ip_address:
            message["audit_event"]["profilebe"] = {
                "ip_address": ip_address,
            }

        logger.info(json.dumps(message))

    _thread_locals.loggables = list()
