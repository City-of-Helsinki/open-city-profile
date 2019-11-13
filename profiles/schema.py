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

from profiles.decorators import staff_required
from services.consts import SERVICE_TYPES
from services.models import Service, ServiceConnection
from services.schema import AllowedServiceType, ServiceConnectionType

from .models import Address, Contact, Email, Phone, Profile


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


class ContactType(DjangoObjectType):
    class Meta:
        model = Contact
        fields = ("primary",)


class EmailType(ContactType):
    class Meta:
        model = Email
        fields = ("email_type", "primary", "email")


class PhoneType(ContactType):
    class Meta:
        model = Phone
        fields = ("phone_type", "primary", "phone")


class AddressType(ContactType):
    class Meta:
        model = Address
        fields = ("address_type", "primary", "email")


class ProfileType(DjangoObjectType):
    class Meta:
        model = Profile
        fields = ("first_name", "last_name", "nickname", "image", "language")
        interfaces = (relay.Node,)
        connection_class = ProfilesConnection
        filterset_class = ProfileFilter

    emails = graphene.List(EmailType)
    phones = graphene.List(PhoneType)
    addresses = graphene.List(AddressType)
    language = Language()
    contact_method = ContactMethod()
    service_connections = DjangoFilterConnectionField(ServiceConnectionType)
    concepts_of_interest = graphene.List(ConceptType)
    divisions_of_interest = graphene.List(AdministrativeDivisionType)

    def resolve_service_connections(self, info, **kwargs):
        return ServiceConnection.objects.filter(profile=self)

    def resolve_emails(self, info, **kwargs):
        return Email.objects.filter(profile=self)

    def resolve_phones(self, info, **kwargs):
        return Phone.objects.filter(profile=self)

    def resolve_addresses(self, info, **kwargs):
        return Address.objects.filter(profile=self)

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
        email, created = Email.objects.get_or_create(profile=profile)
        email.email = profile_data.email
        email.primary = True
        email.save()
        phone, created = Phone.objects.get_or_create(profile=profile)
        phone.phone = profile_data.phone
        phone.primary = True
        phone.save()

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
    profile = graphene.Field(
        ProfileType,
        id=graphene.Argument(graphene.ID, required=True),
        serviceType=graphene.Argument(AllowedServiceType, required=True),
    )
    my_profile = graphene.Field(ProfileType)
    concepts_of_interest = graphene.List(ConceptType)
    divisions_of_interest = graphene.List(AdministrativeDivisionType)
    profiles = DjangoFilterConnectionField(
        ProfileType, serviceType=graphene.Argument(AllowedServiceType, required=True)
    )

    @staff_required(required_permission="view")
    def resolve_profile(self, info, **kwargs):
        try:
            service = Service.objects.get(service_type=kwargs["serviceType"])
            return (
                Profile.objects.filter(serviceconnection__service=service)
                .prefetch_related("concepts_of_interest", "divisions_of_interest")
                .get(pk=relay.Node.from_global_id(kwargs["id"])[1])
            )
        except Profile.DoesNotExist:
            raise GraphQLError(_("Profile not found!"))
        except Service.DoesNotExist:
            raise GraphQLError(_("Service not found!"))

    @login_required
    def resolve_my_profile(self, info, **kwargs):
        return (
            Profile.objects.filter(user=info.context.user)
            .prefetch_related("concepts_of_interest", "divisions_of_interest")
            .first()
        )

    def resolve_concepts_of_interest(self, info, **kwargs):
        return Concept.objects.all()

    def resolve_divisions_of_interest(self, info, **kwargs):
        return AdministrativeDivision.objects.filter(division_of_interest__isnull=False)

    @staff_required(required_permission="view")
    def resolve_profiles(self, info, **kwargs):
        return Profile.objects.filter(
            serviceconnection__service__service_type=kwargs["serviceType"]
        )


class Mutation(graphene.ObjectType):
    update_profile = UpdateProfile.Field()
