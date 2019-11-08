import graphene
from django.conf import settings
from django.db.models import CharField, Value
from django.db.models.functions import Concat
from django.utils.translation import override
from django.utils.translation import ugettext_lazy as _
from django_filters import CharFilter, FilterSet, OrderingFilter
from graphene import relay
from graphene_django.filter import DjangoFilterConnectionField
from graphene_django.types import DjangoObjectType
from graphql import GraphQLError
from graphql_jwt.decorators import login_required
from munigeo.models import AdministrativeDivision
from thesaurus.models import Concept

from services.consts import SERVICE_TYPES
from services.models import ServiceConnection
from services.schema import ServiceConnectionType

from .models import Profile


class ConceptType(DjangoObjectType):
    class Meta:
        model = Concept
        fields = ("code",)

    vocabulary = graphene.String()
    label = graphene.String()

    def resolve_vocabulary(self, info, **kwargs):
        return self.vocabulary.prefix


class AdministrativeDivisionType(DjangoObjectType):
    class Meta:
        model = AdministrativeDivision
        fields = ("children", "origin_id", "ocd_id", "municipality")

    type = graphene.String()
    name = graphene.String()

    def resolve_children(self, info, **kwargs):
        return self.children.filter(type__type="sub_district")

    def resolve_type(self, info, **kwargs):
        return self.type.type


with override("en"):
    Language = graphene.Enum(
        "Language", [(l[1].upper(), l[0]) for l in settings.LANGUAGES]
    )
    ContactMethod = graphene.Enum(
        "ContactMethod", [(cm[1].upper(), cm[0]) for cm in settings.CONTACT_METHODS]
    )


class ProfilesConnection(graphene.Connection):
    class Meta:
        abstract = True

    count = graphene.Int()
    total_count = graphene.Int()

    def resolve_count(self, info):
        return self.length

    def resolve_total_count(self, info):
        return self.iterable.model.objects.filter(
            serviceconnection__service__service_type=SERVICE_TYPES[1][0]
        ).count()


class ProfileFilter(FilterSet):
    class Meta:
        model = Profile
        fields = ("first_name", "last_name", "nickname", "email", "phone", "language")

    first_name = CharFilter(lookup_expr="icontains")
    last_name = CharFilter(lookup_expr="icontains")
    nickname = CharFilter(lookup_expr="icontains")
    email = CharFilter(lookup_expr="icontains")
    phone = CharFilter(lookup_expr="icontains")
    language = CharFilter()
    order_by = OrderingFilter(
        fields=(
            ("first_name", "firstName"),
            ("last_name", "lastName"),
            ("nickname", "nickname"),
            ("email", "email"),
            ("phone", "phone"),
            ("language", "language"),
        )
    )


class ProfileType(DjangoObjectType):
    class Meta:
        model = Profile
        fields = (
            "first_name",
            "last_name",
            "nickname",
            "image",
            "email",
            "phone",
            "language",
        )
        interfaces = (relay.Node,)
        connection_class = ProfilesConnection
        filterset_class = ProfileFilter

    language = Language()
    contact_method = ContactMethod()
    service_connections = DjangoFilterConnectionField(ServiceConnectionType)
    concepts_of_interest = graphene.List(ConceptType)
    divisions_of_interest = graphene.List(AdministrativeDivisionType)

    def resolve_service_connections(self, info, **kwargs):
        return ServiceConnection.objects.filter(profile=self)

    def resolve_concepts_of_interest(self, info, **kwargs):
        return self.concepts_of_interest.all()

    def resolve_divisions_of_interest(self, info, **kwargs):
        return self.divisions_of_interest.all()


class ProfileInput(graphene.InputObjectType):
    first_name = graphene.String()
    last_name = graphene.String()
    nickname = graphene.String()
    image = graphene.String()
    email = graphene.String()
    phone = graphene.String()
    language = Language()
    contact_method = ContactMethod()
    concepts_of_interest = graphene.List(graphene.String)
    divisions_of_interest = graphene.List(graphene.String)


class UpdateProfile(graphene.Mutation):
    class Arguments:
        profile = ProfileInput(required=True)

    profile = graphene.Field(ProfileType)

    @login_required
    def mutate(self, info, **kwargs):
        profile_data = kwargs.pop("profile")
        concepts_of_interest = profile_data.pop("concepts_of_interest", [])
        divisions_of_interest = profile_data.pop("divisions_of_interest", [])
        profile, created = Profile.objects.get_or_create(user=info.context.user)
        for field, value in profile_data.items():
            setattr(profile, field, value)
        profile.save()

        cois = Concept.objects.annotate(
            identifier=Concat(
                "vocabulary__prefix", Value(":"), "code", output_field=CharField()
            )
        ).filter(identifier__in=concepts_of_interest)
        profile.concepts_of_interest.set(cois)
        ads = AdministrativeDivision.objects.filter(ocd_id__in=divisions_of_interest)
        profile.divisions_of_interest.set(ads)

        return UpdateProfile(profile=profile)


class Query(graphene.ObjectType):
    profile = graphene.Field(ProfileType)
    concepts_of_interest = graphene.List(ConceptType)
    divisions_of_interest = graphene.List(AdministrativeDivisionType)
    berth_profiles = DjangoFilterConnectionField(ProfileType)

    @login_required
    def resolve_profile(self, info, **kwargs):
        return (
            Profile.objects.filter(user=info.context.user)
            .prefetch_related("concepts_of_interest", "divisions_of_interest")
            .first()
        )

    def resolve_concepts_of_interest(self, info, **kwargs):
        return Concept.objects.all()

    def resolve_divisions_of_interest(self, info, **kwargs):
        return AdministrativeDivision.objects.filter(division_of_interest__isnull=False)

    @login_required
    def resolve_berth_profiles(self, info, **kwargs):
        # TODO: authorization and consent checks
        # authorized user with real django groups instead of superuser
        # check whether the consent is given for the profile
        if info.context.user.is_superuser:
            return Profile.objects.filter(
                serviceconnection__service__service_type=SERVICE_TYPES[1][0]
            )
        raise GraphQLError(_("You do not have permission to perform this action."))


class Mutation(graphene.ObjectType):
    update_profile = UpdateProfile.Field()
