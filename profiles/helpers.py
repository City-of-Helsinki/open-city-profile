from graphql_relay import to_global_id as relay_to_global_id


def to_global_id(type, id):
    return relay_to_global_id(type_=type, id_=id)
