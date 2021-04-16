from io import StringIO

import pytest
from django.core.management import call_command
from guardian.shortcuts import assign_perm

from services.enums import ServiceType
from services.models import Service


def test_command_generate_services_adds_all_services():
    assert Service.objects.count() == 0
    call_command("generate_services")
    assert Service.objects.count() == len(ServiceType)


@pytest.mark.parametrize("service__name", ["berth"])
def test_command_generate_services_adds_only_missing_services(service):
    assert Service.objects.count() == 1
    call_command("generate_services")
    assert Service.objects.count() == len(ServiceType)


def test_command_add_object_permissions_with_correct_arguments_output(
    user, service, group
):
    user.groups.add(group)
    assert not user.has_perm("can_view_profiles", service)
    assert not user.has_perm("can_manage_profiles", service)
    out = StringIO()
    args = [
        ServiceType.BERTH.name,
        group.name,
        "can_view_profiles",
    ]
    call_command("add_object_permission", *args, stdout=out)
    args = [
        ServiceType.BERTH.name,
        group.name,
        "can_manage_profiles",
    ]
    call_command("add_object_permission", *args, stdout=out)
    assert (
        "Permission can_view_profiles added for {0} on service {1}".format(
            group.name, ServiceType.BERTH.name.capitalize()
        )
        in out.getvalue()
    )
    assert (
        "Permission can_manage_profiles added for {0} on service {1}".format(
            group.name, ServiceType.BERTH.name.capitalize()
        )
        in out.getvalue()
    )
    assert user.has_perm("can_view_profiles", service)
    assert user.has_perm("can_manage_profiles", service)


def test_command_add_object_permissions_errors_out_when_invalid_permission_given(
    user, service, group
):
    user.groups.add(group)
    out = StringIO()
    args = [
        ServiceType.BERTH.name,
        group.name,
        "can_manage_profiles_invalid",
    ]
    call_command("add_object_permission", *args, stdout=out)
    assert "Invalid permission given" in out.getvalue()
    assert not user.has_perm("can_manage_profiles_invalid", service)


def test_command_add_object_permissions_errors_out_when_invalid_group_name_given(
    user, service, group
):
    user.groups.add(group)
    out = StringIO()
    args = [
        ServiceType.BERTH.name,
        "InvalidGroup",
        "can_manage_profiles",
    ]
    call_command("add_object_permission", *args, stdout=out)
    assert "Invalid group_name given" in out.getvalue()
    assert not user.has_perm("can_manage_profiles", service)


def test_command_add_object_permissions_throws_error_when_invalid_service_type_given(
    user, service, group
):
    user.groups.add(group)
    out = StringIO()
    args = [
        "BERTH_INVALID",
        group.name,
        "can_manage_profiles",
    ]
    with pytest.raises(KeyError):
        call_command("add_object_permission", *args, stdout=out)
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
        ServiceType.BERTH.name,
        group.name,
        "can_view_profiles",
    ]
    call_command("remove_object_permission", *args, stdout=out)
    args = [
        ServiceType.BERTH.name,
        group.name,
        "can_manage_profiles",
    ]
    call_command("remove_object_permission", *args, stdout=out)
    assert (
        "Permission can_view_profiles removed for {0} on service {1}".format(
            group.name, ServiceType.BERTH.name.capitalize()
        )
        in out.getvalue()
    )
    assert (
        "Permission can_manage_profiles removed for {0} on service {1}".format(
            group.name, ServiceType.BERTH.name.capitalize()
        )
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
    out = StringIO()
    args = [
        ServiceType.BERTH.name,
        group.name,
        "can_manage_profiles_invalid",
    ]
    call_command("remove_object_permission", *args, stdout=out)
    assert "Invalid permission given" in out.getvalue()
    assert user.has_perm("can_manage_profiles", service)


def test_command_remove_object_permissions_errors_out_when_invalid_group_name_given(
    user, service, group
):
    user.groups.add(group)
    assign_perm("can_manage_profiles", group, service)
    assert user.has_perm("can_manage_profiles", service)
    out = StringIO()
    args = [
        ServiceType.BERTH.name,
        "InvalidGroup",
        "can_manage_profiles",
    ]
    call_command("remove_object_permission", *args, stdout=out)
    assert "Invalid group_name given" in out.getvalue()
    assert user.has_perm("can_manage_profiles", service)


def test_command_remove_object_permissions_throws_error_when_invalid_service_type_given(
    user, service, group
):
    user.groups.add(group)
    assign_perm("can_manage_profiles", group, service)
    assert user.has_perm("can_manage_profiles", service)
    out = StringIO()
    args = [
        "BERTH_INVALID",
        group.name,
        "can_manage_profiles",
    ]
    with pytest.raises(KeyError):
        call_command("remove_object_permission", *args, stdout=out)
    assert user.has_perm("can_manage_profiles", service)
