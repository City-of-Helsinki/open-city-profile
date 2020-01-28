import factory
from django.core import management
from django.core.management.base import BaseCommand
from faker import Faker

from services.models import Service
from utils.utils import (
    assign_permissions,
    generate_data_fields,
    generate_group_admins,
    generate_groups_for_services,
    generate_profiles,
    generate_services,
    generate_youth_profiles,
)

available_permissions = [item[0] for item in Service._meta.permissions]


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "-p",
            "--profilecount",
            type=int,
            help="Number of profiles to be created",
            default=50,
        )
        parser.add_argument(
            "-y",
            "--youthprofilepercentage",
            type=float,
            help="Percentage of profiles to have youth profile",
            default=0.2,
        )
        parser.add_argument(
            "-l",
            "--locale",
            type=str,
            help="Locale for generated fake data",
            default="fi_FI",
        )
        parser.add_argument(
            "--nosuperuser", help="Don't add admin/admin superuser", action="store_true"
        )

    def handle(self, *args, **kwargs):
        self.stdout.write("clearing data...")
        management.call_command("flush", verbosity=0, interactive=False)
        if not kwargs["nosuperuser"]:
            management.call_command("add_admin_user")
        self.stdout.write(self.style.SUCCESS("done."))
        self.stdout.write("seeding data...")
        locale = kwargs["locale"]
        faker = Faker(locale)
        with factory.Faker.override_default_locale(locale):
            self.stdout.write("generating data fields...")
            generate_data_fields()
            self.stdout.write("generating services...")
            services = generate_services()
            self.stdout.write("generating groups...")
            groups = generate_groups_for_services(services=services)
            self.stdout.write("assigning permissions...")
            assign_permissions(groups=groups, services=services)
            self.stdout.write("generating group admins...")
            generate_group_admins(groups=groups, faker=faker)
            profile_count = kwargs["profilecount"]
            self.stdout.write("generating profiles ({})...".format(profile_count))
            generate_profiles(profile_count, faker=faker)
            self.stdout.write("generating youth profiles...")
            generate_youth_profiles(kwargs["youthprofilepercentage"], faker=faker)
        self.stdout.write(self.style.SUCCESS("done."))
