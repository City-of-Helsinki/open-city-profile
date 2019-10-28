from django.db import models

from profiles.models import Profile

from .consts import SERVICE_TYPES


class Service(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    service_type = models.CharField(max_length=32, choices=SERVICE_TYPES, blank=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "{} {} - {}".format(
            self.profile.first_name, self.profile.last_name, self.service_type
        )
