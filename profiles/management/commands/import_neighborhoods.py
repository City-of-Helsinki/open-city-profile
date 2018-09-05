from django.core.management.base import BaseCommand

from profiles.importers.hel_neighborhoods import HelsinkiNeighborhoodsImporter


class Command(BaseCommand):
    help = "Import Helsinki neighborhoods"

    def handle(self, *args, **options):
        importer = HelsinkiNeighborhoodsImporter(options)
        importer.import_neighborhoods()
