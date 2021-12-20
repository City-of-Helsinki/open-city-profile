from itertools import chain

import django.dispatch
import graphene
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import F, OuterRef, Q, Subquery
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import override
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
from graphene_validator.decorators import validated
from graphene_validator.errors import ValidationError as GrapheneValidationError
from graphene_validator.validation import validate
from graphql_relay import from_global_id
from munigeo.models import AdministrativeDivision
from thesaurus.models import Concept

from open_city_profile.decorators import (
    login_and_service_required,
    login_required,
    permission_required,
    staff_required,
)
from open_city_profile.exceptions import (
    APINotImplementedError,
    InvalidEmailFormatError,
    ProfileDoesNotExistError,
    ProfileMustHavePrimaryEmailError,
    TokenExpiredError,
)
from open_city_profile.graphene import UUIDMultipleChoiceFilter
from services.models import Service, ServiceConnection
from services.schema import AllowedServiceType, ServiceConnectionType
from subscriptions.schema import (
    SubscriptionInputType,
    SubscriptionNode,
    UpdateMySubscriptionMutation,
)
from utils.validation import model_field_validation

from .connected_services import (
    delete_connected_service_data,
    download_connected_service_data,
)
from .enums import AddressType, EmailType, PhoneType
from .models import (
    Address,
    ClaimToken,
    Contact,
    Email,
    EncryptedAddress,
    Phone,
    Profile,
    SensitiveData,
    TemporaryReadAccessToken,
    VerifiedPersonalInformation,
    VerifiedPersonalInformationPermanentAddress,
    VerifiedPersonalInformationPermanentForeignAddress,
    VerifiedPersonalInformationTemporaryAddress,
)
from .utils import requester_can_view_verified_personal_information

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


profile_updated = django.dispatch.Signal(providing_args=["instance"])


def get_claimable_profile(token=None):
    claim_token = ClaimToken.objects.get(token=token)
    if claim_token.expires_at and claim_token.expires_at < timezone.now():
        raise TokenExpiredError("Token for claiming this profile has expired")
    return Profile.objects.filter(user=None).get(claim_tokens__id=claim_token.id)


def _create_nested(model, profile, data):
    for add_input in filter(None, data):
        item = model(profile=profile)
        for field, value in add_input.items():
            if field == "primary" and value is True:
                model.objects.filter(profile=profile).update(primary=False)
            setattr(item, field, value)

        item.save()


def _update_nested(model, profile, data, field_callback):
    for update_input in filter(None, data):
        id = update_input.pop("id")
        item = model.objects.get(profile=profile, pk=from_global_id(id)[1])
        for field, value in update_input.items():
            if field_callback:
                field_callback(item, field, value)
            if field == "primary" and value is True:
                model.objects.filter(profile=profile).update(primary=False)
            setattr(item, field, value)

        item.save()


def _delete_nested(model, profile, data):
    for remove_id in filter(None, data):
        model.objects.get(profile=profile, pk=from_global_id(remove_id)[1]).delete()


def update_profile(profile, profile_data):
    def email_change_makes_it_unverified(item, field, value):
        if field == "email" and item.email != value:
            item.verified = False

    nested_to_create = [
        (Email, profile_data.pop("add_emails", [])),
        (Phone, profile_data.pop("add_phones", [])),
        (Address, profile_data.pop("add_addresses", [])),
    ]
    nested_to_update = [
        (
            Email,
            profile_data.pop("update_emails", []),
            email_change_makes_it_unverified,
        ),
        (Phone, profile_data.pop("update_phones", []), None),
        (Address, profile_data.pop("update_addresses", []), None),
    ]
    nested_to_delete = [
        (Email, profile_data.pop("remove_emails", [])),
        (Phone, profile_data.pop("remove_phones", [])),
        (Address, profile_data.pop("remove_addresses", [])),
    ]

    # Remove image field from input. It's not supposed to do anything anymore.
    profile_data.pop("image", None)

    profile_had_primary_email = bool(profile.get_primary_email_value())

    for field, value in profile_data.items():
        setattr(profile, field, value)
    profile.save()

    for model, data in nested_to_create:
        _create_nested(model, profile, data)

    for model, data, field_callback in nested_to_update:
        _update_nested(model, profile, data, field_callback)

    for model, data in nested_to_delete:
        _delete_nested(model, profile, data)

    if profile_had_primary_email and not bool(profile.get_primary_email_value()):
        raise ProfileMustHavePrimaryEmailError(
            "Must maintain a primary email on a profile"
        )

    profile_updated.send(sender=profile.__class__, instance=profile)


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
            "national_identification_number",
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
    first_name = CharFilter(method="filter_by_name_icontains")
    last_name = CharFilter(method="filter_by_name_icontains")
    nickname = CharFilter(lookup_expr="icontains")
    national_identification_number = CharFilter(
        method="filter_by_nin_exact", label="Searches by full match only."
    )
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

    def filter_by_name_icontains(self, queryset, name, value):
        name_filter = Q(**{f"{name}__icontains": value})

        if requester_can_view_verified_personal_information(self.request):
            name_filter |= Q(
                **{f"verified_personal_information__{name}__icontains": value}
            )

        return queryset.filter(name_filter)

    def filter_by_nin_exact(self, queryset, name, value):
        if requester_can_view_verified_personal_information(self.request):
            return queryset.filter(
                verified_personal_information__national_identification_number=value
            )
        else:
            return queryset.none()

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


@key(fields="id")
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

    @login_and_service_required
    def __resolve_reference(self, info, **kwargs):
        address = graphene.Node.get_node_from_global_id(
            info, self.id, only_type=AddressNode
        )
        if not address:
            return None

        service = info.context.service
        user = info.context.user

        if service.has_connection_to_profile(address.profile) and (
            user == address.profile.user or user.has_perm("can_view_profiles", service)
        ):
            return address
        else:
            raise PermissionDenied(
                _("You do not have permission to perform this action.")
            )


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
            "municipality_of_residence",
            "municipality_of_residence_number",
        )

    # Need to set the national_identification_number field explicitly as non-null
    # because django-searchable-encrypted-fields SearchFields are always nullable
    # and you can't change it.
    national_identification_number = graphene.NonNull(graphene.String)

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
    ssn = graphene.String(description="Finnish personal identity code.")

    @staticmethod
    def validate_ssn(value, info, **input):
        return model_field_validation(SensitiveData, "ssn", value)


class RestrictedProfileNode(DjangoObjectType):
    class Meta:
        model = Profile
        fields = ("first_name", "last_name", "nickname", "language")
        interfaces = (relay.Node,)

    image = graphene.Field(
        graphene.String,
        deprecation_reason="There is no image in the Profile. This field always just returns null.",
    )
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
        fields = ("first_name", "last_name", "nickname", "language")
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
    verified_personal_information = graphene.Field(
        VerifiedPersonalInformationNode,
        description="Personal information that has been verified to be true. "
        "Can result into `PERMISSION_DENIED_ERROR` if the requester has no required "
        "privileges to access this information.",
    )

    def resolve_service_connections(self, info, **kwargs):
        return ServiceConnection.objects.filter(profile=self)

    def resolve_sensitivedata(self, info, **kwargs):
        service = info.context.service

        if info.context.user == self.user or info.context.user.has_perm(
            "can_view_sensitivedata", service
        ):
            return self.sensitivedata
        else:
            # TODO: We should return PermissionDenied as a partial error here.
            return None

    def resolve_verified_personal_information(self, info, **kwargs):
        loa = info.context.user_auth.data.get("loa")
        if (
            info.context.user == self.user and loa in ["substantial", "high"]
        ) or requester_can_view_verified_personal_information(info.context):
            try:
                return self.verified_personal_information
            except VerifiedPersonalInformation.DoesNotExist:
                return None
        else:
            raise PermissionDenied(
                "No permission to read verified personal information."
            )

    @login_and_service_required
    def __resolve_reference(self, info, **kwargs):
        profile = graphene.Node.get_node_from_global_id(
            info, self.id, only_type=ProfileNode
        )
        if not profile:
            return None

        service = info.context.service
        user = info.context.user

        if service.has_connection_to_profile(profile) and (
            user == profile.user or user.has_perm("can_view_profiles", service)
        ):
            return profile
        else:
            raise PermissionDenied(
                _("You do not have permission to perform this action.")
            )


class TemporaryReadAccessTokenNode(DjangoObjectType):
    class Meta:
        model = TemporaryReadAccessToken
        fields = ("token",)

    expires_at = graphene.DateTime()

    def resolve_expires_at(self, info, **kwargs):
        return self.expires_at()


def _validate_email(email):
    try:
        return model_field_validation(Email, "email", email)
    except GrapheneValidationError:
        raise InvalidEmailFormatError("Email must be in valid email format")


class CreateEmailInput(graphene.InputObjectType):
    primary = graphene.Boolean(description="Is this primary mail address.")
    email = graphene.String(description="Email address.", required=True)
    email_type = AllowedEmailType(description="Email address type.", required=True)

    @staticmethod
    def validate_email(value, info, **input):
        return _validate_email(value)


class UpdateEmailInput(graphene.InputObjectType):
    primary = graphene.Boolean(description="Is this primary mail address.")
    id = graphene.ID(required=True)
    email = graphene.String(description="Email address.")
    email_type = AllowedEmailType(description="Email address type.")

    @staticmethod
    def validate_email(value, info, **input):
        return _validate_email(value)


class CreatePhoneInput(graphene.InputObjectType):
    primary = graphene.Boolean(description="Is this primary phone number.")
    phone = graphene.String(
        description="Phone number. Must not be empty.", required=True
    )
    phone_type = AllowedPhoneType(description="Phone number type.", required=True)

    @staticmethod
    def validate_phone(value, info, **input):
        return model_field_validation(Phone, "phone", value)


class UpdatePhoneInput(graphene.InputObjectType):
    primary = graphene.Boolean(description="Is this primary phone number.")
    id = graphene.ID(required=True)
    phone = graphene.String(description="Phone number. If provided, must not be empty.")
    phone_type = AllowedPhoneType(description="Phone number type.")

    @staticmethod
    def validate_phone(value, info, **input):
        return model_field_validation(Phone, "phone", value)


class AddressInput(graphene.InputObjectType):
    country_code = graphene.String(description="An ISO 3166 alpha-2 country code.")
    primary = graphene.Boolean(description="Is this primary address.")

    @staticmethod
    def validate_country_code(value, info, **input):
        return model_field_validation(Address, "country_code", value)


class CreateAddressInput(AddressInput):
    address = graphene.String(
        description="Street address. Maximum length is 128 characters.", required=True,
    )
    postal_code = graphene.String(
        description="Postal code. Maximum length is 32 characters.", required=True,
    )
    city = graphene.String(
        description="City. Maximum length is 64 characters.", required=True,
    )
    address_type = AllowedAddressType(description="Address type.", required=True)

    @staticmethod
    def validate_address(value, info, **input):
        return model_field_validation(Address, "address", value)

    @staticmethod
    def validate_postal_code(value, info, **input):
        return model_field_validation(Address, "postal_code", value)

    @staticmethod
    def validate_city(value, info, **input):
        return model_field_validation(Address, "city", value)


class UpdateAddressInput(AddressInput):
    id = graphene.ID(required=True)
    address = graphene.String(
        description="Street address. Maximum length is 128 characters."
    )
    postal_code = graphene.String(
        description="Postal code. Maximum length is 32 characters."
    )
    city = graphene.String(description="City. Maximum length is 64 characters.")
    address_type = AllowedAddressType(description="Address type.")

    @staticmethod
    def validate_address(value, info, **input):
        return model_field_validation(Address, "address", value)

    @staticmethod
    def validate_postal_code(value, info, **input):
        return model_field_validation(Address, "postal_code", value)

    @staticmethod
    def validate_city(value, info, **input):
        return model_field_validation(Address, "city", value)


class ProfileInputBase(graphene.InputObjectType):
    first_name = graphene.String(
        description="First name. Maximum length is 255 characters."
    )
    last_name = graphene.String(
        description="Last name. Maximum length is 255 characters."
    )
    nickname = graphene.String(description="Nickname. Maximum length is 32 characters.")
    image = graphene.String(description="**DEPRECATED**. Any input is ignored.")
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

    @staticmethod
    def validate_first_name(value, info, **input):
        return model_field_validation(Profile, "first_name", value)

    @staticmethod
    def validate_last_name(value, info, **input):
        return model_field_validation(Profile, "last_name", value)

    @staticmethod
    def validate_nickname(value, info, **input):
        return model_field_validation(Profile, "nickname", value)


class ProfileInput(ProfileInputBase):
    """The following fields are deprecated:

* `image`

There's no replacement for these."""

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
        validate(cls, root, info, **input)

        profile_data = input.pop("profile")
        nested_to_create = [
            (Email, profile_data.pop("add_emails", [])),
            (Phone, profile_data.pop("add_phones", [])),
            (Address, profile_data.pop("add_addresses", [])),
        ]

        sensitive_data = profile_data.pop("sensitivedata", None)

        # Remove image field from input. It's not supposed to do anything anymore.
        profile_data.pop("image", None)
        # Remove subscriptions field from the input. It has never been handled so
        # providing any input has just resulted into an error.
        profile_data.pop("subscriptions", None)

        profile = Profile.objects.create(user=info.context.user)
        for field, value in profile_data.items():
            setattr(profile, field, value)
        profile.save()

        for model, data in nested_to_create:
            _create_nested(model, profile, data)

        if sensitive_data:
            update_sensitivedata(profile, sensitive_data)

        return CreateMyProfileMutation(profile=profile)


class CreateProfileInput(ProfileInputBase):
    """The following fields are deprecated:

* `image`
* `update_emails`
* `remove_emails`
* `update_phones`
* `remove_phones`
* `update_addresses`
* `remove_addresses`

There's no replacement for these."""

    update_emails = graphene.List(
        UpdateEmailInput, description="**DEPRECATED**. Any input is ignored."
    )
    remove_emails = graphene.List(
        graphene.ID, description="**DEPRECATED**. Any input is ignored."
    )
    update_phones = graphene.List(
        UpdatePhoneInput, description="**DEPRECATED**. Any input is ignored."
    )
    remove_phones = graphene.List(
        graphene.ID, description="**DEPRECATED**. Any input is ignored."
    )
    update_addresses = graphene.List(
        UpdateAddressInput, description="**DEPRECATED**. Any input is ignored."
    )
    remove_addresses = graphene.List(
        graphene.ID, description="**DEPRECATED**. Any input is ignored."
    )


class CreateProfileMutation(relay.ClientIDMutation):
    class Input:
        service_type = graphene.Argument(
            AllowedServiceType,
            description="**OBSOLETE**: doesn't do anything. Requester's service is determined by authentication.",
        )
        profile = CreateProfileInput(required=True)

    profile = graphene.Field(ProfileNode)

    @classmethod
    @staff_required(required_permission="manage")
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        service = info.context.service
        profile_data = input.get("profile")
        sensitivedata = profile_data.get("sensitivedata", None)

        if sensitivedata and not info.context.user.has_perm(
            "can_manage_sensitivedata", service
        ):
            raise PermissionDenied(
                _("You do not have permission to perform this action.")
            )

        validate(cls, root, info, **input)

        nested_to_create = [
            (Email, profile_data.pop("add_emails", [])),
            (Phone, profile_data.pop("add_phones", [])),
            (Address, profile_data.pop("add_addresses", [])),
        ]

        profile_data.pop("sensitivedata", None)

        # Remove image field from input. It's not supposed to do anything anymore.
        profile_data.pop("image", None)
        # Remove subscriptions field from the input. It has never been handled so
        # providing any input has just resulted into an error.
        profile_data.pop("subscriptions", None)

        profile = Profile(**profile_data)
        profile.save()

        for model, data in nested_to_create:
            _create_nested(model, profile, data)

        if sensitivedata:
            SensitiveData.objects.create(profile=profile, **sensitivedata)
            profile.refresh_from_db()

        # create the service connection for the profile
        profile.service_connections.create(service=service)

        return CreateProfileMutation(profile=profile)


class VerifiedPersonalInformationAddressInput(graphene.InputObjectType):
    street_address = graphene.String(
        description="Street address with possible house number etc. Max length 100 characters."
    )
    postal_code = graphene.String(
        description="Finnish postal code, exactly five digits."
    )
    post_office = graphene.String(description="Post office. Max length 100 characters.")

    @staticmethod
    def validate_street_address(value, info, **input):
        return model_field_validation(EncryptedAddress, "street_address", value)

    @staticmethod
    def validate_postal_code(value, info, **input):
        return model_field_validation(EncryptedAddress, "postal_code", value)

    @staticmethod
    def validate_post_office(value, info, **input):
        return model_field_validation(EncryptedAddress, "post_office", value)


class VerifiedPersonalInformationForeignAddressInput(graphene.InputObjectType):
    street_address = graphene.String(
        description="Street address or whatever is the _first part_ of the address. Max length 100 characters."
    )
    additional_address = graphene.String(
        description="Additional address information, perhaps town, county, state, country etc. "
        "Max length 100 characters."
    )
    country_code = graphene.String(description="An ISO 3166-1 country code.")

    @staticmethod
    def validate_street_address(value, info, **input):
        return model_field_validation(
            VerifiedPersonalInformationPermanentForeignAddress, "street_address", value
        )

    @staticmethod
    def validate_additional_address(value, info, **input):
        return model_field_validation(
            VerifiedPersonalInformationPermanentForeignAddress,
            "additional_address",
            value,
        )

    @staticmethod
    def validate_country_code(value, info, **input):
        return model_field_validation(
            VerifiedPersonalInformationPermanentForeignAddress, "country_code", value
        )


class VerifiedPersonalInformationInput(graphene.InputObjectType):
    first_name = graphene.String(
        description="First name(s). Max length 100 characters."
    )
    last_name = graphene.String(description="Last name. Max length 100 characters.")
    given_name = graphene.String(
        description="The name the person is called with. Max length 100 characters."
    )
    national_identification_number = graphene.String(
        description="Finnish personal identity code."
    )
    municipality_of_residence = graphene.String(
        description="Official municipality of residence in Finland as a free form text. Max length 100 characters."
    )
    municipality_of_residence_number = graphene.String(
        description="Official municipality of residence in Finland as an official number, exactly three digits."
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

    @staticmethod
    def validate_first_name(value, info, **input):
        return model_field_validation(VerifiedPersonalInformation, "first_name", value)

    @staticmethod
    def validate_last_name(value, info, **input):
        return model_field_validation(VerifiedPersonalInformation, "last_name", value)

    @staticmethod
    def validate_given_name(value, info, **input):
        return model_field_validation(VerifiedPersonalInformation, "given_name", value)

    @staticmethod
    def validate_national_identification_number(value, info, **input):
        return model_field_validation(
            VerifiedPersonalInformation, "national_identification_number", value
        )

    @staticmethod
    def validate_municipality_of_residence(value, info, **input):
        return model_field_validation(
            VerifiedPersonalInformation, "municipality_of_residence", value
        )

    @staticmethod
    def validate_municipality_of_residence_number(value, info, **input):
        return model_field_validation(
            VerifiedPersonalInformation, "municipality_of_residence_number", value
        )


class EmailInput(graphene.InputObjectType):
    email = graphene.String(description="The email address.", required=True)
    verified = graphene.Boolean(
        description="Sets whether the primary email address has been verified. If not given, defaults to False."
    )


class ProfileWithVerifiedPersonalInformationInput(graphene.InputObjectType):
    first_name = graphene.String(description="First name.")
    last_name = graphene.String(description="Last name.")
    verified_personal_information = graphene.InputField(
        VerifiedPersonalInformationInput
    )
    primary_email = graphene.InputField(
        EmailInput, description="Sets the profile's primary email address."
    )


class CreateOrUpdateUserProfileMutationInput(graphene.InputObjectType):
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


class CreateOrUpdateUserProfileMutationPayload(graphene.ObjectType):
    profile = graphene.Field(ProfileNode)


class CreateOrUpdateProfileWithVerifiedPersonalInformationMutationPayload(
    graphene.ObjectType
):
    profile = graphene.Field(ProfileWithVerifiedPersonalInformationOutput)


class CreateOrUpdateUserProfileMutationBase:
    @staticmethod
    def _handle_address(vpi, address_name, address_model, address_input):
        try:
            address = getattr(vpi, address_name)
        except address_model.DoesNotExist:
            address = address_model(verified_personal_information=vpi)

        for field, value in address_input.items():
            setattr(address, field, value)

        if not address.is_empty():
            address.save()
        elif address.id:
            address.delete()

    @staticmethod
    def _handle_verified_personal_information(
        profile, verified_personal_information_input
    ):
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

        vpi, created = VerifiedPersonalInformation.objects.update_or_create(
            profile=profile, defaults=verified_personal_information_input
        )

        for address_type in address_types:
            address_input = address_type["input"]
            if not address_input:
                continue

            address_name = address_type["name"]
            address_model = address_type["model"]

            CreateOrUpdateUserProfileMutationBase._handle_address(
                vpi, address_name, address_model, address_input
            )

    @staticmethod
    def _handle_primary_email(profile, primary_email_input):
        email_address = primary_email_input["email"]
        verified = primary_email_input.get("verified", False)

        email, email_created = profile.emails.get_or_create(
            email=email_address,
            defaults={"email_type": EmailType.NONE, "verified": verified},
        )

        profile.emails.exclude(pk=email.pk).filter(primary=True).update(primary=False)

        if not email.primary or email.verified is not verified:
            email.primary = True
            email.verified = verified
            email.save()

    @staticmethod
    def _do_mutate(parent, info, input):
        user_id_input = input.pop("user_id")
        profile_input = input.pop("profile")
        verified_personal_information_input = profile_input.pop(
            "verified_personal_information", None
        )
        primary_email_input = profile_input.pop("primary_email", None)

        user, created = User.objects.get_or_create(uuid=user_id_input)

        profile, created = Profile.objects.update_or_create(
            user=user, defaults=profile_input
        )

        if verified_personal_information_input:
            CreateOrUpdateUserProfileMutationBase._handle_verified_personal_information(
                profile, verified_personal_information_input
            )

        service_client_id = input.pop("service_client_id", None)
        if service_client_id:
            service = Service.objects.get(client_ids__client_id=service_client_id)
            profile.service_connections.update_or_create(
                service=service, defaults={"enabled": True}
            )

        if primary_email_input:
            CreateOrUpdateUserProfileMutationBase._handle_primary_email(
                profile, primary_email_input
            )

        return profile


@validated
class CreateOrUpdateUserProfileMutation(
    CreateOrUpdateUserProfileMutationBase, graphene.Mutation
):
    class Arguments:
        input = CreateOrUpdateUserProfileMutationInput(required=True)

    Output = CreateOrUpdateUserProfileMutationPayload

    @staticmethod
    @permission_required("profiles.manage_verified_personal_information")
    @transaction.atomic
    def mutate(parent, info, input):
        profile = CreateOrUpdateUserProfileMutationBase._do_mutate(parent, info, input)
        return CreateOrUpdateUserProfileMutationPayload(profile=profile)


@validated
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
        profile = CreateOrUpdateUserProfileMutationBase._do_mutate(parent, info, input)

        return CreateOrUpdateProfileWithVerifiedPersonalInformationMutationPayload(
            profile=profile
        )


class UpdateMyProfileMutation(relay.ClientIDMutation):
    class Input:
        profile = ProfileInput(required=True)

    profile = graphene.Field(ProfileNode)

    @classmethod
    @login_and_service_required
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        profile = Profile.objects.get(user=info.context.user)

        if not info.context.service.has_connection_to_profile(profile):
            raise PermissionDenied(
                _("You do not have permission to perform this action.")
            )

        validate(cls, root, info, **input)

        profile_data = input.pop("profile")
        sensitive_data = profile_data.pop("sensitivedata", None)
        subscription_data = profile_data.pop("subscriptions", [])

        update_profile(profile, profile_data)

        if sensitive_data:
            update_sensitivedata(profile, sensitive_data)

        for subscription in subscription_data:
            UpdateMySubscriptionMutation().mutate_and_get_payload(
                root, info, subscription=subscription
            )

        return UpdateMyProfileMutation(profile=profile)


class UpdateProfileInput(ProfileInputBase):
    """The following fields are deprecated:

* `image`

There's no replacement for these."""

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
            description="**OBSOLETE**: doesn't do anything. Requester's service is determined by authentication.",
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

        if not service.has_connection_to_profile(profile):
            raise PermissionDenied(
                _("You do not have permission to perform this action.")
            )

        sensitive_data = profile_data.get("sensitivedata", None)

        if sensitive_data and not info.context.user.has_perm(
            "can_manage_sensitivedata", service
        ):
            raise PermissionDenied(
                _("You do not have permission to perform this action.")
            )

        # Remove subscriptions field from the input. It has never been handled so
        # providing any input has just resulted into an error.
        profile_data.pop("subscriptions", None)

        validate(cls, root, info, **input)

        profile_data.pop("sensitivedata", None)

        update_profile(profile, profile_data)

        if sensitive_data:
            update_sensitivedata(profile, sensitive_data)

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
        validate(cls, root, info, **input)

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
    @login_and_service_required
    def mutate_and_get_payload(cls, root, info, **input):
        try:
            profile = Profile.objects.get(user=info.context.user)
        except Profile.DoesNotExist:
            raise ProfileDoesNotExistError("Profile does not exist")

        if not info.context.service.has_connection_to_profile(profile):
            raise PermissionDenied(
                _("You do not have permission to perform this action.")
            )

        delete_connected_service_data(profile, input["authorization_code"])

        profile.delete()
        info.context.user.delete()
        return DeleteMyProfileMutation()


class CreateMyProfileTemporaryReadAccessTokenMutation(relay.ClientIDMutation):
    temporary_read_access_token = graphene.Field(TemporaryReadAccessTokenNode)

    @classmethod
    @login_and_service_required
    def mutate_and_get_payload(cls, root, info):
        profile = Profile.objects.get(user=info.context.user)

        if not info.context.service.has_connection_to_profile(profile):
            raise PermissionDenied(
                _("You do not have permission to perform this action.")
            )

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
            description="**OBSOLETE**: doesn't do anything. Requester's service is determined by authentication.",
        ),
        description="Get profile by profile ID.\n\nRequires `staff` credentials for the requester's service."
        "The profile must have an active connection to the requester's service, otherwise "
        "it will not be returned.\n\nPossible error codes:\n\n* `TODO`",
    )
    # TODO: Add the complete list of error codes
    my_profile = graphene.Field(
        ProfileNode,
        description="Get the profile belonging to the currently authenticated user.\n\nRequires authentication.\n\n"
        "Possible error codes:\n\n* `TODO`",
    )
    # TODO: Add the complete list of error codes
    download_my_profile = graphene.JSONString(
        authorization_code=graphene.String(
            required=True,
            description=(
                "OAuth/OIDC authoziation code. When obtaining the code, it is required to use "
                "service and operation specific GDPR API scopes."
            ),
        ),
        description="Get the user information stored in the profile and its connected services as "
        "machine readable JSON.\n\nRequires authentication.\n\n"
        "Possible error codes:\n\n"
        "* `MISSING_GDPR_API_TOKEN_ERROR`: No API token available for accessing a connected service.",
    )
    # TODO: Add the complete list of error codes
    profiles = DjangoFilterConnectionField(
        ProfileNode,
        service_type=graphene.Argument(
            AllowedServiceType,
            description="**OBSOLETE**: doesn't do anything. Requester's service is determined by authentication.",
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
            pk=from_global_id(kwargs["id"])[1]
        )

    @login_and_service_required
    def resolve_my_profile(self, info, **kwargs):
        try:
            profile = Profile.objects.get(user=info.context.user)
        except Profile.DoesNotExist:
            return None

        if not info.context.service.has_connection_to_profile(profile):
            raise PermissionDenied(
                _("You do not have permission to perform this action.")
            )

        return profile

    @staff_required(required_permission="view")
    def resolve_profiles(self, info, **kwargs):
        service = info.context.service
        return Profile.objects.filter(service_connections__service=service)

    @login_required
    def resolve_claimable_profile(self, info, **kwargs):
        # TODO: Complete error handling for this OM-297
        return get_claimable_profile(token=kwargs["token"])

    @login_and_service_required
    def resolve_download_my_profile(self, info, **kwargs):
        try:
            profile = Profile.objects.get(user=info.context.user)
        except Profile.DoesNotExist:
            return None

        if not info.context.service.has_connection_to_profile(profile):
            raise PermissionDenied(
                _("You do not have permission to perform this action.")
            )

        external_data = download_connected_service_data(
            profile, kwargs["authorization_code"]
        )

        serialized_profile = profile.serialize()

        loa = info.context.user_auth.data.get("loa")
        if loa not in ["substantial", "high"]:
            profile_children = serialized_profile.get("children", [])
            vpi_index = next(
                (
                    i
                    for i, item in enumerate(profile_children)
                    if item["key"] == "VERIFIEDPERSONALINFORMATION"
                ),
                None,
            )
            if vpi_index is not None:
                profile_children[vpi_index] = {
                    "key": "VERIFIEDPERSONALINFORMATION",
                    "error": _("No permission to read verified personal information."),
                }

        return {"key": "DATA", "children": [serialized_profile, *external_data]}

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
            "The given input doesn't pass validation.",
            deprecation_reason="Renamed to createOrUpdateUserProfile",
        )
    )
    create_or_update_user_profile = (
        CreateOrUpdateUserProfileMutation.Field(
            description="Creates a new or updates an existing profile for the specified user.\n\n"
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
        "\n* Phone\n\nRequires authentication.\n\n"
        "Possible error codes:\n\n"
        "* `PROFILE_MUST_HAVE_PRIMARY_EMAIL`: If trying to get rid of the profile's primary email."
    )
    update_profile = UpdateProfileMutation.Field(
        description="Updates the profile with id given as an argument based on the given data."
        "\n\nOne or several of the following is possible to add, modify or remove:\n\n* Email\n* Address"
        "\n* Phone\n\nIf sensitive data is given, associated data will also be created "
        "and linked to the profile **or** the existing data set will be updated if the profile is "
        "already linked to it.\n\nRequires elevated privileges.\n\n"
        "Possible error codes:\n\n"
        "* `PROFILE_MUST_HAVE_PRIMARY_EMAIL`: If trying to get rid of the profile's primary email."
    )
    # TODO: Add the complete list of error codes
    delete_my_profile = DeleteMyProfileMutation.Field(
        description="Deletes the data of the profile which is linked to the currently authenticated user.\n\n"
        "Requires authentication.\n\nPossible error codes:\n\n"
        "* `PROFILE_DOES_NOT_EXIST_ERROR`: Returned if there is no profile linked to "
        "the currently authenticated user.\n"
        "* `MISSING_GDPR_API_TOKEN_ERROR`: No API token available for accessing a connected service.\n"
        "* `CONNECTED_SERVICE_DELETION_NOT_ALLOWED_ERROR`: The profile deletion is disallowed by one or more "
        "connected services.\n"
        "* `CONNECTED_SERVICE_DELETION_FAILED_ERROR`: The profile deletion failed for one or more connected services."
    )
    # TODO: Add the complete list of error codes
    claim_profile = ClaimProfileMutation.Field(
        description="Fetches a profile which has no linked user account yet by the given token and links the profile "
        "to the currently authenticated user's account.\n\n**NOTE:** This functionality is not implemented "
        "completely. If the authenticated user already has a profile, this mutation will respond with "
        "an error.\n\n"
        "Possible error codes:\n\n"
        "* `PROFILE_MUST_HAVE_PRIMARY_EMAIL`: If trying to get rid of the profile's primary email.\n"
        "* `API_NOT_IMPLEMENTED_ERROR`: Returned if the currently authenticated user already has a profile."
    )

    create_my_profile_temporary_read_access_token = CreateMyProfileTemporaryReadAccessTokenMutation.Field(
        description="Creates and returns an access token for the profile which is linked to the currently "
        "authenticated user. The access token gives read access for this profile for any user, including anonymous, "
        "unauthenticated users. The token has an expiration time after which it can no longer be used.\n\n"
        "Requires authentication.\n\n"
        "Possible error codes:\n\n* `PERMISSION_DENIED_ERROR`"
    )
