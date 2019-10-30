from django.utils.translation import ugettext_lazy as _

from services.consts import SERVICE_TYPES
from services.tests.factories import ServiceFactory

from .factories import ProfileFactory


def test_normal_user_can_not_query_berth_profiles(rf, user_gql_client):
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    query = """
        {
            berthProfiles {
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
    ServiceFactory(profile=profile, service_type=SERVICE_TYPES[1][0])
    request = rf.post("/graphql")
    request.user = superuser_gql_client.user

    query = """
        {
            berthProfiles {
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


def test_admin_user_can_filter_berth_profiles(rf, superuser_gql_client):
    profile_1, profile_2 = ProfileFactory(), ProfileFactory()
    ServiceFactory(profile=profile_1, service_type=SERVICE_TYPES[1][0])
    ServiceFactory(profile=profile_2, service_type=SERVICE_TYPES[1][0])
    request = rf.post("/graphql")
    request.user = superuser_gql_client.user

    query = """
        query getBerthProfiles($firstName: String){
            berthProfiles(firstName: $firstName) {
                count
                totalCount
            }
        }
    """

    expected_data = {"berthProfiles": {"count": 1, "totalCount": 2}}

    executed = superuser_gql_client.execute(
        query, variables={"firstName": profile_2.first_name}, context=request
    )
    assert dict(executed["data"]) == expected_data


def test_admin_user_can_sort_berth_profiles(rf, superuser_gql_client):
    profile_1, profile_2 = (
        ProfileFactory(first_name="Adam", last_name="Tester"),
        ProfileFactory(first_name="Bryan", last_name="Tester"),
    )
    ServiceFactory(profile=profile_1, service_type=SERVICE_TYPES[1][0])
    ServiceFactory(profile=profile_2, service_type=SERVICE_TYPES[1][0])
    request = rf.post("/graphql")
    request.user = superuser_gql_client.user

    query = """
        query getBerthProfiles {
            berthProfiles(orderBy: "-firstName") {
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
    executed = superuser_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data


def test_admin_user_can_paginate_berth_profiles(rf, superuser_gql_client):
    profile_1, profile_2 = (
        ProfileFactory(first_name="Adam", last_name="Tester"),
        ProfileFactory(first_name="Bryan", last_name="Tester"),
    )
    ServiceFactory(profile=profile_1, service_type=SERVICE_TYPES[1][0])
    ServiceFactory(profile=profile_2, service_type=SERVICE_TYPES[1][0])
    request = rf.post("/graphql")
    request.user = superuser_gql_client.user

    query = """
        query getBerthProfiles {
            berthProfiles(orderBy: "firstName", first: 1) {
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
    executed = superuser_gql_client.execute(query, context=request)
    assert "data" in executed
    assert executed["data"]["berthProfiles"]["edges"] == expected_data["edges"]
    assert "pageInfo" in executed["data"]["berthProfiles"]
    assert "endCursor" in executed["data"]["berthProfiles"]["pageInfo"]

    end_cursor = executed["data"]["berthProfiles"]["pageInfo"]["endCursor"]

    query = """
        query getBerthProfiles($endCursor: String){
            berthProfiles(first: 1, after: $endCursor) {
                edges {
                    node {
                        firstName
                    }
                }
            }
        }
    """

    expected_data = {"edges": [{"node": {"firstName": "Bryan"}}]}
    executed = superuser_gql_client.execute(
        query, variables={"endCursor": end_cursor}, context=request
    )
    assert "data" in executed
    assert executed["data"]["berthProfiles"] == expected_data
