import graphene
from django.db import transaction
from graphene import relay
from graphene_django.filter import DjangoFilterConnectionField
from graphene_django.types import DjangoObjectType

import profiles.schema as profiles_schema
from open_city_profile.decorators import login_required

from .models import SubscriptionType, SubscriptionTypeCategory


class SubscriptionTypeNode(DjangoObjectType):
    label = graphene.String()

    class Meta:
        model = SubscriptionType
        interfaces = (relay.Node,)
        filter_fields = []
        exclude = ("subscriptions",)


class SubscriptionTypeCategoryNode(DjangoObjectType):
    label = graphene.String()

    class Meta:
        model = SubscriptionTypeCategory
        interfaces = (relay.Node,)
        filter_fields = []


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
    subscription_type_categories = DjangoFilterConnectionField(
        SubscriptionTypeCategoryNode
    )

    def resolve_subscription_type_categories(self, info, **kwargs):
        return SubscriptionTypeCategory.objects.all()


class Mutation(graphene.ObjectType):
    # TODO: Complete the description
    update_my_subscription = UpdateMySubscriptionMutation.Field(description="")
