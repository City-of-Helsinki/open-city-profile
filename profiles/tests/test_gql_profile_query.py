from string import Template

from django.utils.translation import gettext_lazy as _
from graphene import relay
from guardian.shortcuts import assign_perm

from open_city_profile.consts import OBJECT_DOES_NOT_EXIST_ERROR
from services.enums import ServiceType
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
    service_berth = service_factory()
    service_youth = service_factory(service_type=ServiceType.YOUTH_MEMBERSHIP)
    ServiceConnectionFactory(profile=profile, service=service_berth)
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service_youth)

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
    executed = user_gql_client.execute(query, service=service_youth)
    assert "errors" in executed
    assert "code" in executed["errors"][0]["extensions"]
    assert executed["errors"][0]["extensions"]["code"] == OBJECT_DOES_NOT_EXIST_ERROR


def test_staff_user_cannot_override_service_with_argument_they_are_not_an_admin_of(
    user_gql_client, profile, group, service_factory
):
    service_berth = service_factory()
    service_youth = service_factory(service_type=ServiceType.YOUTH_MEMBERSHIP)
    ServiceConnectionFactory(profile=profile, service=service_berth)
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service_youth)

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
        service_type=ServiceType.BERTH.name,
    )
    executed = user_gql_client.execute(query, service=service_youth)
    assert "errors" in executed
    assert executed["errors"][0]["message"] == _(
        "You do not have permission to perform this action."
    )


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
