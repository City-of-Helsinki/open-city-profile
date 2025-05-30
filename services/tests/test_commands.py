from io import StringIO

import pytest
from django.core.management import CommandError, call_command
from guardian.shortcuts import assign_perm

from services.models import Service
from utils.utils import SERVICES


def test_command_generate_services_adds_all_services():
    assert Service.objects.count() == 0
    call_command("generate_services")
    assert Service.objects.count() == len(SERVICES)


@pytest.mark.parametrize("service__name", ["berth"])
def test_command_generate_services_adds_only_missing_services(service):
    assert Service.objects.count() == 1
    call_command("generate_services")
    assert Service.objects.count() == len(SERVICES)


def test_command_add_object_permissions_with_correct_arguments_output(
    user, service, group
):
    user.groups.add(group)
    assert not user.has_perm("can_view_profiles", service)
    assert not user.has_perm("can_manage_profiles", service)
    out = StringIO()
    args = [
        service.name,
        group.name,
        "can_view_profiles",
    ]
    call_command("add_object_permission", *args, stdout=out)
    args = [
        service.name,
        group.name,
        "can_manage_profiles",
    ]
    call_command("add_object_permission", *args, stdout=out)
    assert (
        f"Permission can_view_profiles added for {group.name} on service {service.name}"
        in out.getvalue()
    )
    assert (
        f"Permission can_manage_profiles added for {group.name} on service {service.name}"
        in out.getvalue()
    )
    assert user.has_perm("can_view_profiles", service)
    assert user.has_perm("can_manage_profiles", service)


def test_command_add_object_permissions_errors_out_when_invalid_permission_given(
    user, service, group
):
    user.groups.add(group)
    args = [
        service.name,
        group.name,
        "can_manage_profiles_invalid",
    ]
    with pytest.raises(CommandError, match="Invalid permission given"):
        call_command("add_object_permission", *args)
    assert not user.has_perm("can_manage_profiles_invalid", service)


def test_command_add_object_permissions_errors_out_when_invalid_group_name_given(
    user, service, group
):
    user.groups.add(group)
    args = [
        service.name,
        "InvalidGroup",
        "can_manage_profiles",
    ]
    with pytest.raises(CommandError, match="Invalid group_name given"):
        call_command("add_object_permission", *args)
    assert not user.has_perm("can_manage_profiles", service)


def test_command_add_object_permissions_errors_out_when_invalid_service_given(
    user, service, group
):
    user.groups.add(group)
    args = [
        "INVALID",
        group.name,
        "can_manage_profiles",
    ]
    with pytest.raises(CommandError, match="Invalid service given"):
        call_command("add_object_permission", *args)
    assert not user.has_perm("can_manage_profiles", service)


def test_command_remove_object_permissions_with_correct_arguments_output(
    user, service, group
):
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service)
    assign_perm("can_manage_profiles", group, service)
    assert user.has_perm("can_view_profiles", service)
    assert user.has_perm("can_manage_profiles", service)
    out = StringIO()
    args = [
        service.name,
        group.name,
        "can_view_profiles",
    ]
    call_command("remove_object_permission", *args, stdout=out)
    args = [
        service.name,
        group.name,
        "can_manage_profiles",
    ]
    call_command("remove_object_permission", *args, stdout=out)
    assert (
        f"Permission can_view_profiles removed for {group.name} on service {service.name}"
        in out.getvalue()
    )
    assert (
        f"Permission can_manage_profiles removed for {group.name} on service {service.name}"
        in out.getvalue()
    )
    assert not user.has_perm("can_view_profiles", service)
    assert not user.has_perm("can_manage_profiles", service)


def test_command_remove_object_permissions_errors_out_when_invalid_permission_given(
    user, service, group
):
    user.groups.add(group)
    assign_perm("can_manage_profiles", group, service)
    assert user.has_perm("can_manage_profiles", service)
    args = [
        service.name,
        group.name,
        "can_manage_profiles_invalid",
    ]
    with pytest.raises(CommandError, match="Invalid permission given"):
        call_command("remove_object_permission", *args)
    assert user.has_perm("can_manage_profiles", service)


def test_command_remove_object_permissions_errors_out_when_invalid_group_name_given(
    user, service, group
):
    user.groups.add(group)
    assign_perm("can_manage_profiles", group, service)
    assert user.has_perm("can_manage_profiles", service)
    args = [
        service.name,
        "InvalidGroup",
        "can_manage_profiles",
    ]
    with pytest.raises(CommandError, match="Invalid group_name given"):
        call_command("remove_object_permission", *args)
    assert user.has_perm("can_manage_profiles", service)


def test_command_remove_object_permissions_errors_out_when_invalid_service_given(
    user, service, group
):
    user.groups.add(group)
    assign_perm("can_manage_profiles", group, service)
    assert user.has_perm("can_manage_profiles", service)
    args = [
        "INVALID",
        group.name,
        "can_manage_profiles",
    ]
    with pytest.raises(CommandError, match="Invalid service given"):
        call_command("remove_object_permission", *args)
    assert user.has_perm("can_manage_profiles", service)
