import logging

from django.conf import settings
from django.db.models.signals import post_delete, post_init, post_save
from django.dispatch import receiver

from .utils import get_current_service, get_current_user


def should_audit(model):
    if hasattr(model, "audit_log") and model.audit_log:
        return True
    return False


def log(action, instance):
    if settings.AUDIT_LOGGING_ENABLED and should_audit(instance.__class__):
        logger = logging.getLogger("audit")
        # TODO: Finalize log format
        logger.info(
            "User %s from service %s %s %s with id %s"
            % (
                get_current_user() or "SYSTEM",
                get_current_service() or "NONE",
                action,
                instance.__class__.__name__,
                str(instance.id),
            )
        )


@receiver(post_delete)
def post_delete_audit_log(sender, instance, **kwargs):
    log("deleted", instance)


@receiver(post_init)
def post_init_audit_log(sender, instance, **kwargs):
    log("accessed", instance)


@receiver(post_save)
def post_save_audit_log(sender, instance, created, **kwargs):
    if created:
        log("created", instance)
    else:
        log("changed", instance)
