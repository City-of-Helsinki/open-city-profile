from django.core.management.base import BaseCommand

from services.consts import SERVICE_TYPES
from services.models import Service


class Command(BaseCommand):
    def handle(self, **options):
        for service_type in SERVICE_TYPES:
            Service.objects.get_or_create(service_type=service_type[0])
