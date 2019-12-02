from django.core.management.base import BaseCommand

from services.enums import ServiceType
from services.models import Service


class Command(BaseCommand):
    def handle(self, **options):
        for service_type in ServiceType:
            Service.objects.get_or_create(service_type=service_type)
