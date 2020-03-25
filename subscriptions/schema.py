import graphene
from graphene import relay
from graphene_django.filter import DjangoFilterConnectionField
from graphene_django.types import DjangoObjectType

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


class SubscriptionTypeCategoryNode(DjangoObjectType):
    label = graphene.String()

    class Meta:
        model = SubscriptionTypeCategory
        interfaces = (relay.Node,)
        filter_fields = []


class Query(graphene.ObjectType):
    subscription_type_categories = DjangoFilterConnectionField(
        SubscriptionTypeCategoryNode
    )

    def resolve_subscription_type_categories(self, info, **kwargs):
        return SubscriptionTypeCategory.objects.order_by("order")
