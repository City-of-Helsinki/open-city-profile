import json
import sys

from django.core.management.base import BaseCommand

from services.utils import generate_data_fields


class Command(BaseCommand):
    help = "Configures AllowedDataFields as given by a specification."

    def handle(self, *args, **kwargs):
        try:
            data = sys.stdin.read()
        except KeyboardInterrupt:
            return

        fields_spec = json.loads(data)
        generate_data_fields(fields_spec)
