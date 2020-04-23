from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from youths.models import YouthProfile


@receiver(post_save, sender=YouthProfile)
def generate_membership_number(sender, instance, created, **kwargs):
    """Generate a membership number for a youth profile.

    Membership number is only generated for a new profile or a profile
    missing a membership number.
    """
    if created or not instance.membership_number:
        membership_number = str(instance.pk).zfill(
            settings.YOUTH_MEMBERSHIP_NUMBER_LENGTH
        )
        instance.membership_number = membership_number
        sender.objects.filter(pk=instance.pk).update(
            membership_number=membership_number
        )
