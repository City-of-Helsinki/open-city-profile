import json
import logging
from datetime import datetime, timezone

from django.conf import settings
from django.utils.text import camel_case_to_spaces

from .utils import (
    get_current_client_id,
    get_current_service,
    get_current_user,
    get_original_client_ip,
)


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
        current_user = get_current_user()
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

        service = get_current_service()
        if service:
            message["audit_event"]["actor"]["service_name"] = service.name
        client_id = get_current_client_id()
        if client_id:
            message["audit_event"]["actor"]["client_id"] = client_id

        ip_address = get_original_client_ip()
        if ip_address:
            message["audit_event"]["actor"]["ip_address"] = ip_address

        logger.info(json.dumps(message))
