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
    generate_service_connections,
    generate_services,
)

available_permissions = [item[0] for item in Service._meta.permissions]


DATA_FIELD_VALUES = [
    {
        "field_name": "name",
        "translations": [
            {"code": "en", "label": "Name"},
            {"code": "fi", "label": "Nimi"},
            {"code": "sv", "label": "Namn"},
        ],
    },
    {
        "field_name": "email",
        "translations": [
            {"code": "en", "label": "Email"},
            {"code": "fi", "label": "Sähköposti"},
            {"code": "sv", "label": "Epost"},
        ],
    },
    {
        "field_name": "address",
        "translations": [
            {"code": "en", "label": "Address"},
            {"code": "fi", "label": "Osoite"},
            {"code": "sv", "label": "Adress"},
        ],
    },
    {
        "field_name": "phone",
        "translations": [
            {"code": "en", "label": "Phone"},
            {"code": "fi", "label": "Puhelinnumero"},
            {"code": "sv", "label": "Telefonnummer"},
        ],
    },
    {
        "field_name": "ssn",
        "translations": [
            {"code": "en", "label": "Social Security Number"},
            {"code": "fi", "label": "Henkilötunnus"},
            {"code": "sv", "label": "Personnnumer"},
        ],
    },
]


class Command(BaseCommand):
    help = "Seed environment with development data"

    def add_arguments(self, parser):
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
            "-l",
            "--locale",
            type=str,
            help="Locale for generated fake data",
            default="fi_FI",
        )
        parser.add_argument(
            "--superuser", help="Add admin/admin superuser", action="store_true"
        )

    def handle(self, *args, **kwargs):
        no_clear = kwargs["no_clear"]
        superuser = kwargs["superuser"]
        locale = kwargs["locale"]
        faker = Faker(locale)
        profile_count = kwargs["profilecount"]

        if not no_clear:
            self.stdout.write("Clearing data...")
            management.call_command("flush", verbosity=0, interactive=False)
            self.stdout.write(self.style.SUCCESS("Done - Data cleared"))

        self.stdout.write("Creating/updating initial data")

        if superuser:
            self.stdout.write("Adding admin user...")
            management.call_command("add_admin_user")
            self.stdout.write(self.style.SUCCESS("Done - Admin user"))

        self.stdout.write("Generating data fields...")
        generate_data_fields(DATA_FIELD_VALUES)
        self.stdout.write("Generating services...")
        services = generate_services()
        self.stdout.write("Generating groups...")
        groups = generate_groups_for_services(services=services)

        self.stdout.write(self.style.SUCCESS("Done - Profile data"))

        self.stdout.write("Assigning group permissions for services...")
        assign_permissions(groups=groups)

        with factory.Faker.override_default_locale(locale):
            self.stdout.write("Generating group admins...")
            generate_group_admins(groups=groups, faker=faker)
            self.stdout.write(f"Generating profiles ({profile_count})...")
            generate_profiles(profile_count, faker=faker)
            self.stdout.write("Generating service connections...")
            generate_service_connections()

        self.stdout.write(self.style.SUCCESS("Done - Development fake data"))
