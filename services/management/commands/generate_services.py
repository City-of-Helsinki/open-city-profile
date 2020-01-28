from django.core.management.base import BaseCommand

from utils.utils import generate_services


class Command(BaseCommand):
    def handle(self, **options):
        generate_services()
