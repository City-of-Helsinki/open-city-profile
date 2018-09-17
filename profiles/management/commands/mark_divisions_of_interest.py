from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import translation
from profiles.models import DivisionOfInterest
from munigeo.models import AdministrativeDivision


class Command(BaseCommand):
    help = 'Mark divisions of interest'

    def handle(self, *args, **options):
        translation.activate(settings.LANGUAGES[0][0])
        divisions = AdministrativeDivision.objects.filter(type__type__in=('neighborhood', 'sub_district'))\
            .select_related('type')

        n_list = [div for div in divisions if div.type.type == 'neighborhood']
        sd_list = [div for div in divisions if div.type.type == 'sub_district']
        n_names = {x.name for x in n_list if x.type.type == 'neighborhood'}
        sd_names = {x.name for x in sd_list if x.type.type == 'sub_district'}

        # Select all neighborhoods and those sub districts that are not one-to-one
        # mapped to a neighborhood (which in this case means they have a unique name)
        common_names = n_names.intersection(sd_names)
        selected_divs = n_list + [div for div in sd_list if div.name not in common_names]

        print("Marking the following administrative divisions:")
        for div in sorted(selected_divs, key=lambda x: x.name):
            print("\t%s (%s)" % (div.name, div.type.type))

        DivisionOfInterest.objects.all().delete()
        doi_objs = [DivisionOfInterest(division=div) for div in selected_divs]
        DivisionOfInterest.objects.bulk_create(doi_objs)
