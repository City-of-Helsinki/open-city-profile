from string import Template

from django.utils.translation import gettext_lazy as _
from graphene import relay
from guardian.shortcuts import assign_perm

from open_city_profile.consts import OBJECT_DOES_NOT_EXIST_ERROR
from services.enums import ServiceType
from services.tests.factories import ServiceConnectionFactory

from ..schema import ProfileNode
from .factories import SensitiveDataFactory


def test_normal_user_cannot_query_a_profile(rf, user_gql_client, profile, service):
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
        service_type=ServiceType.BERTH.name,
    )
    executed = user_gql_client.execute(query, context=request)
    assert "errors" in executed
    assert executed["errors"][0]["message"] == _(
        "You do not have permission to perform this action."
    )


def test_staff_user_can_query_a_profile_connected_to_service_he_is_admin_of(
    rf, user_gql_client, profile, group, service
):
    ServiceConnectionFactory(profile=profile, service=service)
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
        service_type=ServiceType.BERTH.name,
    )
    expected_data = {
        "profile": {"firstName": profile.first_name, "lastName": profile.last_name}
    }
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data


def test_staff_user_cannot_query_a_profile_without_id(
    rf, user_gql_client, profile, group, service
):
    ServiceConnectionFactory(profile=profile, service=service)
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

    query = t.substitute(service_type=ServiceType.BERTH.name)
    executed = user_gql_client.execute(query, context=request)
    assert "errors" in executed


def test_staff_user_cannot_query_a_profile_without_service_type(
    rf, user_gql_client, profile, group, service
):
    ServiceConnectionFactory(profile=profile, service=service)
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
    assert "errors" in executed


def test_staff_user_cannot_query_a_profile_with_service_type_that_is_not_connected(
    rf, user_gql_client, profile, group, service_factory
):
    service_berth = service_factory()
    service_youth = service_factory(service_type=ServiceType.YOUTH_MEMBERSHIP)
    ServiceConnectionFactory(profile=profile, service=service_berth)
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
        service_type=ServiceType.YOUTH_MEMBERSHIP.name,
    )
    executed = user_gql_client.execute(query, context=request)
    assert "errors" in executed
    assert "code" in executed["errors"][0]["extensions"]
    assert executed["errors"][0]["extensions"]["code"] == OBJECT_DOES_NOT_EXIST_ERROR


def test_staff_user_cannot_query_a_profile_with_service_type_that_he_is_not_admin_of(
    rf, user_gql_client, profile, group, service_factory
):
    service_berth = service_factory()
    service_youth = service_factory(service_type=ServiceType.YOUTH_MEMBERSHIP)
    ServiceConnectionFactory(profile=profile, service=service_berth)
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
        service_type=ServiceType.BERTH.name,
    )
    executed = user_gql_client.execute(query, context=request)
    assert "errors" in executed
    assert executed["errors"][0]["message"] == _(
        "You do not have permission to perform this action."
    )


def test_staff_user_cannot_query_sensitive_data_with_only_profile_permissions(
    rf, user_gql_client, profile, group, service
):
    SensitiveDataFactory(profile=profile)
    ServiceConnectionFactory(profile=profile, service=service)
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service)
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    t = Template(
        """
        {
            profile(id: "${id}", serviceType: ${service_type}) {
                sensitivedata {
                    ssn
                }
            }
        }
    """
    )

    query = t.substitute(
        id=relay.Node.to_global_id(ProfileNode._meta.name, profile.id),
        service_type=ServiceType.BERTH.name,
    )
    expected_data = {"profile": {"sensitivedata": None}}
    executed = user_gql_client.execute(query, context=request)
    assert "errors" not in executed
    assert dict(executed["data"]) == expected_data


def test_staff_user_can_query_sensitive_data_with_given_permissions(
    rf, user_gql_client, profile, group, service
):
    sensitive_data = SensitiveDataFactory(profile=profile)
    ServiceConnectionFactory(profile=profile, service=service)
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service)
    assign_perm("can_view_sensitivedata", group, service)
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    t = Template(
        """
        {
            profile(id: "${id}", serviceType: ${service_type}) {
                sensitivedata {
                    ssn
                }
            }
        }
    """
    )

    query = t.substitute(
        id=relay.Node.to_global_id(ProfileNode._meta.name, profile.id),
        service_type=ServiceType.BERTH.name,
    )
    expected_data = {"profile": {"sensitivedata": {"ssn": sensitive_data.ssn}}}
    executed = user_gql_client.execute(query, context=request)
    assert "errors" not in executed
    assert dict(executed["data"]) == expected_data


def test_staff_receives_null_sensitive_data_if_it_does_not_exist(
    rf, user_gql_client, profile, group, service
):
    ServiceConnectionFactory(profile=profile, service=service)
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service)
    assign_perm("can_view_sensitivedata", group, service)
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    t = Template(
        """
        {
            profile(id: "${id}", serviceType: ${service_type}) {
                sensitivedata {
                    ssn
                }
            }
        }
    """
    )

    query = t.substitute(
        id=relay.Node.to_global_id(ProfileNode._meta.name, profile.id),
        service_type=ServiceType.BERTH.name,
    )
    expected_data = {"profile": {"sensitivedata": None}}
    executed = user_gql_client.execute(query, context=request)
    assert "errors" in executed
    assert dict(executed["data"]) == expected_data
