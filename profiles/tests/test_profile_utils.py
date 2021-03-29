from guardian.shortcuts import assign_perm

from ..utils import requester_has_service_permission


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
