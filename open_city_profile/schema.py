import graphene

import profiles.schema
import youths.schema


class Query(profiles.schema.Query, youths.schema.Query, graphene.ObjectType):
    pass


class Mutation(profiles.schema.Mutation, youths.schema.Mutation, graphene.ObjectType):
    pass


schema = graphene.Schema(query=Query, mutation=Mutation)
