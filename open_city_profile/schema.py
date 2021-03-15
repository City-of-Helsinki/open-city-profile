import graphene
from graphene_federation import build_schema

import profiles.schema
import services.schema
import subscriptions.schema


class Query(
    profiles.schema.Query, subscriptions.schema.Query, graphene.ObjectType,
):
    pass


class Mutation(
    profiles.schema.Mutation,
    services.schema.Mutation,
    subscriptions.schema.Mutation,
    graphene.ObjectType,
):
    pass


schema = build_schema(Query, Mutation)
