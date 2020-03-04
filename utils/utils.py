import random

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group
from django.utils.timezone import get_current_timezone, make_aware
from django_ilmoitin.models import NotificationTemplate
from guardian.shortcuts import assign_perm

from profiles.enums import AddressType, EmailType, PhoneType
from profiles.models import Address, Email, Phone, Profile
from services.enums import ServiceType
from services.models import AllowedDataField, Service, ServiceConnection
from users.models import User
from youths.enums import NotificationType, YouthLanguage
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


def generate_data_fields():
    for value in DATA_FIELD_VALUES:
        data_field = AllowedDataField.objects.create(field_name=value.get("field_name"))
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


def generate_services():
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


def generate_groups_for_services(services=[]):
    return Group.objects.bulk_create(
        [Group(name=service.service_type.value) for service in services]
    )


def assign_permissions(groups=[], services=[]):
    available_permissions = [item[0] for item in Service._meta.permissions]
    for group in groups:
        service = Service.objects.get(service_type=group.name)
        if service:
            for permission in available_permissions:
                assign_perm(permission, group, service)


def create_user(username="", faker=None):
    def get_random_username():
        while True:
            name = faker.user_name()
            if not User.objects.filter(username=name).exists():
                return name

    return User(
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


def generate_group_admins(groups=[], faker=None):
    def create_user_and_add_to_group(group=None):
        user = create_user(username="{}_user".format(group.name.lower()), faker=faker)
        user.save()
        user.groups.add(group)
        return user

    return [create_user_and_add_to_group(group) for group in groups]


def generate_profiles(k=50, faker=None):
    for i in range(k):
        user = create_user(faker=faker)
        user.save()
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
        services = Service.objects.all()
        if services.exists():
            ServiceConnection.objects.create(
                profile=profile, service=random.choice(services)
            )


def generate_youth_profiles(percentage=0.2, faker=None):
    profiles = Profile.objects.all()
    youth_profile_profiles = profiles.order_by("?")[: int(len(profiles) * percentage)]
    for profile in youth_profile_profiles:
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


def generate_notifications():
    template = NotificationTemplate(
        type=NotificationType.YOUTH_PROFILE_CONFIRMATION_NEEDED.value
    )
    fi_subject = "Vahvista nuorisojäsenyys"
    fi_html = (
        "Hei {{ youth_profile.approver_first_name }},<br /><br />{{ youth_profile.profile.first_name }} on "
        "pyytänyt sinua vahvistamaan nuorisojäsenyytensä. Käy antamassa vahvistus Jässäri-palvelussa käyttäen tätä "
        'linkkiä:<br /><br /><a href="https://jassari.test.kuva.hel.ninja/approve/{{ youth_profile.approval_token }}">'
        "https://jassari.test.kuva.hel.ninja/approve/{{ youth_profile.approval_token }}</a><br /><br /><i>Tämä viesti "
        "on lähetetty järjestelmistä automaattisesti. Älä vastaa tähän viestiin, sillä vastauksia ei käsitellä.</i>"
    )
    fi_text = (
        "Hei {{ youth_profile.approver_first_name }},\r\n\r\n{{ youth_profile.profile.first_name }} on pyytänyt sinua "
        "vahvistamaan nuorisojäsenyytensä. Käy antamassa vahvistus Jässäri-palvelussa käyttäen tätä linkkiä:\r\n\r\n"
        "https://jassari.test.kuva.hel.ninja/approve/{{ youth_profile.approval_token }}\r\n\r\nTämä viesti on "
        "lähetetty järjestelmistä automaattisesti. Älä vastaa tähän viestiin, sillä vastauksia ei käsitellä."
    )
    template.set_current_language("fi")
    template.subject = fi_subject
    template.body_html = fi_html
    template.body_text = fi_text
    template.set_current_language("sv")
    template.subject = fi_subject + " SV TRANSLATION NEEDED"
    template.body_html = fi_html + "<p>SV TRANSLATION NEEDED</p>"
    template.body_text = fi_text + "<p>SV TRANSLATION NEEDED</p>"
    template.set_current_language("en")
    template.subject = fi_subject + " EN TRANSLATION NEEDED"
    template.body_html = fi_html + "<p>EN TRANSLATION NEEDED</p>"
    template.body_text = fi_text + "<p>EN TRANSLATION NEEDED</p>"
    template.save()

    template = NotificationTemplate(type=NotificationType.YOUTH_PROFILE_CONFIRMED.value)
    fi_subject = "Nuorisojäsenyys vahvistettu"
    fi_html = (
        "Hei {{ youth_profile.profile.first_name }},\r\n<br /><br />\r\n{{ youth_profile.approver_first_name }} "
        "on vahvistanut nuorisojäsenyytesi. Kirjaudu Jässäri-palveluun nähdäksesi omat tietosi:\r\n<br /><br />\r\n"
        '<a href="https://jassari.test.kuva.hel.ninja">https://jassari.test.kuva.hel.ninja</a>\r\n<br /><br />\r\n<i>'
        "Tämä viesti on lähetetty järjestelmästä automaattisesti. Älä vastaa tähän viestiin, sillä vastauksia ei "
        "käsitellä.</i>"
    )
    fi_text = (
        "Hei {{ youth_profile.profile.first_name }},\r\n\r\n{{ youth_profile.approver_first_name }} on vahvistanut "
        "nuorisojäsenyytesi. Kirjaudu Jässäri-palveluun nähdäksesi omat tietosi:\r\n\r\nhttps://jassari.test.kuva.h"
        "el.ninja\r\n\r\nTämä viesti on lähetetty järjestelmästä automaattisesti. Älä vastaa tähän viestiin, sillä "
        "vastauksia ei käsitellä."
    )
    template.set_current_language("fi")
    template.subject = fi_subject
    template.body_html = fi_html
    template.body_text = fi_text
    template.set_current_language("sv")
    template.subject = fi_subject + " SV TRANSLATION NEEDED"
    template.body_html = fi_html + "<p>SV TRANSLATION NEEDED</p>"
    template.body_text = fi_text + "<p>SV TRANSLATION NEEDED</p>"
    template.set_current_language("en")
    template.subject = fi_subject + " EN TRANSLATION NEEDED"
    template.body_html = fi_html + "<p>EN TRANSLATION NEEDED</p>"
    template.body_text = fi_text + "<p>EN TRANSLATION NEEDED</p>"
    template.save()
