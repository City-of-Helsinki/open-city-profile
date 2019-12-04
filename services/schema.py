import graphene
from django.db.utils import IntegrityError
from django.utils.translation import ugettext_lazy as _
from graphene import relay
from graphene_django.types import DjangoObjectType
from graphql import GraphQLError
from graphql_jwt.decorators import login_required

from .enums import ServiceType
from .models import Service, ServiceConnection

AllowedServiceType = graphene.Enum.from_enum(
    ServiceType, description=lambda e: e.label if e else ""
)


class ServiceNode(DjangoObjectType):
    type = AllowedServiceType(source="service_type")

    class Meta:
        model = Service
        fields = ("created_at",)
        filter_fields = []
        interfaces = (relay.Node,)


class ServiceConnectionType(DjangoObjectType):
    class Meta:
        model = ServiceConnection
        fields = ("service", "created_at", "enabled")
        filter_fields = []
        interfaces = (relay.Node,)


class ServiceInput(graphene.InputObjectType):
    type = AllowedServiceType()


class ServiceConnectionInput(graphene.InputObjectType):
    service = ServiceInput(required=True)
    enabled = graphene.Boolean()


class AddServiceConnection(graphene.Mutation):
    class Arguments:
        service_connection = ServiceConnectionInput(required=True)

    service_connection = graphene.Field(ServiceConnectionType)

    @login_required
    def mutate(self, info, **kwargs):
        service_connection_data = kwargs.pop("service_connection")
        service_data = service_connection_data.get("service")
        service_type = service_data.get("type")
        try:
            service = Service.objects.get(service_type=service_type)
            service_connection = ServiceConnection.objects.create(
                profile=info.context.user.profile, service=service
            )
            return AddServiceConnection(service_connection=service_connection)
        except Service.DoesNotExist:
            raise GraphQLError(_("Service not found!"))
        except IntegrityError:
            raise GraphQLError(_("Service already exists for this profile!"))


class Mutation(graphene.ObjectType):
    add_service_connection = AddServiceConnection.Field()
