from django.db.models.signals import post_delete, post_init, post_save
from django.dispatch import receiver

from .audit_log import add_loggable


@receiver(post_delete)
def post_delete_audit_log(sender, instance, **kwargs):
    add_loggable("DELETE", instance)


@receiver(post_init)
def post_init_audit_log(sender, instance, **kwargs):
    add_loggable("READ", instance)


@receiver(post_save)
def post_save_audit_log(sender, instance, created, **kwargs):
    if created:
        add_loggable("CREATE", instance)
    else:
        add_loggable("UPDATE", instance)
