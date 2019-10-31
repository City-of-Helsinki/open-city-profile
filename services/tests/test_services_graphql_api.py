from collections import OrderedDict
from string import Template

from django.utils.translation import ugettext_lazy as _

from services.tests.factories import ProfileFactory, ServiceFactory


def test_normal_user_can_query_own_services(rf, user_gql_client):
    request = rf.post("/graphql")
    request.user = user_gql_client.user
    profile = ProfileFactory(user=user_gql_client.user)
    service = ServiceFactory(profile=profile)

    query = """
        {
            profile {
                services {
                    type
                }
            }
        }
    """
    expected_data = {
        "profile": OrderedDict(
            {"services": [OrderedDict({"type": service.service_type})]}
        )
    }
    executed = user_gql_client.execute(query, context_value=request)
    assert dict(executed["data"]) == expected_data


def test_normal_user_can_add_service_mutation(rf, user_gql_client):
    request = rf.post("/graphql")
    request.user = user_gql_client.user
    ProfileFactory(user=user_gql_client.user)

    t = Template(
        """
        mutation{
            addService(service: {type: ${serviceType}}){
                service{
                    type
                }
            }
        }
        """
    )
    creation_data = {"serviceType": "BERTH"}
    query = t.substitute(**creation_data)
    expected_data = {
        "addService": OrderedDict({"service": OrderedDict({"type": "BERTH"})})
    }
    executed = user_gql_client.execute(query, context_value=request)
    assert dict(executed["data"]) == expected_data


def test_normal_user_cannot_add_service_multiple_times_mutation(rf, user_gql_client):
    request = rf.post("/graphql")
    request.user = user_gql_client.user
    ProfileFactory(user=user_gql_client.user)

    t = Template(
        """
        mutation{
            addService(service: {type: ${serviceType}}){
                service{
                    type
                }
            }
        }
        """
    )
    creation_data = {"serviceType": "BERTH"}
    query = t.substitute(**creation_data)
    expected_data = {"addService": {"service": {"type": "BERTH"}}}
    executed = user_gql_client.execute(query, context_value=request)
    assert dict(executed["data"]) == expected_data
    executed = user_gql_client.execute(query, context_value=request)
    assert "errors" in executed
    assert executed["errors"][0]["message"] == _(
        "Service already exists for this profile!"
    )
