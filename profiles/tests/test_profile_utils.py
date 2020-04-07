import pytest
from guardian.shortcuts import assign_perm

from open_city_profile.tests.factories import GroupFactory
from services.enums import ServiceType
from services.tests.factories import ServiceConnectionFactory, ServiceFactory

from ..utils import user_has_staff_perms_to_view_profile
from .factories import ProfileFactory, UserFactory


@pytest.mark.parametrize("user_should_have_perms", [True, False])
def test_user_has_admin_perms_to_view_profile_util(user_should_have_perms):
    service_1 = ServiceFactory(service_type=ServiceType.BERTH)
    service_2 = ServiceFactory(service_type=ServiceType.YOUTH_MEMBERSHIP)
    group = GroupFactory()
    user = UserFactory()
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service_1)

    profile = ProfileFactory()

    if user_should_have_perms:
        ServiceConnectionFactory(profile=profile, service=service_1)
        assert user_has_staff_perms_to_view_profile(user, profile)
    else:
        ServiceConnectionFactory(profile=profile, service=service_2)
        assert not user_has_staff_perms_to_view_profile(user, profile)
