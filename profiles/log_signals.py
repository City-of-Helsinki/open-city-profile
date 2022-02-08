from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .audit_log import log


@receiver(post_delete)
def post_delete_audit_log(sender, instance, **kwargs):
    log("DELETE", instance)


@receiver(post_save)
def post_save_audit_log(sender, instance, created, **kwargs):
    if created:
        log("CREATE", instance)
    else:
        log("UPDATE", instance)
