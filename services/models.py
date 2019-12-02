from django.db import models
from enumfields import EnumField

from profiles.models import Profile

from .enums import ServiceType


class Service(models.Model):
    service_type = EnumField(ServiceType, max_length=32, blank=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        permissions = (
            ("can_manage_profiles", "Can manage profiles"),
            ("can_view_profiles", "Can view profiles"),
        )

    def __str__(self):
        return self.service_type.name


class ServiceConnection(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    enabled = models.BooleanField(default=True)

    class Meta:
        unique_together = ("profile", "service")

    def __str__(self):
        return "{} {} - {}".format(
            self.profile.first_name, self.profile.last_name, self.service
        )
