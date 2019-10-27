import graphene
from graphene_django.types import DjangoObjectType
from graphql_jwt.decorators import login_required

from .consts import SERVICE_TYPES
from .models import Service


class ServiceType(DjangoObjectType):
    type = graphene.Field(graphene.String, source="service_type")

    class Meta:
        model = Service
        fields = ("created_at",)


AllowedServiceType = graphene.Enum(
    "type", [(st[0].upper(), st[0]) for st in SERVICE_TYPES]
)


class ServiceInput(graphene.InputObjectType):
    type = AllowedServiceType()


class AddService(graphene.Mutation):
    class Arguments:
        service = ServiceInput(required=True)

    service = graphene.Field(ServiceType)

    @login_required
    def mutate(self, info, **kwargs):
        service_data = kwargs.pop("service")
        service_type = service_data.get("type")
        service, created = Service.objects.get_or_create(
            profile=info.context.user.profile, service_type=service_type
        )
        service.save()

        return AddService(service=service)


class Mutation(graphene.ObjectType):
    add_service = AddService.Field()
