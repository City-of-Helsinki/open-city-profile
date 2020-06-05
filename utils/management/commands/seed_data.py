import factory
from django.core import management
from django.core.management.base import BaseCommand
from faker import Faker

from services.models import Service
from subscriptions.utils import generate_subscription_types
from utils.utils import (
    assign_permissions,
    generate_data_fields,
    generate_group_admins,
    generate_groups_for_services,
    generate_notifications,
    generate_profiles,
    generate_service_connections,
    generate_services,
    generate_youth_profiles,
)

available_permissions = [item[0] for item in Service._meta.permissions]


class Command(BaseCommand):
    help = "Seed environment with initial data"

    def add_arguments(self, parser):
        parser.add_argument(
            "-d",
            "--development",
            help="Add randomized development data, implies --clear",
            action="store_true",
        )
        parser.add_argument(
            "-c",
            "--clear",
            help="Flush the DB before initializing the data",
            action="store_true",
        )
        parser.add_argument(
            "--no-clear",
            help="Don't flush the DB before initializing the data",
            action="store_true",
        )
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
            "--superuser", help="Add admin/admin superuser", action="store_true"
        )
        parser.add_argument(
            "--divisions",
            help="Import Helsinki divisions of interest",
            action="store_true",
        )

    def handle(self, *args, **kwargs):
        clear = kwargs["clear"]
        no_clear = kwargs["no_clear"]
        development = kwargs["development"]
        superuser = kwargs["superuser"]
        divisions = kwargs["divisions"]
        locale = kwargs["locale"]
        faker = Faker(locale)
        profile_count = kwargs["profilecount"]
        youth_profile_percentage = kwargs["youthprofilepercentage"]

        if not no_clear and (development or clear):
            self.stdout.write("Clearing data...")
            management.call_command("flush", verbosity=0, interactive=False)
            self.stdout.write(self.style.SUCCESS("Done - Data cleared"))

        self.stdout.write("Creating/updating initial data")

        if superuser:
            self.stdout.write("Adding admin user...")
            management.call_command("add_admin_user")
            self.stdout.write(self.style.SUCCESS("Done - Admin user"))

        if divisions:
            self.stdout.write("Importing Helsinki divisions of interest...")
            management.call_command("geo_import", "finland", "--municipalities")
            management.call_command("geo_import", "helsinki", "--divisions")
            management.call_command("mark_divisions_of_interest")
            self.stdout.write(
                self.style.SUCCESS("Done - Helsinki divisions of interest")
            )

        # Initial profile data
        self.stdout.write("Generating data fields...")
        generate_data_fields()
        self.stdout.write("Generating services...")
        services = generate_services()
        self.stdout.write("Generating groups...")
        groups = generate_groups_for_services(services=services)
        self.stdout.write("Generating subscription types...")
        generate_subscription_types()

        self.stdout.write(self.style.SUCCESS("Done - Profile data"))

        # Initial youth profile data
        self.stdout.write("Generating youth membership notifications...")
        generate_notifications()

        self.stdout.write(self.style.SUCCESS("Done - Youth Profile data"))

        # Development
        if development:
            self.stdout.write("Assigning group permissions for services...")
            assign_permissions(groups=groups)

            with factory.Faker.override_default_locale(locale):
                self.stdout.write("Generating group admins...")
                generate_group_admins(groups=groups, faker=faker)
                self.stdout.write(f"Generating profiles ({profile_count})...")
                generate_profiles(profile_count, faker=faker)
                self.stdout.write("Generating service connections...")
                generate_service_connections(youth_profile_percentage)
                self.stdout.write("Generating youth profiles...")
                generate_youth_profiles(faker=faker)

            self.stdout.write(self.style.SUCCESS("Done - Development fake data"))
