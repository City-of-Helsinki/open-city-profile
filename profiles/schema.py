from itertools import chain

import graphene
import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import F, OuterRef, Subquery
from django.utils import timezone
from django.utils.translation import override
from django.utils.translation import ugettext_lazy as _
from django_filters import (
    BooleanFilter,
    CharFilter,
    ChoiceFilter,
    FilterSet,
    OrderingFilter,
)
from graphene import relay
from graphene.utils.str_converters import to_snake_case
from graphene_django import DjangoConnectionField
from graphene_django.filter import DjangoFilterConnectionField
from graphene_django.types import DjangoObjectType
from graphene_federation import key
from graphql_jwt.decorators import login_required, permission_required
from munigeo.models import AdministrativeDivision
from thesaurus.models import Concept

from open_city_profile.exceptions import (
    APINotImplementedError,
    ConnectedServiceDeletionFailedError,
    ConnectedServiceDeletionNotAllowedError,
    MissingGDPRApiTokenError,
    ProfileDoesNotExistError,
    TokenExpiredError,
)
from open_city_profile.graphene import UUIDMultipleChoiceFilter
from open_city_profile.oidc import TunnistamoTokenExchange
from profiles.decorators import staff_required
from services.exceptions import MissingGDPRUrlException
from services.models import Service, ServiceConnection
from services.schema import AllowedServiceType, ServiceConnectionType
from subscriptions.schema import (
    SubscriptionInputType,
    SubscriptionNode,
    UpdateMySubscriptionMutation,
)

from .enums import AddressType, EmailType, PhoneType
from .models import (
    Address,
    ClaimToken,
    Contact,
    Email,
    Phone,
    Profile,
    SensitiveData,
    TemporaryReadAccessToken,
    VerifiedPersonalInformation,
    VerifiedPersonalInformationPermanentAddress,
    VerifiedPersonalInformationPermanentForeignAddress,
    VerifiedPersonalInformationTemporaryAddress,
)
from .utils import (
    create_nested,
    delete_nested,
    update_nested,
    user_has_staff_perms_to_view_profile,
)

User = get_user_model()

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


def update_sensitivedata(profile, sensitive_data):
    if hasattr(profile, "sensitivedata"):
        profile_sensitivedata = profile.sensitivedata
    else:
        profile_sensitivedata = SensitiveData(profile=profile)
    for field, value in sensitive_data.items():
        setattr(profile_sensitivedata, field, value)
    profile_sensitivedata.save()


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

    count = graphene.Int(required=True)
    total_count = graphene.Int(required=True)

    def resolve_count(self, info):
        return self.length

    def resolve_total_count(self, info, **kwargs):
        return self.iterable.model.objects.count()


class PrimaryContactInfoOrderingFilter(OrderingFilter):
    """Custom ordering filter

    This filter enables ordering profiles by primary contact info fields, for example by city of primary address.
    """

    # custom field definitions:
    # 0. custom field name (camel case format)
    # 1. field display text
    # 2. model with foreign key profile_id
    # 3. field name of the related model

    FIELDS = (
        ("primaryCity", "Primary City", Address, "city"),
        ("primaryPostalCode", "Primary Postal Code", Address, "postal_code"),
        ("primaryAddress", "Primary Address", Address, "address"),
        ("primaryCountryCode", "Primary Country Code", Address, "country_code"),
        ("primaryEmail", "Primary Email", Email, "email"),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # add ascending and descending custom orderings
        self.extra["choices"] += [(item[0], item[1]) for item in self.FIELDS]
        self.extra["choices"] += [
            (f"-{item[0]}", f"{item[1]} (Descending)") for item in self.FIELDS
        ]

    def filter(self, qs, values):
        def _get_field_data_by_field(fields, field):
            for f in fields:
                if f[0] == field:
                    return f
            return None

        # collect all the ascending/descending options and flatten the list
        options = chain(*[[item[0], f"-{item[0]}"] for item in self.FIELDS])

        for value in values or []:
            # match with all of our custom ascending and descending orderings
            if value in options:
                # get rid of leading "-" if ordering is descending
                field_name = value.replace("-", "")
                field_data = _get_field_data_by_field(self.FIELDS, field_name)
                # annotate the query with extra field and return the queryset
                annotation = {
                    to_snake_case(field_name): Subquery(
                        field_data[2]
                        .objects.filter(profile_id=OuterRef("id"), primary=True)
                        .values(field_data[3])
                    )
                }
                return qs.annotate(**annotation).order_by(to_snake_case(value))
        return super().filter(qs, values)


class ProfileFilter(FilterSet):
    class Meta:
        model = Profile
        fields = (
            "id",
            "first_name",
            "last_name",
            "nickname",
            "emails__email",
            "emails__email_type",
            "emails__primary",
            "emails__verified",
            "phones__phone",
            "phones__phone_type",
            "phones__primary",
            "addresses__address",
            "addresses__postal_code",
            "addresses__city",
            "addresses__country_code",
            "addresses__address_type",
            "addresses__primary",
            "language",
            "enabled_subscriptions",
        )

    id = UUIDMultipleChoiceFilter(
        label="Profile ids for selecting the exact profiles to return. "
        '**Note:** these are raw UUIDs, not "relay opaque identifiers".'
    )
    first_name = CharFilter(lookup_expr="icontains")
    last_name = CharFilter(lookup_expr="icontains")
    nickname = CharFilter(lookup_expr="icontains")
    emails__email = CharFilter(lookup_expr="icontains")
    emails__email_type = ChoiceFilter(choices=EmailType.choices())
    emails__primary = BooleanFilter()
    emails__verified = BooleanFilter()
    phones__phone = CharFilter(lookup_expr="icontains")
    phones__phone_type = ChoiceFilter(choices=PhoneType.choices())
    phones__primary = BooleanFilter()
    addresses__address = CharFilter(lookup_expr="icontains")
    addresses__postal_code = CharFilter(lookup_expr="icontains")
    addresses__city = CharFilter(lookup_expr="icontains")
    addresses__country_code = CharFilter(lookup_expr="icontains")
    addresses__address_type = ChoiceFilter(choices=AddressType.choices())
    addresses__primary = BooleanFilter()
    language = CharFilter()
    enabled_subscriptions = CharFilter(method="get_enabled_subscriptions")
    order_by = PrimaryContactInfoOrderingFilter(
        fields=(
            ("first_name", "firstName"),
            ("last_name", "lastName"),
            ("nickname", "nickname"),
            ("language", "language"),
        )
    )

    def get_enabled_subscriptions(self, queryset, name, value):
        """
        Custom filter to join the enabled of subscription with subscription type correctly
        """
        return queryset.filter(
            subscriptions__enabled=True, subscriptions__subscription_type__code=value
        )


class ContactNode(DjangoObjectType):
    class Meta:
        model = Contact
        fields = ("primary",)
        interfaces = (relay.Node,)


class EmailNode(ContactNode):
    email_type = AllowedEmailType()

    class Meta:
        model = Email
        fields = ("id", "email_type", "primary", "email", "verified")
        interfaces = (relay.Node,)


class PhoneNode(ContactNode):
    phone_type = AllowedPhoneType()

    class Meta:
        model = Phone
        fields = ("id", "phone_type", "primary", "phone")
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
        interfaces = (relay.Node,)


class VerifiedPersonalInformationAddressNode(graphene.ObjectType):
    street_address = graphene.String(
        required=True, description="Street address with possible house number etc."
    )
    postal_code = graphene.String(required=True, description="Postal code.")
    post_office = graphene.String(required=True, description="Post office.")


class VerifiedPersonalInformationForeignAddressNode(DjangoObjectType):
    class Meta:
        model = VerifiedPersonalInformationPermanentForeignAddress
        fields = ("street_address", "additional_address", "country_code")


class VerifiedPersonalInformationNode(DjangoObjectType):
    class Meta:
        model = VerifiedPersonalInformation
        fields = (
            "first_name",
            "last_name",
            "given_name",
            "national_identification_number",
            "email",
            "municipality_of_residence",
            "municipality_of_residence_number",
        )

    permanent_address = graphene.Field(
        VerifiedPersonalInformationAddressNode,
        description="The permanent residency address in Finland.",
    )

    temporary_address = graphene.Field(
        VerifiedPersonalInformationAddressNode,
        description="The temporary residency address in Finland.",
    )

    permanent_foreign_address = graphene.Field(
        VerifiedPersonalInformationForeignAddressNode,
        description="The temporary foreign (i.e. not in Finland) residency address.",
    )

    def resolve_permanent_address(self, info, **kwargs):
        try:
            return self.permanent_address
        except VerifiedPersonalInformationPermanentAddress.DoesNotExist:
            return None

    def resolve_temporary_address(self, info, **kwargs):
        try:
            return self.temporary_address
        except VerifiedPersonalInformationTemporaryAddress.DoesNotExist:
            return None

    def resolve_permanent_foreign_address(self, info, **kwargs):
        try:
            return self.permanent_foreign_address
        except VerifiedPersonalInformationPermanentForeignAddress.DoesNotExist:
            return None


class SensitiveDataNode(DjangoObjectType):
    class Meta:
        model = SensitiveData
        fields = ("id", "ssn")
        interfaces = (relay.Node,)


class SensitiveDataFields(graphene.InputObjectType):
    ssn = graphene.String(description="Social security number.")


class RestrictedProfileNode(DjangoObjectType):
    class Meta:
        model = Profile
        fields = ("first_name", "last_name", "nickname", "image", "language")
        interfaces = (relay.Node,)

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
    emails = DjangoConnectionField(
        EmailNode, description="List of email addresses of the profile."
    )
    phones = DjangoConnectionField(
        PhoneNode, description="List of phone numbers of the profile."
    )
    addresses = DjangoConnectionField(
        AddressNode, description="List of addresses of the profile."
    )
    language = Language()
    contact_method = ContactMethod()

    def resolve_primary_email(self, info, **kwargs):
        return info.context.primary_email_for_profile_loader.load(self.id)

    def resolve_primary_phone(self, info, **kwargs):
        return info.context.primary_phone_for_profile_loader.load(self.id)

    def resolve_primary_address(self, info, **kwargs):
        return info.context.primary_address_for_profile_loader.load(self.id)

    def resolve_emails(self, info, **kwargs):
        return info.context.emails_by_profile_id_loader.load(self.id)

    def resolve_phones(self, info, **kwargs):
        return info.context.phones_by_profile_id_loader.load(self.id)

    def resolve_addresses(self, info, **kwargs):
        return info.context.addresses_by_profile_id_loader.load(self.id)


@key(fields="id")
class ProfileNode(RestrictedProfileNode):
    class Meta:
        model = Profile
        fields = ("first_name", "last_name", "nickname", "image", "language")
        interfaces = (relay.Node,)
        connection_class = ProfilesConnection
        filterset_class = ProfileFilter

    sensitivedata = graphene.Field(
        SensitiveDataNode,
        description="Data that is consider to be sensitive e.g. social security number",
    )
    service_connections = DjangoFilterConnectionField(
        ServiceConnectionType, description="List of the profile's connected services."
    )
    subscriptions = DjangoFilterConnectionField(SubscriptionNode)

    def resolve_service_connections(self, info, **kwargs):
        return ServiceConnection.objects.filter(profile=self)

    def resolve_sensitivedata(self, info, **kwargs):
        service = getattr(info.context, "service", None)
        if (
            not service and info.context.user == self.user
        ) or info.context.user.has_perm("can_view_sensitivedata", service):
            return self.sensitivedata
        else:
            # TODO: We should return PermissionDenied as a partial error here.
            return None

    @login_required
    def __resolve_reference(self, info, **kwargs):
        profile = graphene.Node.get_node_from_global_id(
            info, self.id, only_type=ProfileNode
        )
        if not profile:
            return None

        user = info.context.user
        if user == profile.user or user_has_staff_perms_to_view_profile(user, profile):
            return profile
        else:
            raise PermissionDenied(
                _("You do not have permission to perform this action.")
            )


class ProfileWithVerifiedPersonalInformationNode(ProfileNode):
    class Meta:
        model = Profile
        fields = ("first_name", "last_name", "nickname", "image", "language")
        interfaces = (relay.Node,)
        connection_class = ProfilesConnection
        filterset_class = ProfileFilter

    verified_personal_information = graphene.Field(
        VerifiedPersonalInformationNode,
        description="Personal information that has been verified to be true.",
    )

    def resolve_verified_personal_information(self, info, **kwargs):
        loa = info.context.user_auth.data.get("loa")
        if loa in ["substantial", "high"]:
            try:
                return self.verified_personal_information
            except VerifiedPersonalInformation.DoesNotExist:
                return None
        else:
            raise PermissionDenied(
                "No permission to read verified personal information."
            )


class TemporaryReadAccessTokenNode(DjangoObjectType):
    class Meta:
        model = TemporaryReadAccessToken
        fields = ("token",)

    expires_at = graphene.DateTime()

    def resolve_expires_at(self, info, **kwargs):
        return self.expires_at()


class EmailInput(graphene.InputObjectType):
    primary = graphene.Boolean(description="Is this primary mail address.")


class CreateEmailInput(EmailInput):
    email = graphene.String(description="Email address.", required=True)
    email_type = AllowedEmailType(description="Email address type.", required=True)


class UpdateEmailInput(EmailInput):
    id = graphene.ID(required=True)
    email = graphene.String(description="Email address.")
    email_type = AllowedEmailType(description="Email address type.")


class PhoneInput(graphene.InputObjectType):
    primary = graphene.Boolean(description="Is this primary phone number.")


class CreatePhoneInput(PhoneInput):
    phone = graphene.String(description="Phone number.", required=True)
    phone_type = AllowedPhoneType(description="Phone number type.", required=True)


class UpdatePhoneInput(PhoneInput):
    id = graphene.ID(required=True)
    phone = graphene.String(description="Phone number.")
    phone_type = AllowedPhoneType(description="Phone number type.")


class AddressInput(graphene.InputObjectType):
    country_code = graphene.String(description="Country code")
    primary = graphene.Boolean(description="Is this primary address.")


class CreateAddressInput(AddressInput):
    address = graphene.String(description="Street address.", required=True)
    postal_code = graphene.String(description="Postal code.", required=True)
    city = graphene.String(description="City.", required=True)
    address_type = AllowedAddressType(description="Address type.", required=True)


class UpdateAddressInput(AddressInput):
    id = graphene.ID(required=True)
    address = graphene.String(description="Street address.")
    postal_code = graphene.String(description="Postal code.")
    city = graphene.String(description="City.")
    address_type = AllowedAddressType(description="Address type.")


class ProfileInputBase(graphene.InputObjectType):
    first_name = graphene.String(description="First name.")
    last_name = graphene.String(description="Last name.")
    nickname = graphene.String(description="Nickname.")
    image = graphene.String(description="Profile image.")
    language = Language(description="Language.")
    contact_method = ContactMethod(description="Contact method.")
    add_emails = graphene.List(CreateEmailInput, description="Add emails to profile.")
    add_phones = graphene.List(
        CreatePhoneInput, description="Add phone numbers to profile."
    )
    add_addresses = graphene.List(
        CreateAddressInput, description="Add addresses to profile."
    )
    subscriptions = graphene.List(SubscriptionInputType)
    sensitivedata = graphene.InputField(SensitiveDataFields)


class ProfileInput(ProfileInputBase):
    update_emails = graphene.List(
        UpdateEmailInput, description="Update profile emails."
    )
    remove_emails = graphene.List(
        graphene.ID, description="Remove emails from profile."
    )
    update_phones = graphene.List(
        UpdatePhoneInput, description="Update profile phone numbers."
    )
    remove_phones = graphene.List(
        graphene.ID, description="Remove phone numbers from profile."
    )
    update_addresses = graphene.List(
        UpdateAddressInput, description="Update profile addresses."
    )
    remove_addresses = graphene.List(
        graphene.ID, description="Remove addresses from profile."
    )


class CreateMyProfileMutation(relay.ClientIDMutation):
    class Input:
        profile = ProfileInput(required=True)

    profile = graphene.Field(ProfileNode)

    @classmethod
    @login_required
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        profile_data = input.pop("profile")
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

        return CreateMyProfileMutation(profile=profile)


class CreateProfileInput(ProfileInputBase):
    """The following fields are deprecated:

* `update_emails`
* `remove_emails`
* `update_phones`
* `remove_phones`
* `update_addresses`
* `remove_addresses`

There's no replacement for these as these fields have never had any effect in the first place."""

    update_emails = graphene.List(
        UpdateEmailInput, description="DEPRECATED. Update profile emails."
    )
    remove_emails = graphene.List(
        graphene.ID, description="DEPRECATED. Remove emails from profile."
    )
    update_phones = graphene.List(
        UpdatePhoneInput, description="DEPRECATED. Update profile phone numbers."
    )
    remove_phones = graphene.List(
        graphene.ID, description="DEPRECATED. Remove phone numbers from profile."
    )
    update_addresses = graphene.List(
        UpdateAddressInput, description="DEPRECATED. Update profile addresses."
    )
    remove_addresses = graphene.List(
        graphene.ID, description="DEPRECATED. Remove addresses from profile."
    )


class CreateProfileMutation(relay.ClientIDMutation):
    class Input:
        service_type = graphene.Argument(
            AllowedServiceType,
            description="**DEPRECATED**: requester's service is determined by authentication, "
            "but for now it can still be overridden by this argument.",
        )
        profile = CreateProfileInput(required=True)

    profile = graphene.Field(ProfileNode)

    @classmethod
    @staff_required(required_permission="manage")
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        service = info.context.service
        profile_data = input.pop("profile")
        sensitivedata = profile_data.pop("sensitivedata", None)
        nested_to_create = [
            (Email, profile_data.pop("add_emails", [])),
            (Phone, profile_data.pop("add_phones", [])),
            (Address, profile_data.pop("add_addresses", [])),
        ]

        profile = Profile(**profile_data)
        profile.save()

        for model, data in nested_to_create:
            create_nested(model, profile, data)

        if sensitivedata:
            if info.context.user.has_perm("can_manage_sensitivedata", service):
                SensitiveData.objects.create(profile=profile, **sensitivedata)
                profile.refresh_from_db()
            else:
                raise PermissionDenied(
                    _("You do not have permission to perform this action.")
                )

        # create the service connection for the profile
        profile.service_connections.create(service=service)

        return CreateProfileMutation(profile=profile)


class VerifiedPersonalInformationAddressInput(graphene.InputObjectType):
    street_address = graphene.String(
        description="Street address with possible house number etc. Max length 1024 characters."
    )
    postal_code = graphene.String(
        description="Postal code. Max length 1024 characters."
    )
    post_office = graphene.String(
        description="Post office. Max length 1024 characters."
    )


class VerifiedPersonalInformationForeignAddressInput(graphene.InputObjectType):
    street_address = graphene.String(
        description="Street address or whatever is the _first part_ of the address. Max length 1024 characters."
    )
    additional_address = graphene.String(
        description="Additional address information, perhaps town, county, state, country etc. "
        "Max length 1024 characters."
    )
    country_code = graphene.String(
        description="An ISO 3166-1 country code. Max length 3 characters."
    )


class VerifiedPersonalInformationInput(graphene.InputObjectType):
    first_name = graphene.String(
        description="First name(s). Max length 1024 characters."
    )
    last_name = graphene.String(description="Last name. Max length 1024 characters.")
    given_name = graphene.String(
        description="The name the person is called with. Max length 1024 characters."
    )
    national_identification_number = graphene.String(
        description="Can be social security number or other person identifier. Max length 1024 characters."
    )
    email = graphene.String(description="Email. Max length 1024 characters.")
    municipality_of_residence = graphene.String(
        description="Official municipality of residence in Finland as a free form text. Max length 1024 characters."
    )
    municipality_of_residence_number = graphene.String(
        description="Official municipality of residence in Finland as an official number. Max length 4 characters."
    )
    permanent_address = graphene.InputField(
        VerifiedPersonalInformationAddressInput,
        description="The permanent residency address in Finland.",
    )
    temporary_address = graphene.InputField(
        VerifiedPersonalInformationAddressInput,
        description="The temporary residency address in Finland.",
    )
    permanent_foreign_address = graphene.InputField(
        VerifiedPersonalInformationForeignAddressInput,
        description="The temporary foreign (i.e. not in Finland) residency address.",
    )


class ProfileWithVerifiedPersonalInformationInput(graphene.InputObjectType):
    verified_personal_information = graphene.InputField(
        VerifiedPersonalInformationInput, required=True
    )


class CreateOrUpdateProfileWithVerifiedPersonalInformationMutationInput(
    graphene.InputObjectType
):
    user_id = graphene.UUID(
        required=True,
        description="The **user id** of the user the Profile is or will be associated with.",
    )
    service_client_id = graphene.String(
        description="Connect the profile to the service identified by this client id."
    )
    profile = graphene.InputField(
        ProfileWithVerifiedPersonalInformationInput, required=True
    )


class ProfileWithVerifiedPersonalInformationOutput(graphene.ObjectType):
    class Meta:
        interfaces = (relay.Node,)


class CreateOrUpdateProfileWithVerifiedPersonalInformationMutationPayload(
    graphene.ObjectType
):
    profile = graphene.Field(ProfileWithVerifiedPersonalInformationOutput)


class CreateOrUpdateProfileWithVerifiedPersonalInformationMutation(graphene.Mutation):
    class Arguments:
        input = CreateOrUpdateProfileWithVerifiedPersonalInformationMutationInput(
            required=True
        )

    Output = CreateOrUpdateProfileWithVerifiedPersonalInformationMutationPayload

    @staticmethod
    @permission_required("profiles.manage_verified_personal_information")
    @transaction.atomic
    def mutate(parent, info, input):
        user_id_input = input.pop("user_id")
        profile_input = input.pop("profile")
        verified_personal_information_input = profile_input.pop(
            "verified_personal_information"
        )

        address_types = [
            {"model": VerifiedPersonalInformationPermanentAddress},
            {"model": VerifiedPersonalInformationTemporaryAddress},
            {"model": VerifiedPersonalInformationPermanentForeignAddress},
        ]
        for address_type in address_types:
            address_type["name"] = address_type["model"].RELATED_NAME
            address_type["input"] = verified_personal_information_input.pop(
                address_type["name"], None
            )

        user, created = User.objects.get_or_create(uuid=user_id_input)

        profile, created = Profile.objects.get_or_create(user=user)

        information, created = VerifiedPersonalInformation.objects.update_or_create(
            profile=profile, defaults=verified_personal_information_input
        )

        for address_type in address_types:
            address_input = address_type["input"]
            if address_input:
                address_name = address_type["name"]
                address_model = address_type["model"]
                try:
                    address = getattr(information, address_name)
                    address.update(address_input)
                except address_model.DoesNotExist:
                    address = address_model.objects.create(
                        verified_personal_information=information, **address_input
                    )
                if address.is_empty():
                    address.delete()

        service_client_id = input.pop("service_client_id", None)
        if service_client_id:
            service = Service.objects.get(client_ids__client_id=service_client_id)
            profile.service_connections.update_or_create(
                service=service, defaults={"enabled": True}
            )

        return CreateOrUpdateProfileWithVerifiedPersonalInformationMutationPayload(
            profile=profile
        )


class UpdateMyProfileMutation(relay.ClientIDMutation):
    class Input:
        profile = ProfileInput(required=True)

    profile = graphene.Field(ProfileNode)

    @classmethod
    @login_required
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        profile_data = input.pop("profile")
        sensitive_data = profile_data.pop("sensitivedata", None)
        subscription_data = profile_data.pop("subscriptions", [])
        profile = Profile.objects.get(user=info.context.user)
        update_profile(profile, profile_data)

        if sensitive_data:
            update_sensitivedata(profile, sensitive_data)

        for subscription in subscription_data:
            UpdateMySubscriptionMutation().mutate_and_get_payload(
                root, info, subscription=subscription
            )

        return UpdateMyProfileMutation(profile=profile)


class UpdateProfileInput(ProfileInputBase):
    id = graphene.Argument(graphene.ID, required=True)
    update_emails = graphene.List(
        UpdateEmailInput, description="Update profile emails."
    )
    remove_emails = graphene.List(
        graphene.ID, description="Remove emails from profile."
    )
    update_phones = graphene.List(
        UpdatePhoneInput, description="Update profile phone numbers."
    )
    remove_phones = graphene.List(
        graphene.ID, description="Remove phone numbers from profile."
    )
    update_addresses = graphene.List(
        UpdateAddressInput, description="Update profile addresses."
    )
    remove_addresses = graphene.List(
        graphene.ID, description="Remove addresses from profile."
    )


class UpdateProfileMutation(relay.ClientIDMutation):
    class Input:
        service_type = graphene.Argument(
            AllowedServiceType,
            description="**DEPRECATED**: requester's service is determined by authentication, "
            "but for now it can still be overridden by this argument.",
        )
        profile = UpdateProfileInput(required=True)

    profile = graphene.Field(ProfileNode)

    @classmethod
    @staff_required(required_permission="manage")
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        service = info.context.service
        profile_data = input.get("profile")
        profile = graphene.Node.get_node_from_global_id(
            info, profile_data.pop("id"), only_type=ProfileNode
        )
        sensitive_data = profile_data.pop("sensitivedata", None)
        update_profile(profile, profile_data)

        if sensitive_data:
            if info.context.user.has_perm("can_manage_sensitivedata", service):
                update_sensitivedata(profile, sensitive_data)
            else:
                raise PermissionDenied(
                    _("You do not have permission to perform this action.")
                )

        return UpdateProfileMutation(profile=profile)


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
    class Input:
        authorization_code = graphene.String(
            required=True,
            description=(
                "OAuth/OIDC authoziation code. When obtaining the code, it is required to use "
                "service and operation specific GDPR API scopes."
            ),
        )

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        authorization_code = input["authorization_code"]

        try:
            profile = Profile.objects.get(user=info.context.user)
        except Profile.DoesNotExist:
            raise ProfileDoesNotExistError("Profile does not exist")

        if profile.service_connections.exists():
            tte = TunnistamoTokenExchange()
            api_tokens = tte.fetch_api_tokens(authorization_code)
            cls.delete_service_connections_for_profile(
                profile, api_tokens, dry_run=True
            )
            cls.delete_service_connections_for_profile(
                profile, api_tokens, dry_run=False
            )

        profile.delete()
        info.context.user.delete()
        return DeleteMyProfileMutation()

    @staticmethod
    def delete_service_connections_for_profile(profile, api_tokens, dry_run=False):
        failed_services = []

        for service_connection in profile.service_connections.all():
            service = service_connection.service

            if not service.gdpr_delete_scope:
                raise ConnectedServiceDeletionNotAllowedError(
                    f"Connected services: {service.name}"
                    f"does not have an API for removing data."
                )

            api_identifier = service.gdpr_delete_scope.rsplit(".", 1)[0]
            api_token = api_tokens.get(api_identifier, "")

            if not api_token:
                raise MissingGDPRApiTokenError(
                    f"Couldn't fetch an API token for service {service.name}."
                )

            try:
                service_connection.delete_gdpr_data(
                    api_token=api_token, dry_run=dry_run
                )
                if not dry_run:
                    service_connection.delete()
            except (requests.RequestException, MissingGDPRUrlException):
                failed_services.append(service.name)

        if failed_services:
            failed_services_string = ", ".join(failed_services)
            if dry_run:
                raise ConnectedServiceDeletionNotAllowedError(
                    f"Connected services: {failed_services_string} did not allow deleting the profile."
                )

            raise ConnectedServiceDeletionFailedError(
                f"Deletion failed for the following connected services: {failed_services_string}."
            )


class CreateMyProfileTemporaryReadAccessTokenMutation(relay.ClientIDMutation):
    temporary_read_access_token = graphene.Field(TemporaryReadAccessTokenNode)

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info):
        profile = Profile.objects.get(user=info.context.user)

        TemporaryReadAccessToken.objects.filter(
            profile=profile, created_at__gt=timezone.now() - F("validity_duration")
        ).delete()

        token = TemporaryReadAccessToken.objects.create(profile=profile)

        return CreateMyProfileTemporaryReadAccessTokenMutation(
            temporary_read_access_token=token
        )


class Query(graphene.ObjectType):
    # TODO: Add the complete list of error codes
    profile = graphene.Field(
        ProfileNode,
        id=graphene.Argument(graphene.ID, required=True),
        service_type=graphene.Argument(
            AllowedServiceType,
            description="**DEPRECATED**: requester's service is determined by authentication, "
            "but for now it can still be overridden by this argument.",
        ),
        description="Get profile by profile ID.\n\nRequires `staff` credentials for the requester's service."
        "The profile must have an active connection to the requester's service, otherwise "
        "it will not be returned.\n\nPossible error codes:\n\n* `TODO`",
    )
    # TODO: Add the complete list of error codes
    my_profile = graphene.Field(
        ProfileWithVerifiedPersonalInformationNode,
        description="Get the profile belonging to the currently authenticated user.\n\nRequires authentication.\n\n"
        "Possible error codes:\n\n* `TODO`",
    )
    # TODO: Change the description when the download API is implemented to fetch data from services as well
    # TODO: Add the complete list of error codes
    download_my_profile = graphene.JSONString(
        authorization_code=graphene.String(
            required=True,
            description=(
                "OAuth/OIDC authoziation code. When obtaining the code, it is required to use "
                "service and operation specific GDPR API scopes."
            ),
        ),
        description="Get the user information stored in the profile as machine readable JSON.\n\nRequires "
        "authentication.\n\nPossible error codes:\n\n* `TODO`",
    )
    # TODO: Add the complete list of error codes
    profiles = DjangoFilterConnectionField(
        ProfileNode,
        service_type=graphene.Argument(
            AllowedServiceType,
            description="**DEPRECATED**: requester's service is determined by authentication, "
            "but for now it can still be overridden by this argument.",
        ),
        description="Search for profiles. The results are filtered based on the given parameters. The results are "
        "paged using Relay.\n\nRequires `staff` credentials for the requester's service."
        "The profiles must have an active connection to the requester's service, otherwise "
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

    profile_with_access_token = graphene.Field(
        RestrictedProfileNode,
        token=graphene.Argument(
            graphene.UUID,
            required=True,
            description="The UUID token in a string representation, "
            "for example `bd96c5b1-d9ba-4ad8-8c53-140578555f29`",
        ),
        description="Get a profile by using a temporary read access `token`. The `token` is the only authorization "
        "technique with this endpoint so this can also be used unauthenticated.\n\n"
        "Possible error codes:\n\n"
        "* `PROFILE_DOES_NOT_EXIST_ERROR`\n"
        "* `TOKEN_EXPIRED_ERROR`",
    )

    @staff_required(required_permission="view")
    def resolve_profile(self, info, **kwargs):
        service = info.context.service
        return Profile.objects.filter(service_connections__service=service).get(
            pk=relay.Node.from_global_id(kwargs["id"])[1]
        )

    @login_required
    def resolve_my_profile(self, info, **kwargs):
        return Profile.objects.filter(user=info.context.user).first()

    @staff_required(required_permission="view")
    def resolve_profiles(self, info, **kwargs):
        service = info.context.service
        return Profile.objects.filter(service_connections__service=service)

    @login_required
    def resolve_claimable_profile(self, info, **kwargs):
        # TODO: Complete error handling for this OM-297
        return get_claimable_profile(token=kwargs["token"])

    @login_required
    def resolve_download_my_profile(self, info, **kwargs):
        authorization_code = kwargs["authorization_code"]
        profile = Profile.objects.filter(user=info.context.user).first()

        external_data = []

        if profile.service_connections.exists():
            tte = TunnistamoTokenExchange()
            api_tokens = tte.fetch_api_tokens(authorization_code)

            for service_connection in profile.service_connections.all():
                service = service_connection.service

                if not service.gdpr_query_scope:
                    continue

                api_identifier = service.gdpr_query_scope.rsplit(".", 1)[0]
                api_token = api_tokens.get(api_identifier, "")

                if not api_token:
                    raise MissingGDPRApiTokenError(
                        f"Couldn't fetch an API token for service {service.name}."
                    )

                service_connection_data = service_connection.download_gdpr_data(
                    api_token=api_token
                )

                if service_connection_data:
                    external_data.append(service_connection_data)

        return {"key": "DATA", "children": [profile.serialize(), *external_data]}

    def resolve_profile_with_access_token(self, info, **kwargs):
        try:
            token = TemporaryReadAccessToken.objects.get(token=kwargs["token"])
        except TemporaryReadAccessToken.DoesNotExist:
            raise ProfileDoesNotExistError("Profile does not exist")

        if token.expires_at() < timezone.now():
            raise TokenExpiredError("The access token has expired")

        return token.profile


class Mutation(graphene.ObjectType):
    # TODO: Add the complete list of error codes
    create_my_profile = CreateMyProfileMutation.Field(
        description="Creates a new profile based on the given data. The new profile is linked to the currently "
        "authenticated user.\n\nOne or several of the following is possible to add:\n\n* Email\n"
        "* Address\n* Phone\n\nRequires authentication.\n\nPossible error codes:\n\n* `TODO`"
    )
    create_profile = CreateProfileMutation.Field()

    # fmt: off
    create_or_update_profile_with_verified_personal_information = (
        CreateOrUpdateProfileWithVerifiedPersonalInformationMutation.Field(
            description="Creates a new or updates an existing profile with its "
            "_verified personal information_ section for the specified user.\n\n"
            "Requires elevated privileges.\n\n"
            "Possible error codes:\n\n"
            "* `PERMISSION_DENIED_ERROR`: "
            "The current user doesn't have the reguired permissions to perform this action.\n"
            "* `VALIDATION_ERROR`: "
            "The given input doesn't pass validation."
        )
    )
    # fmt: on

    # TODO: Add the complete list of error codes
    update_my_profile = UpdateMyProfileMutation.Field(
        description="Updates the profile which is linked to the currently authenticated user based on the given data."
        "\n\nOne or several of the following is possible to add, modify or remove:\n\n* Email\n* Address"
        "\n* Phone\n\nRequires authentication.\n\nPossible error codes:\n\n* `TODO`"
    )
    update_profile = UpdateProfileMutation.Field(
        description="Updates the profile with id given as an argument based on the given data."
        "\n\nOne or several of the following is possible to add, modify or remove:\n\n* Email\n* Address"
        "\n* Phone\n\nIf sensitive data is given, associated data will also be created "
        "and linked to the profile **or** the existing data set will be updated if the profile is "
        "already linked to it.\n\nRequires elevated privileges.\n\nPossible error codes:\n\n* `TODO`"
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

    create_my_profile_temporary_read_access_token = CreateMyProfileTemporaryReadAccessTokenMutation.Field(
        description="Creates and returns an access token for the profile which is linked to the currently "
        "authenticated user. The access token gives read access for this profile for any user, including anonymous, "
        "unauthenticated users. The token has an expiration time after which it can no longer be used.\n\n"
        "Requires authentication.\n\n"
        "Possible error codes:\n\n* `PERMISSION_DENIED_ERROR`"
    )
