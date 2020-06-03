import json
import logging
from datetime import datetime

from django.conf import settings
from django.db.models.signals import post_delete, post_init, post_save
from django.dispatch import receiver

from .utils import get_current_service, get_current_user


def should_audit(model):
    if hasattr(model, "audit_log") and model.audit_log:
        return True
    return False


def log(action, instance):
    def _resolve_role(current_user, profile):
        if profile.user == current_user:
            return "profileowner"
        elif current_user is not None:
            return "admin"
        else:
            return "system"

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

        current_time = datetime.utcnow()
        current_user = get_current_user()
        profile = instance.resolve_profile()
        profile_id = str(profile.pk) if profile else None
        user_id = profile.user.pk if profile and profile.user else None

        message = {
            "profile_event": {
                "status": "SUCCESS",
                "date_time_epoch": str(int(current_time.timestamp())),
                "date_time": f"{current_time.isoformat(sep='T', timespec='milliseconds')}Z",
                "actor_user": {
                    "role": _resolve_role(current_user, profile),
                    "user_id": current_user.pk if current_user else None,
                },
                "operation": action,
                "target_profile": {
                    "user_id": user_id,
                    "profile_id": profile_id,
                    "profile_part": profile_parts[instance.__class__.__name__],
                },
            }
        }
        service = get_current_service()
        if service:
            message["profile_event"]["actor_service"] = {
                "id": str(service.name),
                "name": str(service.label),
            }
        logger.info(json.dumps(message))


@receiver(post_delete)
def post_delete_audit_log(sender, instance, **kwargs):
    log("delete", instance)


@receiver(post_init)
def post_init_audit_log(sender, instance, **kwargs):
    log("read", instance)


@receiver(post_save)
def post_save_audit_log(sender, instance, created, **kwargs):
    if created:
        log("create", instance)
    else:
        log("update", instance)
