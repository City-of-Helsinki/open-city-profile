import graphene
from django.db import transaction
from graphene import relay

import profiles.schema as profiles_schema
from open_city_profile.decorators import login_required


class SubscriptionTypeNode(graphene.ObjectType):
    subscription_type_category = graphene.Field(
        "subscriptions.schema.SubscriptionTypeCategoryNode", required=True
    )
    code = graphene.String(required=True)
    created_at = graphene.DateTime(required=True)
    order = graphene.Int(required=True)
    label = graphene.String()

    class Meta:
        interfaces = (relay.Node,)
        filter_fields = []
        exclude = ("subscriptions",)


class SubscriptionTypeNodeConnection(relay.Connection):
    class Meta:
        node = SubscriptionTypeNode


class SubscriptionTypeCategoryNode(graphene.ObjectType):
    code = graphene.String(required=True)
    created_at = graphene.DateTime(required=True)
    order = graphene.Int(required=True)
    subscription_types = relay.ConnectionField(
        SubscriptionTypeNodeConnection, required=True
    )
    label = graphene.String()

    class Meta:
        interfaces = (relay.Node,)
        filter_fields = []


class SubscriptionTypeCategoryNodeConnection(relay.Connection):
    class Meta:
        node = SubscriptionTypeCategoryNode


class SubscriptionNode(graphene.ObjectType):
    class Meta:
        interfaces = (relay.Node,)
        filter_fields = []

    profile = graphene.Field(lambda: profiles_schema.ProfileNode, required=True)
    subscription_type = graphene.Field(SubscriptionTypeNode, required=True)
    created_at = graphene.DateTime(required=True)
    enabled = graphene.Boolean(required=True)


class SubscriptionNodeConnection(relay.Connection):
    class Meta:
        node = SubscriptionNode


class SubscriptionInputType(graphene.InputObjectType):
    subscription_type_id = graphene.ID(required=True)
    enabled = graphene.Boolean(required=True)


class UpdateMySubscriptionMutation(relay.ClientIDMutation):
    class Input:
        subscription = graphene.Field(SubscriptionInputType, required=True)

    subscription = graphene.Field(SubscriptionNode)

    @classmethod
    @login_required
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        return UpdateMySubscriptionMutation(subscription=None)


class Query(graphene.ObjectType):
    subscription_type_categories = relay.ConnectionField(
        SubscriptionTypeCategoryNodeConnection,
        deprecation_reason="The whole subscriptions concept is non-functional. There's no replacement.",
    )

    def resolve_subscription_type_categories(self, info, **kwargs):
        return []


class Mutation(graphene.ObjectType):
    # TODO: Complete the description
    update_my_subscription = UpdateMySubscriptionMutation.Field(
        description="",
        deprecation_reason="The whole subscriptions concept is non-functional. There's no replacement.",
    )
