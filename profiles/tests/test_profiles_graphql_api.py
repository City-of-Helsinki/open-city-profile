from django.utils.translation import ugettext_lazy as _
from guardian.shortcuts import assign_perm

from services.tests.factories import ServiceConnectionFactory, ServiceFactory

from .factories import GroupFactory, ProfileFactory


def test_normal_user_can_not_query_berth_profiles(rf, user_gql_client):
    ServiceFactory()
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    query = """
        {
            berthProfiles(serviceType: BERTH) {
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
            berthProfiles(serviceType: BERTH) {
                edges {
                    node {
                        firstName
                        lastName
                        nickname
                        email
                        phone
                    }
                }
            }
        }
    """

    expected_data = {
        "berthProfiles": {
            "edges": [
                {
                    "node": {
                        "firstName": profile.first_name,
                        "lastName": profile.last_name,
                        "nickname": profile.nickname,
                        "email": profile.email,
                        "phone": profile.phone,
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
            berthProfiles(serviceType: BERTH) {
                edges {
                    node {
                        firstName
                    }
                }
            }
        }
    """

    expected_data = {
        "berthProfiles": {"edges": [{"node": {"firstName": profile.first_name}}]}
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
            berthProfiles(serviceType: BERTH, firstName: $firstName) {
                count
                totalCount
            }
        }
    """

    expected_data = {"berthProfiles": {"count": 1, "totalCount": 2}}

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
            berthProfiles(serviceType: BERTH, orderBy: "-firstName") {
                edges {
                    node {
                        firstName
                    }
                }
            }
        }
    """

    expected_data = {
        "berthProfiles": {
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
            berthProfiles(serviceType: BERTH, orderBy: "firstName", first: 1) {
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
    assert executed["data"]["berthProfiles"]["edges"] == expected_data["edges"]
    assert "pageInfo" in executed["data"]["berthProfiles"]
    assert "endCursor" in executed["data"]["berthProfiles"]["pageInfo"]

    end_cursor = executed["data"]["berthProfiles"]["pageInfo"]["endCursor"]

    query = """
        query getBerthProfiles($endCursor: String){
            berthProfiles(serviceType: BERTH, first: 1, after: $endCursor) {
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
    assert executed["data"]["berthProfiles"] == expected_data


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
            berthProfiles(serviceType: BERTH) {
                edges {
                    node {
                        firstName
                    }
                }
            }
        }
    """

    expected_data = {
        "berthProfiles": {"edges": [{"node": {"firstName": profile_berth.first_name}}]}
    }
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data

    query = """
        {
            berthProfiles(serviceType: YOUTH_MEMBERSHIP) {
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
