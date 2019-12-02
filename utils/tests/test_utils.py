from django.contrib.auth.models import Group
from faker import Faker

from open_city_profile.tests.factories import GroupFactory, UserFactory
from profiles.models import Profile
from services.enums import ServiceType
from services.models import Service
from services.tests.factories import ServiceFactory
from users.models import User
from utils.utils import (
    assign_permissions,
    create_user,
    generate_group_admins,
    generate_groups_for_services,
    generate_profiles,
    generate_services,
    generate_youth_profiles,
)
from youths.models import YouthProfile


def test_generates_services():
    assert Service.objects.count() == 0
    services = generate_services()
    assert len(services) == len(ServiceType)
    assert Service.objects.count() == len(ServiceType)


def test_generates_group_for_service():
    services = [ServiceFactory()]
    assert Group.objects.count() == 0
    groups = generate_groups_for_services(services)
    assert len(groups) == len(services)
    assert Group.objects.count() == len(services)


def test_assigns_permissions():
    available_permissions = [item[0] for item in Service._meta.permissions]
    service = ServiceFactory()
    group = GroupFactory(name=service.service_type)
    user = UserFactory()
    user.groups.add(group)
    for permission in available_permissions:
        assert not user.has_perm(permission, service)
    assign_permissions([group], [service])
    for permission in available_permissions:
        assert user.has_perm(permission, service)


def test_creates_random_user():
    assert User.objects.count() == 1  # anonymous user exists
    user = create_user(faker=Faker())
    assert user
    assert User.objects.count() == 1
    user.save()
    assert User.objects.count() == 2


def test_creates_defined_user():
    assert User.objects.count() == 1  # anonymous user exists
    faker = Faker()
    user = create_user(username="berth_user", faker=faker)
    user.save()
    assert User.objects.count() == 2
    assert user.username == "berth_user"


def test_generates_group_admins():
    group = GroupFactory(name=ServiceType.BERTH.value)
    assert group.user_set.count() == 0
    generate_group_admins([group], faker=Faker())
    assert group.user_set.count() == 1


def test_generates_profiles():
    ServiceFactory()
    assert Profile.objects.count() == 0
    generate_profiles(k=10, faker=Faker())
    assert Profile.objects.count() == 10


def test_generates_default_amount_of_profiles():
    ServiceFactory()
    assert Profile.objects.count() == 0
    generate_profiles(faker=Faker())
    assert Profile.objects.count() == 50


def test_generates_profiles_without_any_services():
    assert Profile.objects.count() == 0
    generate_profiles(k=1, faker=Faker())
    assert Profile.objects.count() == 1


def test_generates_youth_profiles():
    generate_profiles(k=10, faker=Faker())
    assert Profile.objects.count() == 10
    assert YouthProfile.objects.count() == 0
    generate_youth_profiles(0.2, faker=Faker())
    assert YouthProfile.objects.count() == 2


def test_cant_generate_youth_profiles_without_profiles():
    assert Profile.objects.count() == 0
    assert YouthProfile.objects.count() == 0
    generate_youth_profiles(1, faker=Faker())
    assert YouthProfile.objects.count() == 0
