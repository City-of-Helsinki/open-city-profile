import inflection


def to_graphql_name(s):
    return inflection.camelize(s, False)
