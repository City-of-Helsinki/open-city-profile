import graphene
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.translation import override
from django_filters import CharFilter, FilterSet, OrderingFilter
from graphene import relay
from graphene_django.filter import DjangoFilterConnectionField
from graphene_django.types import DjangoObjectType
from graphene_federation import key
from graphql_jwt.decorators import login_required
from munigeo.models import AdministrativeDivision
from thesaurus.models import Concept

from open_city_profile.exceptions import (
    APINotImplementedError,
    CannotDeleteProfileWhileServiceConnectedError,
    ProfileDoesNotExistError,
    TokenExpiredError,
)
from profiles.decorators import staff_required
from services.enums import ServiceType
from services.models import Service, ServiceConnection
from services.schema import AllowedServiceType, ServiceConnectionType
from youths.schema import (
    CreateMyYouthProfileMutation,
    UpdateMyYouthProfileMutation,
    YouthProfileFields,
    YouthProfileType,
)

from .enums import AddressType, EmailType, PhoneType
from .models import Address, ClaimToken, Contact, Email, Phone, Profile, SensitiveData
from .utils import create_nested, delete_nested, update_nested

AllowedEmailType = graphene.Enum.from_enum(
    EmailType, description=lambda e: e.label if e else ""
)
AllowedPhoneType = graphene.Enum.from_enum(
    PhoneType, description=lambda e: e.label if e else ""
)
AllowedAddressType = graphene.Enum.from_enum(
    AddressType, description=lambda e: e.label if e else ""
)


def get_claimable_profile(token=None):
    claim_token = ClaimToken.objects.get(token=token)
    if claim_token.expires_at and claim_token.expires_at < timezone.now():
        raise TokenExpiredError("Token for claiming this profile has expired")
    return Profile.objects.filter(user=None).get(claim_tokens__id=claim_token.id)


def update_profile(profile, profile_data):
    nested_to_create = [
        (Email, profile_data.pop("add_emails", [])),
        (Phone, profile_data.pop("add_phones", [])),
        (Address, profile_data.pop("add_addresses", [])),
    ]
    nested_to_update = [
        (Email, profile_data.pop("update_emails", [])),
        (Phone, profile_data.pop("update_phones", [])),
        (Address, profile_data.pop("update_addresses", [])),
    ]
    nested_to_delete = [
        (Email, profile_data.pop("remove_emails", [])),
        (Phone, profile_data.pop("remove_phones", [])),
        (Address, profile_data.pop("remove_addresses", [])),
    ]

    for field, value in profile_data.items():
        setattr(profile, field, value)
    profile.save()

    for model, data in nested_to_create:
        create_nested(model, profile, data)

    for model, data in nested_to_update:
        update_nested(model, profile, data)

    for model, data in nested_to_delete:
        delete_nested(model, profile, data)


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

    def resolve_total_count(self, info, **kwargs):
        return self.iterable.model.objects.count()


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


class ContactNode(DjangoObjectType):
    class Meta:
        model = Contact
        fields = ("primary",)
        filter_fields = []
        interfaces = (relay.Node,)


class EmailNode(ContactNode):
    email_type = AllowedEmailType()

    class Meta:
        model = Email
        fields = ("id", "email_type", "primary", "email")
        filter_fields = []
        interfaces = (relay.Node,)


class PhoneNode(ContactNode):
    phone_type = AllowedPhoneType()

    class Meta:
        model = Phone
        fields = ("id", "phone_type", "primary", "phone")
        filter_fields = []
        interfaces = (relay.Node,)


class AddressNode(ContactNode):
    address_type = AllowedAddressType()

    class Meta:
        model = Address
        fields = (
            "id",
            "address_type",
            "primary",
            "address",
            "postal_code",
            "city",
            "country_code",
        )
        filter_fields = []
        interfaces = (relay.Node,)


class SensitiveDataNode(DjangoObjectType):
    class Meta:
        model = SensitiveData
        fields = ("ssn",)
        interfaces = (relay.Node,)


@key(fields="id")
class ProfileNode(DjangoObjectType):
    class Meta:
        model = Profile
        fields = ("first_name", "last_name", "nickname", "image", "language")
        interfaces = (relay.Node,)
        connection_class = ProfilesConnection
        filterset_class = ProfileFilter

    primary_email = graphene.Field(
        EmailNode,
        description="Convenience field for the email which is marked as primary.",
    )
    primary_phone = graphene.Field(
        PhoneNode,
        description="Convenience field for the phone which is marked as primary.",
    )
    primary_address = graphene.Field(
        AddressNode,
        description="Convenience field for the address which is marked as primary.",
    )
    emails = DjangoFilterConnectionField(
        EmailNode, description="List of email addresses of the profile."
    )
    phones = DjangoFilterConnectionField(
        PhoneNode, description="List of phone numbers of the profile."
    )
    addresses = DjangoFilterConnectionField(
        AddressNode, description="List of addresses of the profile."
    )
    sensitivedata = graphene.Field(
        SensitiveDataNode,
        description="Data that is consider to be sensitive e.g. social security number",
    )
    language = Language()
    contact_method = ContactMethod()
    service_connections = DjangoFilterConnectionField(
        ServiceConnectionType, description="List of the profile's connected services."
    )
    youth_profile = graphene.Field(
        YouthProfileType, description="The Youth membership data of the profile."
    )

    def resolve_service_connections(self, info, **kwargs):
        return ServiceConnection.objects.filter(profile=self)

    def resolve_primary_email(self, info, **kwargs):
        return Email.objects.filter(profile=self, primary=True).first()

    def resolve_primary_phone(self, info, **kwargs):
        return Phone.objects.filter(profile=self, primary=True).first()

    def resolve_primary_address(self, info, **kwargs):
        return Address.objects.filter(profile=self, primary=True).first()

    def resolve_emails(self, info, **kwargs):
        return Email.objects.filter(profile=self)

    def resolve_phones(self, info, **kwargs):
        return Phone.objects.filter(profile=self)

    def resolve_addresses(self, info, **kwargs):
        return Address.objects.filter(profile=self)

    def resolve_sensitivedata(self, info, **kwargs):
        service = (
            Service.objects.filter(service_type=info.context.service_type).first()
            if hasattr(info.context, "service_type")
            else None
        )
        if (
            not service and info.context.user == self.user
        ) or info.context.user.has_perm("can_view_sensitivedata", service):
            return self.sensitivedata
        else:
            # TODO: We should return PermissionDenied as a partial error here.
            return None


class EmailInput(graphene.InputObjectType):
    id = graphene.ID()
    email = graphene.String(description="Email address.")
    email_type = AllowedEmailType(description="Email address type.", required=True)
    primary = graphene.Boolean(description="Is this primary mail address.")


class PhoneInput(graphene.InputObjectType):
    id = graphene.ID()
    phone = graphene.String(description="Phone number.", required=True)
    phone_type = AllowedPhoneType(description="Phone number type.", required=True)
    primary = graphene.Boolean(description="Is this primary phone number.")


class AddressInput(graphene.InputObjectType):
    id = graphene.ID()
    address = graphene.String(description="Street address.", required=True)
    postal_code = graphene.String(description="Postal code.", required=True)
    city = graphene.String(description="City.", required=True)
    country_code = graphene.String(description="Country code")
    address_type = AllowedAddressType(description="Address type.", required=True)
    primary = graphene.Boolean(description="Is this primary address.")


class ProfileInput(graphene.InputObjectType):
    first_name = graphene.String(description="First name.")
    last_name = graphene.String(description="Last name.")
    nickname = graphene.String(description="Nickname.")
    image = graphene.String(description="Profile image.")
    language = Language(description="Language.")
    contact_method = ContactMethod(description="Contact method.")
    add_emails = graphene.List(EmailInput, description="Add emails to profile.")
    update_emails = graphene.List(EmailInput, description="Update profile emails.")
    remove_emails = graphene.List(
        graphene.ID, description="Remove emails from profile."
    )
    add_phones = graphene.List(PhoneInput, description="Add phone numbers to profile.")
    update_phones = graphene.List(
        PhoneInput, description="Update profile phone numbers."
    )
    remove_phones = graphene.List(
        graphene.ID, description="Remove phone numbers from profile."
    )
    add_addresses = graphene.List(AddressInput, description="Add addresses to profile.")
    update_addresses = graphene.List(
        AddressInput, description="Update profile addresses."
    )
    remove_addresses = graphene.List(
        graphene.ID, description="Remove addresses from profile."
    )
    youth_profile = graphene.InputField(YouthProfileFields)


class CreateMyProfileMutation(relay.ClientIDMutation):
    class Input:
        profile = ProfileInput(required=True)

    profile = graphene.Field(ProfileNode)

    @classmethod
    @login_required
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        profile_data = input.pop("profile")
        youth_profile_data = profile_data.pop("youth_profile", None)
        nested_to_create = [
            (Email, profile_data.pop("add_emails", [])),
            (Phone, profile_data.pop("add_phones", [])),
            (Address, profile_data.pop("add_addresses", [])),
        ]

        profile = Profile.objects.create(user=info.context.user)
        for field, value in profile_data.items():
            setattr(profile, field, value)
        profile.save()

        for model, data in nested_to_create:
            create_nested(model, profile, data)

        if youth_profile_data:
            CreateMyYouthProfileMutation().mutate_and_get_payload(
                root, info, youth_profile=youth_profile_data
            )

        return CreateMyProfileMutation(profile=profile)


class UpdateMyProfileMutation(relay.ClientIDMutation):
    class Input:
        profile = ProfileInput(required=True)

    profile = graphene.Field(ProfileNode)

    @classmethod
    @login_required
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        profile_data = input.pop("profile")
        youth_profile_data = profile_data.pop("youth_profile", None)
        profile = Profile.objects.get(user=info.context.user)
        update_profile(profile, profile_data)

        if youth_profile_data:
            UpdateMyYouthProfileMutation().mutate_and_get_payload(
                root, info, youth_profile=youth_profile_data
            )

        return UpdateMyProfileMutation(profile=profile)


class ClaimProfileMutation(relay.ClientIDMutation):
    class Input:
        token = graphene.Argument(graphene.UUID, required=True)
        profile = ProfileInput()

    profile = graphene.Field(ProfileNode)

    @classmethod
    @login_required
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        profile_to_claim = get_claimable_profile(token=input["token"])
        if Profile.objects.filter(user=info.context.user).exists():
            # Logged in user has a profile
            # TODO: Case with existing profile waiting for final spec, ticket:
            #       https://helsinkisolutionoffice.atlassian.net/browse/OM-385
            raise APINotImplementedError(
                "Claiming a profile with existing profile not yet implemented"
            )
        else:
            # Logged in user has no profile, let's use claimed profile
            update_profile(profile_to_claim, input["profile"])
            profile_to_claim.user = info.context.user
            profile_to_claim.save()
            profile_to_claim.claim_tokens.all().delete()
            return ClaimProfileMutation(profile=profile_to_claim)


class DeleteMyProfileMutation(relay.ClientIDMutation):
    @classmethod
    @login_required
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        try:
            profile = Profile.objects.get(user=info.context.user)
        except Profile.DoesNotExist:
            raise ProfileDoesNotExistError("Profile does not exist")

        # TODO: Here we should check whether profile can be
        #       actually removed. Waiting for spec for this.
        #       For now just check if user has BERTH.
        #
        #       More info:
        #       https://helsinkisolutionoffice.atlassian.net/browse/OM-248
        if profile.service_connections.filter(
            service__service_type=ServiceType.BERTH
        ).exists():
            raise CannotDeleteProfileWhileServiceConnectedError(
                "Cannot delete profile while service BERTH still connected"
            )

        profile.delete()
        return DeleteMyProfileMutation()


class Query(graphene.ObjectType):
    # TODO: Add the complete list of error codes
    profile = graphene.Field(
        ProfileNode,
        id=graphene.Argument(graphene.ID, required=True),
        serviceType=graphene.Argument(AllowedServiceType, required=True),
        description="Get profile by profile ID.\n\nRequires `staff` credentials for the service given in "
        "`serviceType`. The profile must have an active connection to the given `serviceType`, otherwise "
        "it will not be returned.\n\nPossible error codes:\n\n* `TODO`",
    )
    # TODO: Add the complete list of error codes
    my_profile = graphene.Field(
        ProfileNode,
        description="Get the profile belonging to the currently authenticated user.\n\nRequires authentication.\n\n"
        "Possible error codes:\n\n* `TODO`",
    )
    # TODO: Change the description when the download API is implemented to fetch data from services as well
    # TODO: Add the complete list of error codes
    download_my_profile = graphene.JSONString(
        description="Get the user information stored in the profile as machine readable JSON.\n\nRequires "
        "authentication.\n\nPossible error codes:\n\n* `TODO`"
    )
    # TODO: Add the complete list of error codes
    profiles = DjangoFilterConnectionField(
        ProfileNode,
        serviceType=graphene.Argument(AllowedServiceType, required=True),
        description="Search for profiles. The results are filtered based on the given parameters. The results are "
        "paged using Relay.\n\nRequires `staff` credentials for the service given in "
        "`serviceType`. The profiles must have an active connection to the given `serviceType`, otherwise "
        "they will not be returned.\n\nPossible error codes:\n\n* `TODO`",
    )
    # TODO: Add the complete list of error codes
    claimable_profile = graphene.Field(
        ProfileNode,
        token=graphene.Argument(graphene.UUID, required=True),
        description="Get a profile by the given `token` so that it may be linked to the currently authenticated user. "
        "The profile must not already have a user account linked to it.\n\nRequires authentication.\n\n"
        "Possible error codes:\n\n* `TODO`",
    )

    @staff_required(required_permission="view")
    def resolve_profile(self, info, **kwargs):
        service = Service.objects.get(service_type=kwargs["serviceType"])
        # serviceType passed on to the sub resolvers
        info.context.service_type = kwargs["serviceType"]
        return Profile.objects.filter(service_connections__service=service).get(
            pk=relay.Node.from_global_id(kwargs["id"])[1]
        )

    @login_required
    def resolve_my_profile(self, info, **kwargs):
        return Profile.objects.filter(user=info.context.user).first()

    @staff_required(required_permission="view")
    def resolve_profiles(self, info, **kwargs):
        # serviceType passed on to the sub resolvers
        info.context.service_type = kwargs["serviceType"]
        return Profile.objects.filter(
            service_connections__service__service_type=kwargs["serviceType"]
        )

    @login_required
    def resolve_claimable_profile(self, info, **kwargs):
        # TODO: Complete error handling for this OM-297
        return get_claimable_profile(token=kwargs["token"])

    @login_required
    def resolve_download_my_profile(self, info, **kwargs):
        return Profile.objects.filter(user=info.context.user).first().serialize()


class Mutation(graphene.ObjectType):
    # TODO: Add the complete list of error codes
    create_my_profile = CreateMyProfileMutation.Field(
        description="Creates a new profile based on the given data. The new profile is linked to the currently "
        "authenticated user.\n\nOne or several of the following is possible to add:\n\n* Email\n"
        "* Address\n* Phone\n\nIf youth data is given, a youth profile will also be created and linked "
        "to the profile.\n\nRequires authentication.\n\nPossible error codes:\n\n* `TODO`"
    )
    # TODO: Add the complete list of error codes
    update_my_profile = UpdateMyProfileMutation.Field(
        description="Updates the profile which is linked to the currently authenticated user based on the given data."
        "\n\nOne or several of the following is possible to add, modify or remove:\n\n* Email\n* Address"
        "\n* Phone\n\nIf youth data is given, a youth profile will also be created and linked "
        "to the profile **or** the existing youth profile will be updated if the profile is already "
        "linked to a youth profile.\n\nRequires authentication.\n\nPossible error codes:\n\n* `TODO`"
    )
    # TODO: Add the complete list of error codes
    delete_my_profile = DeleteMyProfileMutation.Field(
        description="Deletes the data of the profile which is linked to the currently authenticated user.\n\n"
        "Requires authentication.\n\nPossible error codes:\n\n* "
        "`CANNOT_DELETE_PROFILE_WHILE_SERVICE_CONNECTED_ERROR`: Returned if the profile is connected to "
        "Berth service.\n\n* `PROFILE_DOES_NOT_EXIST_ERROR`: Returned if there is no profile linked to "
        "the currently authenticated user.\n\n* `TODO`"
    )
    # TODO: Add the complete list of error codes
    claim_profile = ClaimProfileMutation.Field(
        description="Fetches a profile which has no linked user account yet by the given token and links the profile "
        "to the currently authenticated user's account.\n\n**NOTE:** This functionality is not implemented"
        " completely. If the authenticated user already has a profile, this mutation will respond with "
        "an error.\n\nPossible error codes:\n\n* `API_NOT_IMPLEMENTED_ERROR`: Returned if the currently "
        "authenticated user already has a profile.\n\n* `TODO`"
    )
