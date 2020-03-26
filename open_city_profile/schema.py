import graphene
from graphene_federation import build_schema

import profiles.schema
import services.schema
import youths.schema


class Query(profiles.schema.Query, youths.schema.Query, graphene.ObjectType):
    pass


class Mutation(
    profiles.schema.Mutation,
    services.schema.Mutation,
    youths.schema.Mutation,
    graphene.ObjectType,
):
    pass


schema = build_schema(Query, Mutation)
