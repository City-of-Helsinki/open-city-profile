from string import Template

import pytest
from django.utils.translation import gettext_lazy as _
from graphene import relay
from guardian.shortcuts import assign_perm

from open_city_profile.consts import OBJECT_DOES_NOT_EXIST_ERROR
from open_city_profile.tests.asserts import assert_match_error_code
from services.tests.factories import ServiceConnectionFactory

from ..schema import ProfileNode
from .factories import SensitiveDataFactory


def test_normal_user_cannot_query_a_profile(user_gql_client, profile, service):
    ServiceConnectionFactory(profile=profile, service=service)

    t = Template(
        """
        {
            profile(id: "${id}") {
                firstName
                lastName
            }
        }
    """
    )

    query = t.substitute(
        id=relay.Node.to_global_id(ProfileNode._meta.name, profile.id),
    )
    executed = user_gql_client.execute(query, service=service)
    assert "errors" in executed
    assert executed["errors"][0]["message"] == _(
        "You do not have permission to perform this action."
    )


def test_staff_user_can_query_a_profile_connected_to_service_he_is_admin_of(
    user_gql_client, profile, group, service
):
    ServiceConnectionFactory(profile=profile, service=service)
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service)

    # serviceType is included in query just to ensure that it has NO affect
    t = Template(
        """
        {
            profile(id: "${id}", serviceType: GODCHILDREN_OF_CULTURE) {
                firstName
                lastName
            }
        }
    """
    )

    query = t.substitute(
        id=relay.Node.to_global_id(ProfileNode._meta.name, profile.id),
    )
    expected_data = {
        "profile": {"firstName": profile.first_name, "lastName": profile.last_name}
    }
    executed = user_gql_client.execute(query, service=service)
    assert executed["data"] == expected_data


def test_staff_user_cannot_query_a_profile_without_id(
    user_gql_client, profile, group, service
):
    ServiceConnectionFactory(profile=profile, service=service)
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service)

    query = """
        {
            profile {
                firstName
                lastName
            }
        }
    """

    executed = user_gql_client.execute(query, service=service)
    assert "errors" in executed


def test_staff_user_cannot_query_a_profile_without_a_connection_to_their_service(
    user_gql_client, profile, group, service_factory
):
    user = user_gql_client.user
    staff_user_service = service_factory()
    user.groups.add(group)
    assign_perm("can_view_profiles", group, staff_user_service)

    other_service = service_factory()
    ServiceConnectionFactory(profile=profile, service=other_service)

    t = Template(
        """
        {
            profile(id: "${id}") {
                firstName
                lastName
            }
        }
    """
    )

    query = t.substitute(
        id=relay.Node.to_global_id(ProfileNode._meta.name, profile.id),
    )
    executed = user_gql_client.execute(query, service=staff_user_service)
    assert "errors" in executed
    assert "code" in executed["errors"][0]["extensions"]
    assert executed["errors"][0]["extensions"]["code"] == OBJECT_DOES_NOT_EXIST_ERROR


def test_staff_user_cannot_query_sensitive_data_with_only_profile_permissions(
    user_gql_client, profile, group, service
):
    SensitiveDataFactory(profile=profile)
    ServiceConnectionFactory(profile=profile, service=service)
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service)

    t = Template(
        """
        {
            profile(id: "${id}") {
                sensitivedata {
                    ssn
                }
            }
        }
    """
    )

    query = t.substitute(
        id=relay.Node.to_global_id(ProfileNode._meta.name, profile.id),
    )
    expected_data = {"profile": {"sensitivedata": None}}
    executed = user_gql_client.execute(query, service=service)
    assert "errors" not in executed
    assert executed["data"] == expected_data


def test_staff_user_can_query_sensitive_data_with_given_permissions(
    user_gql_client, profile, group, service
):
    sensitive_data = SensitiveDataFactory(profile=profile)
    ServiceConnectionFactory(profile=profile, service=service)
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service)
    assign_perm("can_view_sensitivedata", group, service)

    t = Template(
        """
        {
            profile(id: "${id}") {
                sensitivedata {
                    ssn
                }
            }
        }
    """
    )

    query = t.substitute(
        id=relay.Node.to_global_id(ProfileNode._meta.name, profile.id),
    )
    expected_data = {"profile": {"sensitivedata": {"ssn": sensitive_data.ssn}}}
    executed = user_gql_client.execute(query, service=service)
    assert "errors" not in executed
    assert executed["data"] == expected_data


def test_staff_receives_null_sensitive_data_if_it_does_not_exist(
    user_gql_client, profile, group, service
):
    ServiceConnectionFactory(profile=profile, service=service)
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service)
    assign_perm("can_view_sensitivedata", group, service)

    t = Template(
        """
        {
            profile(id: "${id}") {
                sensitivedata {
                    ssn
                }
            }
        }
    """
    )

    query = t.substitute(
        id=relay.Node.to_global_id(ProfileNode._meta.name, profile.id),
    )
    expected_data = {"profile": {"sensitivedata": None}}
    executed = user_gql_client.execute(query, service=service)
    assert "errors" in executed
    assert executed["data"] == expected_data


@pytest.mark.parametrize("amr_claim_value", [None, 0, "authmethod1", "foo"])
@pytest.mark.parametrize("has_needed_permission", [True, False])
def test_staff_user_needs_required_permission_to_access_verified_personal_information(
    has_needed_permission,
    amr_claim_value,
    settings,
    user_gql_client,
    profile_with_verified_personal_information,
    group,
    service,
):
    settings.VERIFIED_PERSONAL_INFORMATION_ACCESS_AMR_LIST = [
        "authmethod1",
        "authmethod2",
    ]

    ServiceConnectionFactory(
        profile=profile_with_verified_personal_information, service=service
    )

    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service)
    if has_needed_permission:
        assign_perm("can_view_verified_personal_information", group, service)

    t = Template(
        """
            {
                profile(id: "${id}") {
                    verifiedPersonalInformation {
                        firstName
                    }
                }
            }
        """
    )
    query = t.substitute(
        id=relay.Node.to_global_id(
            ProfileNode._meta.name, profile_with_verified_personal_information.id
        )
    )

    token_payload = {"loa": "substantial", "amr": amr_claim_value}
    executed = user_gql_client.execute(
        query, auth_token_payload=token_payload, service=service
    )

    if (
        has_needed_permission
        and amr_claim_value in settings.VERIFIED_PERSONAL_INFORMATION_ACCESS_AMR_LIST
    ):
        assert "errors" not in executed
        assert executed["data"] == {
            "profile": {
                "verifiedPersonalInformation": {
                    "firstName": profile_with_verified_personal_information.verified_personal_information.first_name
                }
            }
        }
    else:
        assert_match_error_code(executed, "PERMISSION_DENIED_ERROR")
        assert executed["data"] == {"profile": {"verifiedPersonalInformation": None}}
