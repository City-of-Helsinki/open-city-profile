import graphene
from django.db import transaction
from graphene import relay
from graphene_django.filter import DjangoFilterConnectionField
from graphene_django.types import DjangoObjectType
from graphql_jwt.decorators import login_required

from .models import Subscription, SubscriptionType, SubscriptionTypeCategory


class SubscriptionNode(DjangoObjectType):
    class Meta:
        model = Subscription
        interfaces = (relay.Node,)
        filter_fields = []


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
        subscription_data = input.get("subscription")
        subscription_type_id = subscription_data.get("subscription_type_id")
        subscription = Subscription.objects.get_or_create(
            profile=info.context.user.profile,
            subscription_type=graphene.Node.get_node_from_global_id(
                info, subscription_type_id, only_type=SubscriptionTypeNode
            ),
        )[0]
        subscription.enabled = subscription_data.get("enabled")
        subscription.save()

        return UpdateMySubscriptionMutation(subscription=subscription)


class Query(graphene.ObjectType):
    subscription_type_categories = DjangoFilterConnectionField(
        SubscriptionTypeCategoryNode
    )

    def resolve_subscription_type_categories(self, info, **kwargs):
        return SubscriptionTypeCategory.objects.all()


class Mutation(graphene.ObjectType):
    # TODO: Complete the description
    update_my_subscription = UpdateMySubscriptionMutation.Field(description="")
