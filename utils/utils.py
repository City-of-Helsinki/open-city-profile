import random

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group
from django.db import transaction
from django.utils.timezone import get_current_timezone, make_aware
from guardian.shortcuts import assign_perm

from profiles.enums import AddressType, EmailType, PhoneType
from profiles.models import Address, Email, Phone, Profile
from services.enums import ServiceType
from services.models import AllowedDataField, Service, ServiceConnection
from users.models import User
from youths.enums import YouthLanguage
from youths.models import YouthProfile

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


@transaction.atomic
def generate_data_fields():
    """Create data fields if they don't exist."""
    for value in DATA_FIELD_VALUES:
        if not AllowedDataField.objects.filter(
            field_name=value.get("field_name")
        ).exists():
            data_field = AllowedDataField.objects.create(
                field_name=value.get("field_name")
            )
            for translation in value.get("translations"):
                data_field.set_current_language(translation["code"])
                data_field.label = translation["label"]
            data_field.save()


SERVICE_TRANSLATIONS = {
    ServiceType.BERTH: {
        "title": {"en": "Boat berths", "fi": "Venepaikka", "sv": "Båtplatser"},
        "description": {
            "en": "Boat berths in Helsinki city boat harbours.",
            "fi": "Venepaikat helsingin kaupungin venesatamissa.",
            "sv": "Båtplatser i Helsingfors båthamnar.",
        },
    },
    ServiceType.YOUTH_MEMBERSHIP: {
        "title": {
            "en": "Youth service membership",
            "fi": "Nuorisopalveluiden jäsenkortti",
            "sv": "Ungdomstjänstmedlemskap",
        },
        "description": {
            "en": (
                "With youth service membership you get to participate in all activities offered by Helsinki city "
                "community centers."
            ),
            "fi": (
                "Nuorisopalveluiden Jäsenkortilla pääset mukaan nuorisotalojen toimintaan. Saat etuja kaupungin "
                "kulttuuritapahtumissa ja paikoissa."
            ),
            "sv": (
                "Med medlemskap i ungdomstjänsten får du delta i alla aktiviteter som erbjuds av Helsingfors "
                "ungdomscenter."
            ),
        },
    },
    ServiceType.GODCHILDREN_OF_CULTURE: {
        "title": {
            "en": "Culture Kids",
            "fi": "Kulttuurin kummilapset",
            "sv": "Kulturens fadderbarn",
        },
        "description": {
            "en": "Culture kids -service provides free cultural experiences for children born in Helsinki in 2020.",
            "fi": (
                "Kulttuurin kummilapset -palvelu tarjoaa ilmaisia kulttuurielämyksiä vuodesta 2020 alkaen ",
                "Helsingissä syntyville lapsille.",
            ),
            "sv": "Kulturens fadderbarn - tjänsten ger gratis kulturupplevelser för barn födda i Helsingfors 2020.",
        },
    },
}


@transaction.atomic
def generate_services():
    """Create services unless they already exist.

    Also assigns allowed data fields for each created service.
    """
    services = []
    for service_type in ServiceType:
        service = Service.objects.filter(service_type=service_type).first()
        if not service:
            service = Service(service_type=service_type, title=service_type.name)
            if service_type in SERVICE_TRANSLATIONS:
                for language in ["fi", "en", "sv"]:
                    service.set_current_language(language)
                    service.title = SERVICE_TRANSLATIONS[service_type]["title"][
                        language
                    ]
                    service.description = SERVICE_TRANSLATIONS[service_type][
                        "description"
                    ][language]
            service.save()
            for field in AllowedDataField.objects.all():
                if (
                    field.field_name != "ssn"
                    or service.service_type == ServiceType.BERTH
                ):
                    service.allowed_data_fields.add(field)
        services.append(service)
    return services


@transaction.atomic
def generate_groups_for_services(services=tuple()):
    """Create groups for given services unless they already exist."""
    groups = []
    for service in services:
        group, created = Group.objects.get_or_create(name=service.service_type.value)
        groups.append(group)
    return groups


def assign_permissions(groups=tuple()):
    """Assigns all service permissions for a group for development purposes.

    Assumes that a Service exists with the same group name.
    """
    available_permissions = [item[0] for item in Service._meta.permissions]
    for group in groups:
        service = Service.objects.get(service_type=group.name)
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
    for i in range(k):
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


def generate_service_connections(youth_profile_percentage=0.2):
    """Create fake service connections for development purposes."""
    profiles = Profile.objects.all()
    number_of_youth_profiles_to_generate = int(
        profiles.count() * youth_profile_percentage
    )

    youth_service = Service.objects.get(service_type=ServiceType.YOUTH_MEMBERSHIP)
    other_services = Service.objects.exclude(pk=youth_service.pk)

    for index, profile in enumerate(profiles):
        if index < number_of_youth_profiles_to_generate:
            ServiceConnection.objects.create(profile=profile, service=youth_service)
        else:
            ServiceConnection.objects.create(
                profile=profile, service=random.choice(other_services)
            )


def generate_youth_profiles(faker=None):
    """Create fake youth membership profiles for development purposes."""
    profiles = Profile.objects.filter(
        service_connections__service__service_type=ServiceType.YOUTH_MEMBERSHIP
    )

    for profile in profiles:
        approved = bool(random.getrandbits(1))
        YouthProfile.objects.create(
            profile=profile,
            birth_date=make_aware(
                faker.date_time_between(start_date="-17y", end_date="-13y"),
                get_current_timezone(),
                is_dst=False,
            ),
            language_at_home=random.choice(list(YouthLanguage)),
            approver_first_name=faker.first_name() if approved else "",
            approver_last_name=profile.last_name if approved else "",
            approved_time=make_aware(
                faker.date_time_between(
                    start_date=profile.user.date_joined, end_date="now"
                ),
                get_current_timezone(),
                is_dst=False,
            )
            if approved
            else None,
            photo_usage_approved=bool(random.getrandbits(1)) if approved else False,
        )
