def test_profile_node_exposes_key_for_federation_gateway(anon_user_gql_client):
    query = """
        query {
            _service {
                sdl
            }
        }
    """

    executed = anon_user_gql_client.execute(query)
    assert (
        'type ProfileNode implements Node  @key(fields: "id")'
        in executed["data"]["_service"]["sdl"]
    )


def test_profile_connection_schema_matches_federated_schema(anon_user_gql_client):
    query = """
        query {
            _service {
                sdl
            }
        }
    """

    executed = anon_user_gql_client.execute(query)
    assert (
        "type ProfileNodeConnection {   pageInfo: PageInfo!   "
        "edges: [ProfileNodeEdge]!   count: Int!   totalCount: Int! }"
        in executed["data"]["_service"]["sdl"]
    )
