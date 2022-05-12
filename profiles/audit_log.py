import json
import logging
import threading
from datetime import datetime, timezone

from django.conf import settings
from django.utils.text import camel_case_to_spaces

_thread_locals = threading.local()


def _get_current_request():
    return getattr(_thread_locals, "request", None)


def _get_current_user():
    return getattr(_get_current_request(), "user", None)


def _get_original_client_ip():
    client_ip = None

    request = _get_current_request()
    if request:
        if settings.USE_X_FORWARDED_FOR:
            forwarded_for = request.headers.get("x-forwarded-for", "")
            client_ip = forwarded_for.split(",")[0] or None

        if not client_ip:
            client_ip = request.META.get("REMOTE_ADDR")

    return client_ip


def _get_current_service():
    return getattr(_get_current_request(), "service", None)


def _get_current_client_id():
    return getattr(_get_current_request(), "client_id", None)


class AuditLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_locals.request = request

        response = self.get_response(request)

        _thread_locals.__dict__.clear()

        return response


def should_audit(model):
    if hasattr(model, "audit_log") and model.audit_log:
        return True
    return False


def _resolve_role(current_user, profile):
    if profile.user == current_user:
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
    if (
        settings.AUDIT_LOGGING_ENABLED
        and should_audit(instance.__class__)
        and instance.pk
    ):
        logger = logging.getLogger("audit")

        current_time = datetime.now(tz=timezone.utc)
        current_user = _get_current_user()
        profile = (
            instance.profile
            if hasattr(instance, "profile")
            else instance.resolve_profile()
        )
        profile_id = str(profile.pk) if profile else None
        target_user = profile.user if profile and profile.user else None

        message = {
            "audit_event": {
                "origin": "PROFILE-BE",
                "status": "SUCCESS",
                "date_time_epoch": int(current_time.timestamp() * 1000),
                "date_time": f"{current_time.replace(tzinfo=None).isoformat(sep='T', timespec='milliseconds')}Z",
                "actor": {"role": _resolve_role(current_user, profile)},
                "operation": action,
                "target": {"id": profile_id, "type": _profile_part(instance)},
            }
        }

        _format_user_data(message["audit_event"], "actor", current_user)

        _format_user_data(message["audit_event"], "target", target_user)

        service = _get_current_service()
        if service:
            message["audit_event"]["actor"]["service_name"] = service.name
        client_id = _get_current_client_id()
        if client_id:
            message["audit_event"]["actor"]["client_id"] = client_id

        ip_address = _get_original_client_ip()
        if ip_address:
            message["audit_event"]["actor"]["ip_address"] = ip_address

        logger.info(json.dumps(message))
