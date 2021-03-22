import pytest
from guardian.shortcuts import assign_perm

from services.enums import ServiceType
from services.tests.factories import ServiceConnectionFactory

from ..utils import (
    requester_has_service_permission,
    user_has_staff_perms_to_view_profile,
)


@pytest.mark.parametrize("user_should_have_perms", [True, False])
def test_user_has_admin_perms_to_view_profile_util(
    user_should_have_perms, user, profile, group, service_factory
):
    service_1 = service_factory(service_type=ServiceType.BERTH)
    service_2 = service_factory(service_type=ServiceType.YOUTH_MEMBERSHIP)
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service_1)

    if user_should_have_perms:
        ServiceConnectionFactory(profile=profile, service=service_1)
        assert user_has_staff_perms_to_view_profile(user, profile)
    else:
        ServiceConnectionFactory(profile=profile, service=service_2)
        assert not user_has_staff_perms_to_view_profile(user, profile)


def test_requester_has_service_permission_util_caches_results(
    rf, user, group, service, django_assert_num_queries
):
    permission = "can_view_profiles"
    user.groups.add(group)
    assign_perm(permission, group, service)

    request = rf.get("path")
    request.user = user
    request.service = service

    assert requester_has_service_permission(request, permission)

    with django_assert_num_queries(0):
        assert requester_has_service_permission(request, permission)
