from django.db.models.signals import post_init, post_save, pre_delete
from django.dispatch import receiver

from .audit_log import log


@receiver(pre_delete)
def pre_delete_audit_log(sender, instance, **kwargs):
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
