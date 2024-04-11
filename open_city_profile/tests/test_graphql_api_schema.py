from graphql import print_schema


def test_graphql_schema_matches_the_reference(gql_schema, snapshot):
    actual_schema = print_schema(gql_schema)

    snapshot.assert_match(actual_schema)
