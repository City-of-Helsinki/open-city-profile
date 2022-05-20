import json
import logging
import threading
from collections import defaultdict
from datetime import datetime, timezone

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.text import camel_case_to_spaces

User = get_user_model()

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
        request._audit_loggables = defaultdict(lambda: {"parts": dict()})

        response = self.get_response(request)

        _commit_audit_logs()
        _thread_locals.__dict__.clear()

        return response


def _get_profile_and_loggables(instance):
    if not settings.AUDIT_LOGGING_ENABLED:
        return

    audit_loggables = getattr(_get_current_request(), "_audit_loggables", None)

    if (
        audit_loggables is not None
        and getattr(instance.__class__, "audit_log", False)
        and instance.pk
    ):
        profile = (
            instance.profile
            if hasattr(instance, "profile")
            else instance.resolve_profile()
        )

        return profile, audit_loggables[profile.pk]


def _resolve_role(current_user, profile_user_uuid):
    if profile_user_uuid and current_user and profile_user_uuid == current_user.uuid:
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


def register_loggable(instance):
    profile_and_loggables = _get_profile_and_loggables(instance)

    if profile_and_loggables is not None:
        profile, profile_loggables = profile_and_loggables

        profile_loggables["profile"] = profile
        if profile.user:
            profile_loggables["user_uuid"] = profile.user.uuid


def log(action, instance):
    profile_and_loggables = _get_profile_and_loggables(instance)

    if profile_and_loggables is not None:
        profile, profile_loggables = profile_and_loggables

        profile_loggables["profile"] = profile
        data_action = (action, _profile_part(instance))
        if data_action not in profile_loggables["parts"]:
            profile_loggables["parts"][data_action] = datetime.now(tz=timezone.utc)


def _produce_json_logs(current_user, service, client_id, ip_address, audit_loggables):
    logger = logging.getLogger("audit")

    actor_dict = {}

    if service:
        actor_dict["service_name"] = service.name

    if client_id:
        actor_dict["client_id"] = client_id

    if ip_address:
        actor_dict["ip_address"] = ip_address

    if current_user:
        actor_dict["user_id"] = str(current_user.uuid)

    for profile_id, data in audit_loggables.items():
        target_user_uuid = data.get("user_uuid")

        actor_dict["role"] = _resolve_role(current_user, target_user_uuid)

        target_dict = {
            "id": str(profile_id),
        }
        if target_user_uuid:
            target_dict["user_id"] = str(target_user_uuid)

        for (action, profile_part), timestamp in data["parts"].items():
            target_dict["type"] = profile_part

            message = {
                "audit_event": {
                    "origin": "PROFILE-BE",
                    "status": "SUCCESS",
                    "date_time_epoch": int(timestamp.timestamp() * 1000),
                    "date_time": f"{timestamp.replace(tzinfo=None).isoformat(sep='T', timespec='milliseconds')}Z",
                    "actor": actor_dict,
                    "operation": action,
                    "target": target_dict,
                }
            }

            logger.info(json.dumps(message))


def _commit_audit_logs():
    request = _get_current_request()

    audit_loggables = getattr(request, "_audit_loggables", None)
    if not audit_loggables:
        return

    del request._audit_loggables

    current_user = _get_current_user()
    service = _get_current_service()
    client_id = _get_current_client_id()
    ip_address = _get_original_client_ip()

    profiles = [log_data["profile"] for log_data in audit_loggables.values()]
    for ids in User.objects.filter(profile__in=profiles).values("uuid", "profile__id"):
        audit_loggables[ids["profile__id"]]["user_uuid"] = ids["uuid"]

    _produce_json_logs(current_user, service, client_id, ip_address, audit_loggables)
