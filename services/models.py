from django.db import models

from profiles.models import Profile

from .consts import SERVICE_TYPES


class Service(models.Model):
    service_type = models.CharField(
        max_length=32, choices=SERVICE_TYPES, blank=False, unique=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.service_type


class ServiceConnection(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.PROTECT)
    service = models.ForeignKey(Service, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    enabled = models.BooleanField(default=True)

    class Meta:
        unique_together = ("profile", "service")

    def __str__(self):
        return "{} {} - {}".format(
            self.profile.first_name, self.profile.last_name, self.service.service_type
        )
