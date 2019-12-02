from io import StringIO

import pytest
from django.core.management import call_command
from guardian.shortcuts import assign_perm

from open_city_profile.tests.factories import GroupFactory, UserFactory
from services.enums import ServiceType
from services.models import Service

from .factories import ServiceFactory


def test_command_generate_services_adds_all_services():
    assert Service.objects.count() == 0
    call_command("generate_services")
    assert Service.objects.count() == len(ServiceType)


def test_command_generate_services_adds_only_missing_services():
    ServiceFactory()
    assert Service.objects.count() == 1
    call_command("generate_services")
    assert Service.objects.count() == len(ServiceType)


def test_command_add_object_permissions_with_correct_arguments_output():
    user = UserFactory()
    group = GroupFactory(name="{}Admin".format(ServiceType.BERTH.name.capitalize()))
    user.groups.add(group)
    service = ServiceFactory()
    assert not user.has_perm("can_view_profiles", service)
    assert not user.has_perm("can_manage_profiles", service)
    out = StringIO()
    args = [
        ServiceType.BERTH.name,
        "{}Admin".format(ServiceType.BERTH.name.capitalize()),
        "can_view_profiles",
    ]
    call_command("add_object_permission", *args, stdout=out)
    args = [
        ServiceType.BERTH.name,
        "{}Admin".format(ServiceType.BERTH.name.capitalize()),
        "can_manage_profiles",
    ]
    call_command("add_object_permission", *args, stdout=out)
    assert (
        "Permission can_view_profiles added for {0}Admin on service {0}".format(
            ServiceType.BERTH.name.capitalize()
        )
        in out.getvalue()
    )
    assert (
        "Permission can_manage_profiles added for {0}Admin on service {0}".format(
            ServiceType.BERTH.name.capitalize()
        )
        in out.getvalue()
    )
    assert user.has_perm("can_view_profiles", service)
    assert user.has_perm("can_manage_profiles", service)


def test_command_add_object_permissions_throws_error_when_invalid_permission_given():
    user = UserFactory()
    group = GroupFactory(name="{}Admin".format(ServiceType.BERTH.name.capitalize()))
    user.groups.add(group)
    service = ServiceFactory()
    out = StringIO()
    args = [
        ServiceType.BERTH.name,
        "{}Admin".format(ServiceType.BERTH.name.capitalize()),
        "can_manage_profiles_invalid",
    ]
    call_command("add_object_permission", *args, stdout=out)
    assert "Invalid permission given" in out.getvalue()
    assert not user.has_perm("can_manage_profiles_invalid", service)


def test_command_add_object_permissions_throws_error_when_invalid_group_name_given():
    user = UserFactory()
    group = GroupFactory(name="{}Admin".format(ServiceType.BERTH.name.capitalize()))
    user.groups.add(group)
    service = ServiceFactory()
    out = StringIO()
    args = [
        ServiceType.BERTH.name,
        "{}AdminInvalid".format(ServiceType.BERTH.name.capitalize()),
        "can_manage_profiles",
    ]
    call_command("add_object_permission", *args, stdout=out)
    assert "Invalid group_name given" in out.getvalue()
    assert not user.has_perm("can_manage_profiles", service)


def test_command_add_object_permissions_throws_error_when_invalid_service_type_given():
    user = UserFactory()
    group = GroupFactory(name="{}Admin".format(ServiceType.BERTH.name.capitalize()))
    user.groups.add(group)
    service = ServiceFactory()
    out = StringIO()
    args = [
        "BERTH_INVALID",
        "{}Admin".format(ServiceType.BERTH.name.capitalize()),
        "can_manage_profiles",
    ]
    with pytest.raises(KeyError):
        call_command("add_object_permission", *args, stdout=out)
    assert not user.has_perm("can_manage_profiles", service)


def test_command_remove_object_permissions_with_correct_arguments_output():
    user = UserFactory()
    group = GroupFactory(name="{}Admin".format(ServiceType.BERTH.name.capitalize()))
    user.groups.add(group)
    service = ServiceFactory()
    assign_perm("can_view_profiles", group, service)
    assign_perm("can_manage_profiles", group, service)
    assert user.has_perm("can_view_profiles", service)
    assert user.has_perm("can_manage_profiles", service)
    out = StringIO()
    args = [
        ServiceType.BERTH.name,
        "{}Admin".format(ServiceType.BERTH.name.capitalize()),
        "can_view_profiles",
    ]
    call_command("remove_object_permission", *args, stdout=out)
    args = [
        ServiceType.BERTH.name,
        "{}Admin".format(ServiceType.BERTH.name.capitalize()),
        "can_manage_profiles",
    ]
    call_command("remove_object_permission", *args, stdout=out)
    assert (
        "Permission can_view_profiles removed for {0}Admin on service {0}".format(
            ServiceType.BERTH.name.capitalize()
        )
        in out.getvalue()
    )
    assert (
        "Permission can_manage_profiles removed for {0}Admin on service {0}".format(
            ServiceType.BERTH.name.capitalize()
        )
        in out.getvalue()
    )
    assert not user.has_perm("can_view_profiles", service)
    assert not user.has_perm("can_manage_profiles", service)


def test_command_remove_object_permissions_throws_error_when_invalid_permission_given():
    user = UserFactory()
    group = GroupFactory(name="{}Admin".format(ServiceType.BERTH.name.capitalize()))
    user.groups.add(group)
    service = ServiceFactory()
    assign_perm("can_manage_profiles", group, service)
    assert user.has_perm("can_manage_profiles", service)
    out = StringIO()
    args = [
        ServiceType.BERTH.name,
        "{}Admin".format(ServiceType.BERTH.name.capitalize()),
        "can_manage_profiles_invalid",
    ]
    call_command("remove_object_permission", *args, stdout=out)
    assert "Invalid permission given" in out.getvalue()
    assert user.has_perm("can_manage_profiles", service)


def test_command_remove_object_permissions_throws_error_when_invalid_group_name_given():
    user = UserFactory()
    group = GroupFactory(name="{}Admin".format(ServiceType.BERTH.name.capitalize()))
    user.groups.add(group)
    service = ServiceFactory()
    assign_perm("can_manage_profiles", group, service)
    assert user.has_perm("can_manage_profiles", service)
    out = StringIO()
    args = [
        ServiceType.BERTH.name,
        "{}AdminInvalid".format(ServiceType.BERTH.name.capitalize()),
        "can_manage_profiles",
    ]
    call_command("remove_object_permission", *args, stdout=out)
    assert "Invalid group_name given" in out.getvalue()
    assert user.has_perm("can_manage_profiles", service)


def test_command_remove_object_permissions_throws_error_when_invalid_service_type_given():
    user = UserFactory()
    group = GroupFactory(name="{}Admin".format(ServiceType.BERTH.name.capitalize()))
    user.groups.add(group)
    service = ServiceFactory()
    assign_perm("can_manage_profiles", group, service)
    assert user.has_perm("can_manage_profiles", service)
    out = StringIO()
    args = [
        "BERTH_INVALID",
        "{}Admin".format(ServiceType.BERTH.name.capitalize()),
        "can_manage_profiles",
    ]
    with pytest.raises(KeyError):
        call_command("remove_object_permission", *args, stdout=out)
    assert user.has_perm("can_manage_profiles", service)
