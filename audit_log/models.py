from django.db import models


class LogEntry(models.Model):
    id = models.BigAutoField(primary_key=True)
    timestamp = models.DateTimeField(db_index=True)
    service_name = models.CharField(max_length=1024, blank=True)
    client_id = models.CharField(max_length=1024, blank=True)
    ip_address = models.CharField(max_length=128, blank=True)
    actor_user_id = models.UUIDField(null=True)
    actor_role = models.CharField(max_length=1024, blank=True)
    target_user_id = models.UUIDField(null=True)
    target_profile_id = models.UUIDField(null=True)
    target_type = models.CharField(max_length=1024, blank=True)
    operation = models.CharField(max_length=1024, blank=True)
