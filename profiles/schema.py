import graphene
from django.conf import settings
from django.db.models import CharField, Value
from django.db.models.functions import Concat
from django.utils.translation import override
from graphene_django.types import DjangoObjectType
from graphql_jwt.decorators import login_required
from munigeo.models import AdministrativeDivision
from thesaurus.models import Concept

from services.models import Service
from services.schema import ServiceType

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


class ProfileType(DjangoObjectType):
    class Meta:
        model = Profile
        fields = ("first_name", "last_name", "nickname", "image", "email", "phone")

    language = Language()
    contact_method = ContactMethod()
    services = graphene.List(ServiceType)
    concepts_of_interest = graphene.List(ConceptType)
    divisions_of_interest = graphene.List(AdministrativeDivisionType)

    def resolve_services(self, info, **kwargs):
        return Service.objects.filter(profile=self)

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


class Mutation(graphene.ObjectType):
    update_profile = UpdateProfile.Field()
