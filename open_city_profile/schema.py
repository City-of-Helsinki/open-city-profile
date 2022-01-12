import graphene
from graphene_federation import build_schema
from graphql.type.directives import specified_directives

import profiles.schema
import services.schema
import subscriptions.schema
from open_city_profile.graphene import (
    HelTranslationDirective,
    HelTranslationLanguageType,
)


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


schema = build_schema(
    Query,
    Mutation,
    directives=specified_directives + [HelTranslationDirective],
    types=[HelTranslationLanguageType],
)
