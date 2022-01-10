from graphql_relay import from_global_id

from services.tests.factories import (
    AllowedDataFieldFactory,
    ServiceConnectionFactory,
    ServiceFactory,
)

from .factories import AddressFactory, EmailFactory, PhoneFactory, ProfileFactory

QUERY = """
{
    myProfile {
        addresses {
            edges {
                node {
                    address
                }
            }
        }
        emails {
            edges {
                node {
                    email
                }
            }
        }
        phones {
            edges {
                node {
                    phone
                }
            }
        }
        serviceConnections {
            edges {
                node {
                    id
                    service {
                        allowedDataFields {
                            edges {
                                node {
                                    fieldName
                                    order
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
"""


def test_addresses_are_ordered_first_by_primary_then_by_id(user_gql_client):
    profile = ProfileFactory(user=user_gql_client.user)
    first_address = AddressFactory(profile=profile, primary=False)
    primary_address = AddressFactory(profile=profile, primary=True)
    second_address = AddressFactory(profile=profile, primary=False)

    expected_edges = list(
        map(
            lambda address: {"node": {"address": address.address}},
            (primary_address, first_address, second_address),
        )
    )

    executed = user_gql_client.execute(QUERY)
    assert executed["data"]["myProfile"]["addresses"]["edges"] == expected_edges


def test_emails_are_ordered_first_by_primary_then_by_id(user_gql_client):
    profile = ProfileFactory(user=user_gql_client.user)
    first_email = EmailFactory(profile=profile, primary=False)
    primary_email = EmailFactory(profile=profile, primary=True)
    second_email = EmailFactory(profile=profile, primary=False)

    expected_edges = list(
        map(
            lambda email: {"node": {"email": email.email}},
            (primary_email, first_email, second_email),
        )
    )

    executed = user_gql_client.execute(QUERY)
    assert executed["data"]["myProfile"]["emails"]["edges"] == expected_edges


def test_phones_are_ordered_first_by_primary_then_by_id(user_gql_client):
    profile = ProfileFactory(user=user_gql_client.user)
    first_phone = PhoneFactory(profile=profile, primary=False)
    primary_phone = PhoneFactory(profile=profile, primary=True)
    second_phone = PhoneFactory(profile=profile, primary=False)

    expected_edges = list(
        map(
            lambda phone: {"node": {"phone": phone.phone}},
            (primary_phone, first_phone, second_phone),
        )
    )

    executed = user_gql_client.execute(QUERY)
    assert executed["data"]["myProfile"]["phones"]["edges"] == expected_edges


def test_service_connections_are_ordered_by_id(user_gql_client):
    profile = ProfileFactory(user=user_gql_client.user)
    connections = [
        ServiceConnectionFactory(profile=profile, service=ServiceFactory())
        for _ in range(3)
    ]

    executed = user_gql_client.execute(QUERY)
    connection_edges = executed["data"]["myProfile"]["serviceConnections"]["edges"]

    assert len(connection_edges) == len(connections)
    for edge, connection in zip(connection_edges, connections):
        assert from_global_id(edge["node"]["id"])[1] == str(connection.id)


def test_allowed_data_fields_are_ordered_by_order_field(user_gql_client, service):
    fields = (
        AllowedDataFieldFactory(field_name="1: field 2", final_order=2),
        AllowedDataFieldFactory(field_name="2: field 3", final_order=3),
        AllowedDataFieldFactory(field_name="3: field 1", final_order=1),
    )
    service.allowed_data_fields.set(fields)

    profile = ProfileFactory(user=user_gql_client.user)
    ServiceConnectionFactory(profile=profile, service=service)

    executed = user_gql_client.execute(QUERY)

    connection_edges = executed["data"]["myProfile"]["serviceConnections"]["edges"]

    assert len(connection_edges) == 1
    service_node = connection_edges[0]["node"]["service"]
    allowed_data_field_edges = service_node["allowedDataFields"]["edges"]

    assert len(allowed_data_field_edges) == 3

    fields_in_expected_order = sorted(fields, key=lambda x: x.order)
    for allowed_data_field_edge, field in zip(
        allowed_data_field_edges, fields_in_expected_order
    ):
        received_field = allowed_data_field_edge["node"]
        assert received_field["fieldName"] == field.field_name
        assert received_field["order"] == field.order
