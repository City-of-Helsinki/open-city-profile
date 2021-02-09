import json
import logging
from datetime import datetime, timezone

from django.conf import settings
from django.db.models.signals import post_delete, post_init, post_save
from django.dispatch import receiver

from .utils import get_current_service, get_current_user


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


def _format_user_data(audit_event, field_name, user):
    if user:
        audit_event[field_name]["user_id"] = (
            str(user.uuid) if hasattr(user, "uuid") else None
        )
        if settings.AUDIT_LOG_USERNAME:
            audit_event[field_name]["user_name"] = (
                user.username if hasattr(user, "username") else None
            )


def log(action, instance):
    profile_parts = {
        "Profile": "base profile",
        "SensitiveData": "sensitive data",
    }

    if (
        settings.AUDIT_LOGGING_ENABLED
        and should_audit(instance.__class__)
        and instance.pk
    ):
        logger = logging.getLogger("audit")

        current_time = datetime.now(tz=timezone.utc)
        current_user = get_current_user()
        profile = instance.resolve_profile()
        profile_id = str(profile.pk) if profile else None
        target_user = profile.user if profile and profile.user else None

        message = {
            "audit_event": {
                "origin": "PROFILE-BE",
                "status": "SUCCESS",
                "date_time_epoch": int(current_time.timestamp()),
                "date_time": f"{current_time.replace(tzinfo=None).isoformat(sep='T', timespec='milliseconds')}Z",
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
        logger.info(json.dumps(message))


@receiver(post_delete)
def post_delete_audit_log(sender, instance, **kwargs):
    log("DELETE", instance)


@receiver(post_init)
def post_init_audit_log(sender, instance, **kwargs):
    log("READ", instance)


@receiver(post_save)
def post_save_audit_log(sender, instance, created, **kwargs):
    if created:
        log("CREATE", instance)
    else:
        log("UPDATE", instance)
