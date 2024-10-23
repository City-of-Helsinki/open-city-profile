import random

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group
from django.db import transaction
from django.utils.timezone import get_current_timezone, make_aware
from guardian.shortcuts import assign_perm

from profiles.enums import AddressType, EmailType, PhoneType
from profiles.models import Address, Email, Phone, Profile
from services.models import AllowedDataField, Service, ServiceConnection
from users.models import User

SERVICES = [
    {
        "name": "berth",
        "translations": {
            "en": {
                "title": "Boat berths",
                "description": "Boat berths in Helsinki city boat harbours.",
            },
            "fi": {
                "title": "Venepaikka",
                "description": "Venepaikat helsingin kaupungin venesatamissa.",
            },
            "sv": {
                "title": "Båtplatser",
                "description": "Båtplatser i Helsingfors båthamnar.",
            },
        },
        "allowed_data_fields": ["name", "email", "address", "phone", "ssn"],
    },
    {
        "name": "youth_membership",
        "translations": {
            "en": {
                "title": "Youth service membership",
                "description": "With youth service membership you get to participate in all activities "  # noqa: E501
                "offered by Helsinki city community centers.",
            },
            "fi": {
                "title": "Nuorisopalveluiden jäsenkortti",
                "description": "Nuorisopalveluiden Jäsenkortilla pääset mukaan nuorisotalojen toimintaan. "  # noqa: E501
                "Saat etuja kaupungin kulttuuritapahtumissa ja paikoissa.",
            },
            "sv": {
                "title": "Ungdomstjänstmedlemskap",
                "description": "Med medlemskap i ungdomstjänsten får du delta i alla aktiviteter som "  # noqa: E501
                "erbjuds av Helsingfors ungdomscenter.",
            },
        },
        "allowed_data_fields": ["name", "email", "address", "phone"],
    },
    {
        "name": "godchildren_of_culture",
        "translations": {
            "en": {
                "title": "Culture Kids",
                "description": "Culture kids -service provides free cultural experiences for children "  # noqa: E501
                "born in Helsinki in 2020.",
            },
            "fi": {
                "title": "Kulttuurin kummilapset",
                "description": "Kulttuurin kummilapset -palvelu tarjoaa ilmaisia kulttuurielämyksiä "  # noqa: E501
                "vuodesta 2020 alkaen Helsingissä syntyville lapsille.",
            },
            "sv": {
                "title": "Kulturens fadderbarn",
                "description": "Kulturens fadderbarn - tjänsten ger gratis kulturupplevelser för barn "  # noqa: E501
                "födda i Helsingfors 2020.",
            },
        },
        "allowed_data_fields": ["name", "email", "address", "phone"],
    },
    {
        "name": "hki_my_data",
        "allowed_data_fields": ["name", "email", "address", "phone"],
    },
]


@transaction.atomic
def generate_services():
    """Create services unless they already exist.

    Also assigns allowed data fields for each created service.
    """
    services = []
    for service_spec in SERVICES:
        service_name = service_spec["name"]
        try:
            service = Service.objects.get(name=service_name)
        except Service.DoesNotExist:
            service = Service(name=service_name, title=service_name)
            for language, translations in service_spec.get("translations", {}).items():
                service.set_current_language(language)
                for field, text in translations.items():
                    setattr(service, field, text)
            service.save()

            allowed_data_fields = service_spec.get("allowed_data_fields", [])
            for field in AllowedDataField.objects.filter(
                field_name__in=allowed_data_fields
            ):
                service.allowed_data_fields.add(field)
        services.append(service)
    return services


@transaction.atomic
def generate_groups_for_services(services=tuple()):
    """Create groups for given services unless they already exist."""
    groups = []
    for service in services:
        group, created = Group.objects.get_or_create(name=service.name)
        groups.append(group)
    return groups


def assign_permissions(groups=tuple()):
    """Assigns all service permissions for a group for development purposes.

    Assumes that a Service exists with the same group name.
    """
    available_permissions = [item[0] for item in Service._meta.permissions]
    for group in groups:
        service = Service.objects.get(name=group.name)
        if service:
            for permission in available_permissions:
                assign_perm(permission, group, service)


def create_user(username="", faker=None):
    """Creates a fake user for development purposes."""

    def get_random_username():
        while True:
            name = faker.user_name()
            if not User.objects.filter(username=name).exists():
                return name

    if username:
        existing = User.objects.filter(username=username)
        if existing.exists():
            return existing.get()

    return User.objects.create(
        first_name=faker.first_name(),
        last_name=faker.last_name(),
        username=username if username else get_random_username(),
        email=faker.email(),
        password=make_password("password"),
        is_active=True,
        is_staff=True,
        date_joined=make_aware(
            faker.date_time_between(start_date="-10y", end_date="now"),
            get_current_timezone(),
            is_dst=False,
        ),
    )


def generate_group_admins(groups=tuple(), faker=None):
    """Creates fake development group admins for development purposes."""

    def create_user_and_add_to_group(group=None):
        user = create_user(username="{}_user".format(group.name.lower()), faker=faker)
        user.groups.add(group)
        return user

    return [create_user_and_add_to_group(group) for group in groups]


def generate_profiles(k=50, faker=None):
    """Create fake profiles and users for development purposes."""
    for _i in range(k):
        user = create_user(faker=faker)
        profile = Profile.objects.create(
            user=user,
            language=random.choice(settings.LANGUAGES)[0],
            contact_method=random.choice(settings.CONTACT_METHODS)[0],
        )
        Email.objects.create(
            profile=profile,
            primary=True,
            email_type=EmailType.NONE,
            email=faker.email(),
        )
        Phone.objects.create(
            profile=profile,
            primary=True,
            phone_type=PhoneType.NONE,
            phone=faker.phone_number(),
        )
        Address.objects.create(
            profile=profile,
            primary=True,
            address=faker.street_address(),
            city=faker.city(),
            postal_code=faker.postcode(),
            country_code=faker.country_code(),
            address_type=AddressType.NONE,
        )


def generate_service_connections():
    """Create fake service connections for development purposes."""
    profiles = Profile.objects.all()
    services = Service.objects.all()

    for profile in profiles:
        ServiceConnection.objects.create(
            profile=profile, service=random.choice(services)
        )
