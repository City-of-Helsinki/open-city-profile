import graphene

import profiles.schema


class Query(profiles.schema.Query, graphene.ObjectType):
    pass


class Mutation(profiles.schema.Mutation, graphene.ObjectType):
    pass


schema = graphene.Schema(query=Query, mutation=Mutation)
