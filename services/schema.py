import graphene
from django.db import transaction
from django.db.utils import IntegrityError
from graphene import relay
from graphene_django.filter import DjangoFilterConnectionField
from graphene_django.types import DjangoObjectType

from open_city_profile.decorators import login_and_service_required
from open_city_profile.exceptions import ServiceAlreadyExistsError
from open_city_profile.graphene import DjangoParlerObjectType

from .enums import ServiceType
from .models import AllowedDataField, Service, ServiceConnection

AllowedServiceType = graphene.Enum.from_enum(
    ServiceType,
    description=lambda e: e.label if e else "",
    deprecation_reason=lambda e: "The whole ServiceType enum is deprecated and shouldn't be used anymore. "
    "There are different replacements in various places, depending on how this type was used.",
)


class AllowedDataFieldNode(DjangoParlerObjectType):
    class Meta:
        model = AllowedDataField
        interfaces = (relay.Node,)


class ServiceConnectionType(DjangoObjectType):
    class Meta:
        model = ServiceConnection
        fields = ("service", "created_at", "enabled")
        filter_fields = []
        interfaces = (relay.Node,)


class ServiceNode(DjangoParlerObjectType):
    type = AllowedServiceType(
        source="service_type", deprecation_reason="See 'name' field for a replacement.",
    )
    serviceconnection_set = DjangoFilterConnectionField(
        ServiceConnectionType,
        required=True,
        deprecation_reason="Always returns an empty result. "
        "Getting connections for a service is not supported and there is no replacement.",
    )

    class Meta:
        model = Service
        fields = (
            "id",
            "name",
            "title",
            "description",
            "allowed_data_fields",
            "created_at",
            "gdpr_url",
            "gdpr_query_scope",
            "gdpr_delete_scope",
        )
        filter_fields = []
        interfaces = (relay.Node,)

    def resolve_serviceconnection_set(self, info, **kwargs):
        return ServiceConnection.objects.none()


class ServiceInput(graphene.InputObjectType):
    type = AllowedServiceType()


class ServiceConnectionInput(graphene.InputObjectType):
    service = ServiceInput(
        description="**OBSOLETE**: doesn't do anything. Requester's service is determined by authentication."
    )
    enabled = graphene.Boolean()


class AddServiceConnectionMutation(relay.ClientIDMutation):
    class Input:
        service_connection = ServiceConnectionInput(required=True)

    service_connection = graphene.Field(ServiceConnectionType)

    @classmethod
    @login_and_service_required
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        service_connection_data = input.pop("service_connection")
        service = info.context.service

        try:
            service_connection = ServiceConnection.objects.create(
                profile=info.context.user.profile,
                service=service,
                enabled=service_connection_data.get("enabled", True),
            )
        except IntegrityError:
            raise ServiceAlreadyExistsError("Service connection already exists")
        return AddServiceConnectionMutation(service_connection=service_connection)


class Query(graphene.ObjectType):
    services = DjangoFilterConnectionField(
        ServiceNode,
        description="Search for services. The results are paged using Relay.",
    )


class Mutation(graphene.ObjectType):
    add_service_connection = AddServiceConnectionMutation.Field(
        description="Connect the currently authenticated user's profile to the given service.\n\nRequires "
        "authentication.\n\nPossible error codes:\n\n* `SERVICE_CONNECTION_ALREADY_EXISTS_ERROR`: "
        "Returned if the currently authenticated user's profile is already connected to the given service."
    )
