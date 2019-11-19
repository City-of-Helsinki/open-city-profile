from string import Template

from django.utils.translation import ugettext_lazy as _
from graphene import relay
from guardian.shortcuts import assign_perm

from open_city_profile.tests.factories import GroupFactory
from services.tests.factories import ServiceConnectionFactory, ServiceFactory

from ..schema import ProfileNode
from .factories import ProfileFactory


def test_normal_user_can_not_query_berth_profiles(rf, user_gql_client):
    ServiceFactory()
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    query = """
        {
            profiles(serviceType: BERTH) {
                edges {
                    node {
                        firstName
                        lastName
                    }
                }
            }
        }
    """
    executed = user_gql_client.execute(query, context=request)
    assert "errors" in executed
    assert executed["errors"][0]["message"] == _(
        "You do not have permission to perform this action."
    )


def test_admin_user_can_query_berth_profiles(rf, superuser_gql_client):
    profile = ProfileFactory()
    service = ServiceFactory()
    ServiceConnectionFactory(profile=profile, service=service)
    request = rf.post("/graphql")
    request.user = superuser_gql_client.user

    query = """
        {
            profiles(serviceType: BERTH) {
                edges {
                    node {
                        firstName
                        lastName
                        nickname
                    }
                }
            }
        }
    """

    expected_data = {
        "profiles": {
            "edges": [
                {
                    "node": {
                        "firstName": profile.first_name,
                        "lastName": profile.last_name,
                        "nickname": profile.nickname,
                    }
                }
            ]
        }
    }
    executed = superuser_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data


def test_staff_user_with_group_access_can_query_berth_profiles(rf, user_gql_client):
    profile = ProfileFactory()
    service = ServiceFactory()
    ServiceConnectionFactory(profile=profile, service=service)
    group = GroupFactory()
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service)
    request = rf.post("/graphql")
    request.user = user

    query = """
        {
            profiles(serviceType: BERTH) {
                edges {
                    node {
                        firstName
                    }
                }
            }
        }
    """

    expected_data = {
        "profiles": {"edges": [{"node": {"firstName": profile.first_name}}]}
    }
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data


def test_staff_user_can_filter_berth_profiles(rf, user_gql_client):
    profile_1, profile_2 = ProfileFactory(), ProfileFactory()
    service = ServiceFactory()
    ServiceConnectionFactory(profile=profile_1, service=service)
    ServiceConnectionFactory(profile=profile_2, service=service)
    group = GroupFactory()
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service)
    request = rf.post("/graphql")
    request.user = user

    query = """
        query getBerthProfiles($firstName: String){
            profiles(serviceType: BERTH, firstName: $firstName) {
                count
                totalCount
            }
        }
    """

    expected_data = {"profiles": {"count": 1, "totalCount": 2}}

    executed = user_gql_client.execute(
        query, variables={"firstName": profile_2.first_name}, context=request
    )
    assert "errors" not in executed
    assert dict(executed["data"]) == expected_data


def test_staff_user_can_sort_berth_profiles(rf, user_gql_client):
    profile_1, profile_2 = (
        ProfileFactory(first_name="Adam", last_name="Tester"),
        ProfileFactory(first_name="Bryan", last_name="Tester"),
    )
    service = ServiceFactory()
    ServiceConnectionFactory(profile=profile_1, service=service)
    ServiceConnectionFactory(profile=profile_2, service=service)
    group = GroupFactory()
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service)
    request = rf.post("/graphql")
    request.user = user

    query = """
        query getBerthProfiles {
            profiles(serviceType: BERTH, orderBy: "-firstName") {
                edges {
                    node {
                        firstName
                    }
                }
            }
        }
    """

    expected_data = {
        "profiles": {
            "edges": [{"node": {"firstName": "Bryan"}}, {"node": {"firstName": "Adam"}}]
        }
    }
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data


def test_staff_user_can_paginate_berth_profiles(rf, user_gql_client):
    profile_1, profile_2 = (
        ProfileFactory(first_name="Adam", last_name="Tester"),
        ProfileFactory(first_name="Bryan", last_name="Tester"),
    )
    service = ServiceFactory()
    ServiceConnectionFactory(profile=profile_1, service=service)
    ServiceConnectionFactory(profile=profile_2, service=service)
    group = GroupFactory()
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service)
    request = rf.post("/graphql")
    request.user = user

    query = """
        query getBerthProfiles {
            profiles(serviceType: BERTH, orderBy: "firstName", first: 1) {
                pageInfo {
                    endCursor
                }
                edges {
                    node {
                        firstName
                    }
                }
            }
        }
    """

    expected_data = {"edges": [{"node": {"firstName": "Adam"}}]}
    executed = user_gql_client.execute(query, context=request)
    assert "data" in executed
    assert executed["data"]["profiles"]["edges"] == expected_data["edges"]
    assert "pageInfo" in executed["data"]["profiles"]
    assert "endCursor" in executed["data"]["profiles"]["pageInfo"]

    end_cursor = executed["data"]["profiles"]["pageInfo"]["endCursor"]

    query = """
        query getBerthProfiles($endCursor: String){
            profiles(serviceType: BERTH, first: 1, after: $endCursor) {
                edges {
                    node {
                        firstName
                    }
                }
            }
        }
    """

    expected_data = {"edges": [{"node": {"firstName": "Bryan"}}]}
    executed = user_gql_client.execute(
        query, variables={"endCursor": end_cursor}, context=request
    )
    assert "data" in executed
    assert executed["data"]["profiles"] == expected_data


def test_staff_user_with_group_access_can_query_only_profiles_he_has_access_to(
    rf, user_gql_client
):
    profile_berth = ProfileFactory()
    profile_youth = ProfileFactory()
    service_berth = ServiceFactory(service_type="BERTH")
    service_youth = ServiceFactory(service_type="YOUTH_MEMBERSHIP")
    ServiceConnectionFactory(profile=profile_berth, service=service_berth)
    ServiceConnectionFactory(profile=profile_youth, service=service_youth)
    group_berth = GroupFactory()
    user = user_gql_client.user
    user.groups.add(group_berth)
    assign_perm("can_view_profiles", group_berth, service_berth)
    request = rf.post("/graphql")
    request.user = user

    query = """
        {
            profiles(serviceType: BERTH) {
                edges {
                    node {
                        firstName
                    }
                }
            }
        }
    """

    expected_data = {
        "profiles": {"edges": [{"node": {"firstName": profile_berth.first_name}}]}
    }
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data

    query = """
        {
            profiles(serviceType: YOUTH_MEMBERSHIP) {
                edges {
                    node {
                        firstName
                    }
                }
            }
        }
    """

    executed = user_gql_client.execute(query, context=request)
    assert "errors" in executed
    assert executed["errors"][0]["message"] == _(
        "You do not have permission to perform this action."
    )


def test_normal_user_can_query_his_own_profile(rf, user_gql_client):
    profile = ProfileFactory(user=user_gql_client.user)
    request = rf.post("/graphql")
    request.user = user_gql_client.user
    query = """
        {
            myProfile {
                firstName
                lastName
            }
        }
    """
    expected_data = {
        "myProfile": {"firstName": profile.first_name, "lastName": profile.last_name}
    }
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data


def test_normal_user_cannot_query_a_profile(rf, user_gql_client):
    profile = ProfileFactory()
    service = ServiceFactory()
    ServiceConnectionFactory(profile=profile, service=service)
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    t = Template(
        """
        {
            profile(id: "${id}", serviceType: ${service_type}) {
                firstName
                lastName
            }
        }
    """
    )

    query = t.substitute(
        id=relay.Node.to_global_id(ProfileNode._meta.name, profile.id),
        service_type=service.service_type,
    )
    executed = user_gql_client.execute(query, context=request)
    assert "errors" in executed
    assert executed["errors"][0]["message"] == _(
        "You do not have permission to perform this action."
    )


def test_staff_user_can_query_a_profile_connected_to_service_he_is_admin_of(
    rf, user_gql_client
):
    profile = ProfileFactory()
    service = ServiceFactory()
    ServiceConnectionFactory(profile=profile, service=service)
    group = GroupFactory()
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service)
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    t = Template(
        """
        {
            profile(id: "${id}", serviceType: ${service_type}) {
                firstName
                lastName
            }
        }
    """
    )

    query = t.substitute(
        id=relay.Node.to_global_id(ProfileNode._meta.name, profile.id),
        service_type=service.service_type,
    )
    executed = user_gql_client.execute(query, context=request)
    expected_data = {
        "profile": {"firstName": profile.first_name, "lastName": profile.last_name}
    }
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data


def test_staff_user_cannot_query_a_profile_without_id(rf, user_gql_client):
    profile = ProfileFactory()
    service = ServiceFactory()
    ServiceConnectionFactory(profile=profile, service=service)
    group = GroupFactory()
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service)
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    t = Template(
        """
        {
            profile(serviceType: ${service_type}) {
                firstName
                lastName
            }
        }
    """
    )

    query = t.substitute(service_type=service.service_type)
    executed = user_gql_client.execute(query, context=request)
    executed = user_gql_client.execute(query, context=request)
    assert "errors" in executed


def test_staff_user_cannot_query_a_profile_without_service_type(rf, user_gql_client):
    profile = ProfileFactory()
    service = ServiceFactory()
    ServiceConnectionFactory(profile=profile, service=service)
    group = GroupFactory()
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service)
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    t = Template(
        """
        {
            profile(id: ${id}) {
                firstName
                lastName
            }
        }
    """
    )

    query = t.substitute(id=relay.Node.to_global_id(ProfileNode._meta.name, profile.id))
    executed = user_gql_client.execute(query, context=request)
    executed = user_gql_client.execute(query, context=request)
    assert "errors" in executed


def test_staff_user_cannot_query_a_profile_with_service_type_that_is_not_connected(
    rf, user_gql_client
):
    profile = ProfileFactory()
    service_berth = ServiceFactory()
    service_youth = ServiceFactory(service_type="YOUTH_MEMBERSHIP")
    ServiceConnectionFactory(profile=profile, service=service_berth)
    group = GroupFactory()
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service_youth)
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    t = Template(
        """
        {
            profile(id: "${id}", serviceType: ${service_type}) {
                firstName
                lastName
            }
        }
    """
    )

    query = t.substitute(
        id=relay.Node.to_global_id(ProfileNode._meta.name, profile.id),
        service_type=service_youth.service_type,
    )
    executed = user_gql_client.execute(query, context=request)
    executed = user_gql_client.execute(query, context=request)
    assert "errors" in executed
    assert executed["errors"][0]["message"] == _("Profile not found!")


def test_staff_user_cannot_query_a_profile_with_service_type_that_he_is_not_admin_of(
    rf, user_gql_client
):
    profile = ProfileFactory()
    service_berth = ServiceFactory()
    service_youth = ServiceFactory(service_type="YOUTH_MEMBERSHIP")
    ServiceConnectionFactory(profile=profile, service=service_berth)
    group = GroupFactory()
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service_youth)
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    t = Template(
        """
        {
            profile(id: "${id}", serviceType: ${service_type}) {
                firstName
                lastName
            }
        }
    """
    )

    query = t.substitute(
        id=relay.Node.to_global_id(ProfileNode._meta.name, profile.id),
        service_type=service_berth.service_type,
    )
    executed = user_gql_client.execute(query, context=request)
    executed = user_gql_client.execute(query, context=request)
    assert "errors" in executed
    assert executed["errors"][0]["message"] == _(
        "You do not have permission to perform this action."
    )


def test_profile_node_exposes_key_for_federation_gateway(rf, anon_user_gql_client):
    request = rf.post("/graphql")

    query = """
        query {
            _service {
                sdl
            }
        }
    """

    executed = anon_user_gql_client.execute(query, context=request)
    assert (
        'type ProfileNode implements Node  @key(fields: "id")'
        in executed["data"]["_service"]["sdl"]
    )
