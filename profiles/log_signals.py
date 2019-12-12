from django.db.models.signals import post_save, post_delete, post_init
from django.dispatch import receiver
import threading
import logging
from .utils import get_current_user


def should_audit(model):
    excludeModels = ['User' , 'ContentType', 'Session', 'Version', 'Revision']
    if model in excludeModels:
        return False
    return True


@receiver(post_delete)
def post_save_audit_log(sender, instance, **kwargs):
    if should_audit(instance.__class__.__name__):
        logger = logging.getLogger("django")
        logger.info(
            "User %s changed %s with id %d"
            % (get_current_user(), instance.__class__.__name__, instance.id)  # What should we write to log????
        )


@receiver(post_init)
def post_init_audit_log(sender, instance, **kwargs):
    if should_audit(instance.__class__.__name__):
        logger = logging.getLogger("django")
        logger.info(
            "User %s accessed %s with id %d"
            % (get_current_user(), instance.__class__.__name__, instance.id)  # What should we write to log????
        )

@receiver(post_save)
def post_save_audit_log(sender, instance, **kwargs):
    if should_audit(instance.__class__.__name__):
        logger = logging.getLogger("django")
        logger.info(
            "User %s changed %s with id %d"
            % (get_current_user(), instance.__class__.__name__, instance.id)  # What should we write to log????
        )
