import random

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group
from django.utils.timezone import get_current_timezone, make_aware
from guardian.shortcuts import assign_perm

from profiles.consts import ADDRESS_TYPES, EMAIL_TYPES, PHONE_TYPES
from profiles.models import Address, Email, Phone, Profile
from services.consts import SERVICE_TYPES
from services.models import Service, ServiceConnection
from users.models import User
from youths.consts import LANGUAGES
from youths.models import YouthProfile


def generate_services():
    return Service.objects.bulk_create(
        [Service(service_type=service_type[0]) for service_type in SERVICE_TYPES]
    )


def generate_groups_for_services(services=[]):
    return Group.objects.bulk_create(
        [Group(name=service.service_type) for service in services]
    )


def assign_permissions(groups=[], services=[]):
    available_permissions = [item[0] for item in Service._meta.permissions]
    for group in groups:
        service = next(
            service for service in services if service.service_type == group.name
        )
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
            email_type=EMAIL_TYPES[0][0],
            email=faker.email(),
        )
        Phone.objects.create(
            profile=profile,
            primary=True,
            phone_type=PHONE_TYPES[0][0],
            phone=faker.phone_number(),
        )
        Address.objects.create(
            profile=profile,
            primary=True,
            address=faker.street_address(),
            city=faker.city(),
            postal_code=faker.postcode(),
            country_code=faker.country_code(),
            address_type=ADDRESS_TYPES[0][0],
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
                faker.date_time_between(start_date="-17y", end_date="now"),
                get_current_timezone(),
                is_dst=False,
            ),
            language_at_home=random.choice(LANGUAGES)[0],
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
