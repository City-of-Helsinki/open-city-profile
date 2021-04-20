import pytest
from django.contrib.auth.models import Group
from django.db.models import Count
from faker import Faker
from guardian.shortcuts import get_group_perms

from open_city_profile.tests.factories import GroupFactory
from profiles.models import Profile
from services.models import AllowedDataField, Service, ServiceConnection
from users.models import User
from utils.utils import (
    assign_permissions,
    create_user,
    DATA_FIELD_VALUES,
    generate_data_fields,
    generate_group_admins,
    generate_groups_for_services,
    generate_profiles,
    generate_service_connections,
    generate_services,
    SERVICES,
)


@pytest.mark.parametrize("times", [1, 2])
def test_generate_services(times):
    """Test services are generated and that function can be run multiple times."""
    assert Service.objects.count() == 0
    for i in range(times):
        services = generate_services()
    assert len(services) == len(SERVICES)
    assert Service.objects.count() == len(SERVICES)


@pytest.mark.parametrize("times", [1, 2])
def test_generate_group_for_service(times, service):
    """Test groups for services are generated and that function can be run multiple times."""
    services = [service]
    assert Group.objects.count() == 0
    for i in range(times):
        groups = generate_groups_for_services(services)
    assert len(groups) == len(services)
    assert Group.objects.count() == len(services)


@pytest.mark.parametrize("times", [1, 2])
def test_assign_permissions(times, user, service):
    available_permissions = [item[0] for item in Service._meta.permissions]
    # assign_permissions expects a Group and a Service exist with the same name.
    group = GroupFactory(name=service.name)
    user.groups.add(group)

    for permission in available_permissions:
        assert not user.has_perm(permission, service)
        assert permission not in get_group_perms(group, service)

    for i in range(times):
        assign_permissions([group])

    for permission in available_permissions:
        assert user.has_perm(permission, service)
        assert permission in get_group_perms(group, service)


def test_creates_random_user():
    assert User.objects.count() == 1  # anonymous user exists
    user = create_user(faker=Faker())
    assert user
    assert User.objects.count() == 2


def test_creates_defined_user():
    assert User.objects.count() == 1  # anonymous user exists
    faker = Faker()
    user = create_user(username="berth_user", faker=faker)
    assert User.objects.count() == 2
    assert user.username == "berth_user"


def test_create_user_returns_existing_user():
    username = "test_user"
    faker = Faker()
    user1 = create_user(username=username, faker=faker)
    user2 = create_user(username=username, faker=faker)
    assert user1 == user2


def test_generates_group_admins():
    group = GroupFactory(name="group_name")
    assert group.user_set.count() == 0
    generate_group_admins([group], faker=Faker())
    assert group.user_set.count() == 1


def test_generates_profiles():
    assert Profile.objects.count() == 0
    generate_profiles(k=10, faker=Faker())
    assert Profile.objects.count() == 10


def test_generates_default_amount_of_profiles():
    assert Profile.objects.count() == 0
    generate_profiles(faker=Faker())
    assert Profile.objects.count() == 50


@pytest.mark.parametrize("profiles", [5, 10, 0])
def test_generate_service_connections(profiles):
    """Service connection is generated for all profiles,"""
    generate_services()
    generate_profiles(k=profiles, faker=Faker())

    generate_service_connections()

    assert ServiceConnection.objects.count() == profiles
    assert (
        Profile.objects.annotate(Count("service_connections"))
        .filter(service_connections__count=1)
        .count()
        == profiles
    )


@pytest.mark.parametrize("times", [1, 2])
def test_generate_data_fields(times):
    """Test data fields are generated and that function can be run multiple times."""
    assert AllowedDataField.objects.count() == 0
    for i in range(times):
        generate_data_fields()
    allowed_data_fields = AllowedDataField.objects.all()
    assert len(allowed_data_fields) == 5

    for value in DATA_FIELD_VALUES:
        field = allowed_data_fields.filter(field_name=value["field_name"]).first()
        assert field is not None
        for translation in value["translations"]:
            field.set_current_language(translation["code"])
            assert field.label == translation["label"]
