from datetime import date

import graphene
from django.db import transaction
from django.utils import timezone
from django.utils.translation import override
from django.utils.translation import ugettext_lazy as _
from django_ilmoitin.utils import send_notification
from graphene import relay
from graphene_django.types import DjangoObjectType
from graphql import GraphQLError
from graphql_jwt.decorators import login_required
from graphql_relay.node.node import from_global_id

from open_city_profile.exceptions import (
    ApproverEmailCannotBeEmptyForMinorsError,
    CannotCreateYouthProfileIfUnder13YearsOldError,
    CannotPerformThisActionWithGivenServiceType,
    CannotRenewYouthProfileError,
    CannotSetPhotoUsagePermissionIfUnder15YearsError,
    ProfileHasNoPrimaryEmailError,
)
from profiles.decorators import staff_required
from profiles.models import Email, Profile
from services.enums import ServiceType
from services.schema import AllowedServiceType

from .enums import NotificationType, YouthLanguage
from .models import AdditionalContactPerson, calculate_expiration, YouthProfile
from .utils import (
    calculate_age,
    create_or_update_contact_persons,
    delete_contact_persons,
)

with override("en"):
    LanguageAtHome = graphene.Enum.from_enum(
        YouthLanguage, description=lambda e: e.label if e else ""
    )


def create_youth_profile(data, profile):
    contact_persons_to_create = data.pop("add_additional_contact_persons", [])

    youth_profile, created = YouthProfile.objects.get_or_create(
        profile=profile, defaults=data
    )

    if calculate_age(youth_profile.birth_date) >= 18:
        youth_profile.approved_time = timezone.now()
    else:
        if not data.get("approver_email"):
            raise ApproverEmailCannotBeEmptyForMinorsError(
                "Approver email is required for youth under 18 years old"
            )
        youth_profile.make_approvable()
    youth_profile.save()

    create_or_update_contact_persons(youth_profile, contact_persons_to_create)

    return youth_profile


def cancel_youth_profile(youth_profile, input):
    expiration = input.get("expiration")

    youth_profile.expiration = expiration or date.today()
    youth_profile.save()

    return youth_profile


def renew_youth_profile(profile):
    youth_profile = YouthProfile.objects.get(profile=profile)

    next_expiration = calculate_expiration(date.today())
    if youth_profile.expiration == next_expiration:
        raise CannotRenewYouthProfileError(
            "Cannot renew youth profile. Either youth profile is already renewed or not yet in the next "
            "renew window."
        )
    youth_profile.expiration = next_expiration

    if calculate_age(youth_profile.birth_date) >= 18:
        youth_profile.approved_time = timezone.now()
    else:
        youth_profile.make_approvable()

    youth_profile.save()
    return youth_profile


class MembershipStatus(graphene.Enum):
    ACTIVE = "active"
    PENDING = "pending"
    EXPIRED = "expired"
    RENEWING = "renewing"


class YouthProfileType(DjangoObjectType):

    membership_number = graphene.String(
        source="membership_number", description="Youth's membership number"
    )

    language_at_home = LanguageAtHome(
        source="language_at_home",
        description="The language which is spoken in the youth's home.",
    )
    membership_status = MembershipStatus(
        description="Membership status based on expiration and approved_time fields"
    )
    renewable = graphene.Boolean(
        description="Tells if the membership is currently renewable or not"
    )

    class Meta:
        model = YouthProfile
        exclude = ("id", "approval_token", "language_at_home")

    def resolve_renewable(self, info, **kwargs):
        return bool(self.approved_time) and self.expiration != calculate_expiration(
            date.today()
        )

    def resolve_membership_status(self, info, **kwargs):
        if self.expiration <= date.today():
            return MembershipStatus.EXPIRED
        elif self.approved_time and self.approved_time <= timezone.now():
            # Status RENEWING implemented naively. Calculates the expiration for the existing approval time and checks
            # if expiration is set explicitly => status == EXPIRED. If expiration is greater than calculated expiration
            # for the current period, do one of the following:
            #
            # 1. If calculated expiration for approval time is in the past, membership is considered expired
            # 2. Otherwise status of the youth profile is RENEWING
            approved_period_expiration = calculate_expiration(self.approved_time.date())
            if self.expiration < approved_period_expiration:
                return MembershipStatus.EXPIRED
            elif self.expiration > approved_period_expiration:
                if date.today() <= approved_period_expiration:
                    return MembershipStatus.RENEWING
                else:
                    return MembershipStatus.EXPIRED
            return MembershipStatus.ACTIVE
        return MembershipStatus.PENDING


class AdditionalContactPersonNode(DjangoObjectType):
    class Meta:
        model = AdditionalContactPerson
        interfaces = (relay.Node,)


class CreateAdditionalContactPersonInput(graphene.InputObjectType):
    first_name = graphene.String(description="First name.", required=True)
    last_name = graphene.String(description="Last name.", required=True)
    phone = graphene.String(description="Phone number.", required=True)
    email = graphene.String(description="Email address.", required=True)


class UpdateAdditionalContactPersonInput(graphene.InputObjectType):
    id = graphene.ID(required=True)
    first_name = graphene.String(description="First name.")
    last_name = graphene.String(description="Last name.")
    phone = graphene.String(description="Phone number.")
    email = graphene.String(description="Email address.")


# Abstract base fields
class YouthProfileFields(graphene.InputObjectType):
    school_name = graphene.String(description="The youth's school name.")
    school_class = graphene.String(description="The youth's school class.")
    language_at_home = LanguageAtHome(
        description="The language which is spoken in the youth's home."
    )
    approver_first_name = graphene.String(
        description="The youth's (supposed) guardian's first name."
    )
    approver_last_name = graphene.String(
        description="The youth's (supposed) guardian's last name."
    )
    approver_phone = graphene.String(
        description="The youth's (supposed) guardian's phone number."
    )
    approver_email = graphene.String(
        description=(
            "The youth's (supposed) guardian's email address which will be used to send approval requests."
            "This field is required for youth under 18 years old."
        )
    )
    birth_date = graphene.Date(
        required=False,
        description="The youth's birth date. This is used for example to calculate if the youth is a minor or not.",
    )
    photo_usage_approved = graphene.Boolean(
        description=(
            "`true` if the youth is allowed to be photographed. Only youth over 15 years old can set this."
            "For youth under 15 years old this is set by the (supposed) guardian in the approval phase"
        )
    )
    add_additional_contact_persons = graphene.List(
        CreateAdditionalContactPersonInput,
        description="Add additional contact persons to youth profile.",
    )
    update_additional_contact_persons = graphene.List(
        UpdateAdditionalContactPersonInput,
        description="Update youth profile's additional contact persons.",
    )
    remove_additional_contact_persons = graphene.List(
        graphene.ID, description="Remove additional contact persons from youth profile."
    )


# Subset of abstract fields are required for creation
class CreateMyYouthProfileInput(YouthProfileFields):
    birth_date = graphene.Date(
        required=True,
        description="The youth's birth date. This is used for example to calculate if the youth is a minor or not.",
    )


class CreateYouthProfileMutation(relay.ClientIDMutation):
    class Input:
        service_type = graphene.Argument(AllowedServiceType, required=True)
        profile_id = graphene.Argument(graphene.ID, required=True)
        youth_profile = CreateMyYouthProfileInput(required=True)

    youth_profile = graphene.Field(YouthProfileType)

    @classmethod
    @staff_required(required_permission="manage")
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        input_data = input.get("youth_profile")
        if input.get("service_type") != ServiceType.YOUTH_MEMBERSHIP.value:
            raise CannotPerformThisActionWithGivenServiceType("Incorrect service type")

        profile = Profile.objects.get(pk=from_global_id(input.get("profile_id"))[1])
        youth_profile = create_youth_profile(input_data, profile)

        return CreateYouthProfileMutation(youth_profile=youth_profile)


class CreateMyYouthProfileMutation(relay.ClientIDMutation):
    class Input:
        youth_profile = CreateMyYouthProfileInput(required=True)

    youth_profile = graphene.Field(YouthProfileType)

    @classmethod
    @login_required
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        input_data = input.get("youth_profile")

        if calculate_age(input_data["birth_date"]) < 13:
            raise CannotCreateYouthProfileIfUnder13YearsOldError(
                "Under 13 years old cannot create youth profile"
            )

        if "photo_usage_approved" in input_data:
            # Disable setting photo usage by themselfs for youths under 15 years old
            if calculate_age(input_data["birth_date"]) < 15:
                raise CannotSetPhotoUsagePermissionIfUnder15YearsError(
                    "Cannot set photo usage permission if under 15 years old"
                )

        profile = Profile.objects.get(user=info.context.user)
        youth_profile = create_youth_profile(input_data, profile)

        return CreateMyYouthProfileMutation(youth_profile=youth_profile)


class UpdateYouthProfileInput(YouthProfileFields):
    resend_request_notification = graphene.Boolean(
        description="If set to `true`, a new approval token is generated and a new email notification is sent to the"
        "approver's email address."
    )


def update_youth_profile(input_data, profile, manage_permission=False):
    """Create or update the youth profile for the given profile.

    :param manage_permission: Calling user has manage permission on youth profile service.
    """
    contact_persons_to_create = input_data.pop("add_additional_contact_persons", [])
    contact_persons_to_update = input_data.pop("update_additional_contact_persons", [])
    contact_persons_to_delete = input_data.pop("remove_additional_contact_persons", [])

    resend_request_notification = input_data.pop("resend_request_notification", False)
    youth_profile, created = YouthProfile.objects.get_or_create(
        profile=profile, defaults=input_data
    )

    if "photo_usage_approved" in input_data and not manage_permission:
        # Disable setting photo usage by themselves for youths under 15 years old (allowed for staff).
        # Check for birth date given in input or birth date persisted in the db.
        if (
            "birth_date" in input_data and calculate_age(input_data["birth_date"]) < 15
        ) or calculate_age(youth_profile.birth_date) < 15:
            raise CannotSetPhotoUsagePermissionIfUnder15YearsError(
                "Cannot set photo usage permission if under 15 years old"
            )

    if created:
        if calculate_age(youth_profile.birth_date) >= 18:
            youth_profile.approved_time = timezone.now()
        else:
            if not input_data.get("approver_email"):
                raise ApproverEmailCannotBeEmptyForMinorsError(
                    "Approver email is required for youth under 18 years old"
                )
            youth_profile.make_approvable()
    else:
        for field, value in input_data.items():
            setattr(youth_profile, field, value)
        if resend_request_notification:
            youth_profile.make_approvable()

    youth_profile.save()

    create_or_update_contact_persons(youth_profile, contact_persons_to_create)
    create_or_update_contact_persons(youth_profile, contact_persons_to_update)
    delete_contact_persons(youth_profile, contact_persons_to_delete)

    return youth_profile


class UpdateYouthProfileMutation(relay.ClientIDMutation):
    class Input:
        service_type = graphene.Argument(AllowedServiceType, required=True)
        profile_id = graphene.Argument(graphene.ID, required=True)
        youth_profile = UpdateYouthProfileInput(required=True)

    @classmethod
    @staff_required(required_permission="manage")
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        input_data = input.get("youth_profile")

        if input.get("service_type") != ServiceType.YOUTH_MEMBERSHIP.value:
            raise CannotPerformThisActionWithGivenServiceType("Incorrect service type")

        profile = Profile.objects.get(pk=from_global_id(input.get("profile_id"))[1])
        youth_profile = update_youth_profile(
            input_data, profile, manage_permission=True
        )
        return UpdateMyYouthProfileMutation(youth_profile=youth_profile)


class UpdateMyYouthProfileMutation(relay.ClientIDMutation):
    class Input:
        youth_profile = UpdateYouthProfileInput(required=True)

    youth_profile = graphene.Field(YouthProfileType)

    @classmethod
    @login_required
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        input_data = input.get("youth_profile")
        profile = Profile.objects.get(user=info.context.user)
        youth_profile = update_youth_profile(input_data, profile)
        return UpdateMyYouthProfileMutation(youth_profile=youth_profile)


class RenewYouthProfileMutation(relay.ClientIDMutation):
    class Input:
        service_type = graphene.Argument(AllowedServiceType, required=True)
        profile_id = graphene.Argument(graphene.ID, required=True)

    youth_profile = graphene.Field(YouthProfileType)

    @classmethod
    @staff_required(required_permission="manage")
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        if input.get("service_type") != ServiceType.YOUTH_MEMBERSHIP.value:
            raise CannotPerformThisActionWithGivenServiceType("Incorrect service type")

        profile = Profile.objects.get(pk=from_global_id(input.get("profile_id"))[1])
        youth_profile = renew_youth_profile(profile)

        return RenewYouthProfileMutation(youth_profile=youth_profile)


class RenewMyYouthProfileMutation(relay.ClientIDMutation):
    youth_profile = graphene.Field(YouthProfileType)

    @classmethod
    @login_required
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        profile = Profile.objects.get(user=info.context.user)
        youth_profile = renew_youth_profile(profile)
        return RenewMyYouthProfileMutation(youth_profile=youth_profile)


class ApproveYouthProfileMutation(relay.ClientIDMutation):
    class Input:
        approval_token = graphene.String(
            required=True,
            description="This is the token with which a youth profile may be fetched for approval purposes.",
        )
        approval_data = YouthProfileFields(
            required=True,
            description="The youth profile data to approve. This may contain modifications done by the approver.",
        )

    youth_profile = graphene.Field(YouthProfileType)

    @classmethod
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        youth_data = input.get("approval_data")
        token = input.get("approval_token")

        youth_profile = YouthProfile.objects.get(approval_token=token)

        for field, value in youth_data.items():
            setattr(youth_profile, field, value)

        try:
            email = youth_profile.profile.get_primary_email()
        except Email.DoesNotExist:
            raise ProfileHasNoPrimaryEmailError(
                "Cannot send email confirmation, youth profile has no primary email address."
            )

        youth_profile.approved_time = timezone.now()
        youth_profile.approval_token = ""  # invalidate
        youth_profile.save()
        send_notification(
            email=email.email,
            notification_type=NotificationType.YOUTH_PROFILE_CONFIRMED.value,
            context={"youth_profile": youth_profile},
            language=youth_profile.profile.language if youth_profile.profile else "fi",
        )
        return ApproveYouthProfileMutation(youth_profile=youth_profile)


class CancelYouthProfileMutation(relay.ClientIDMutation):
    class Input:
        service_type = graphene.Argument(AllowedServiceType, required=True)
        profile_id = graphene.Argument(
            graphene.ID, required=True, description="Profile id of the youth profile"
        )
        expiration = graphene.Date(
            description="Optional value for expiration. If missing or blank, current date will be used"
        )

    youth_profile = graphene.Field(YouthProfileType)

    @classmethod
    @staff_required(required_permission="manage")
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        profile = Profile.objects.get(pk=from_global_id(input.get("profile_id"))[1])
        youth_profile = cancel_youth_profile(profile.youth_profile, input)

        return CancelYouthProfileMutation(youth_profile=youth_profile)


class CancelMyYouthProfileMutation(relay.ClientIDMutation):
    class Input:
        expiration = graphene.Date(
            description="Optional value for expiration. If missing or blank, current date will be used"
        )

    youth_profile = graphene.Field(YouthProfileType)

    @classmethod
    @login_required
    @transaction.atomic
    def mutate_and_get_payload(cls, root, info, **input):
        youth_profile = cancel_youth_profile(
            YouthProfile.objects.get(
                profile=Profile.objects.get(user=info.context.user)
            ),
            input,
        )

        return CancelMyYouthProfileMutation(youth_profile=youth_profile)


class Query(graphene.ObjectType):
    # TODO: Add the complete list of error codes
    youth_profile = graphene.Field(
        YouthProfileType,
        profile_id=graphene.ID(),
        description="Get a youth profile by youth profile ID.\n\n**NOTE:** Currently this requires `superuser` "
        "credentials. This is going to be changed at one point so that service-specific staff "
        "credentials and service type are used, just like the rest of the admin-type queries.\n\n"
        "Possible error codes:\n\n* `TODO`",
    )
    # TODO: Add the complete list of error codes
    youth_profile_by_approval_token = graphene.Field(
        YouthProfileType,
        token=graphene.String(),
        description="Get a youth profile by approval token. \n\nDoesn't require authentication.\n\nPossible "
        "error codes:\n\n* `TODO`",
    )

    @login_required
    def resolve_youth_profile(self, info, **kwargs):
        profile_id = kwargs.get("profile_id")

        if profile_id is not None and not info.context.user.is_superuser:
            raise GraphQLError(_("Query by id not allowed for regular users."))

        if info.context.user.is_superuser:
            return YouthProfile.objects.get(profile_id=from_global_id(profile_id)[1])
        return YouthProfile.objects.get(profile__user=info.context.user)

    def resolve_youth_profile_by_approval_token(self, info, **kwargs):
        return YouthProfile.objects.get(approval_token=kwargs.get("token"))


class Mutation(graphene.ObjectType):
    # TODO: Complete the description
    create_youth_profile = CreateYouthProfileMutation.Field(
        description="Creates a new youth profile and links it to the profile specified with profile_id argument.\n\n"
        "When the youth profile has been created, a notification is sent to the youth profile's approver "
        "whose contact information is given in the input.\n\nRequires elevated privileges.\n\nPossible error "
        "codes:\n\n* `TODO`"
    )
    # TODO: Add the complete list of error codes
    create_my_youth_profile = CreateMyYouthProfileMutation.Field(
        description="Creates a new youth profile and links it to the currently authenticated user's profile.\n\n"
        "When the youth profile has been created, a notification is sent to the youth profile's approver "
        "whose contact information is given in the input.\n\nRequires authentication.\n\nPossible error "
        "codes:\n\n* `TODO`"
    )
    # TODO: Add the complete list of error codes
    update_youth_profile = UpdateYouthProfileMutation.Field(
        description="Updates the youth profile which belongs to the profile specified in profile_id argument.\n\n"
        "The `resend_request_notification` parameter may be used to send a notification to the youth "
        "profile's approver whose contact information is in the youth profile.\n\nRequires elevated privileges."
        "\n\nPossible error codes:\n\n* `TODO`"
    )
    # TODO: Add the complete list of error codes
    update_my_youth_profile = UpdateMyYouthProfileMutation.Field(
        description="Updates the youth profile which belongs to the profile of the currently authenticated user.\n\n"
        "The `resend_request_notification` parameter may be used to send a notification to the youth "
        "profile's approver whose contact information is in the youth profile.\n\nRequires authentication."
        "\n\nPossible error codes:\n\n* `TODO`"
    )
    # TODO: Update the description when we support the draft/published model for the youth profiles
    # TODO: Add the complete list of error codes
    renew_youth_profile = RenewYouthProfileMutation.Field(
        description="Renews the youth profile. Renewing can only be done once per season.\n\nRequires Authentication."
        "\n\nPossible error codes:\n\n* `CANNOT_RENEW_YOUTH_PROFILE_ERROR`: Returned if the youth profile is already "
        "renewed or not in the renew window\n\n* `TODO`"
    )
    # TODO: Update the description when we support the draft/published model for the youth profiles
    # TODO: Add the complete list of error codes
    renew_my_youth_profile = RenewMyYouthProfileMutation.Field(
        description="Renews the youth profile. Renewing can only be done once per season.\n\nRequires Authentication."
        "\n\nPossible error codes:\n\n* `CANNOT_RENEW_YOUTH_PROFILE_ERROR`: Returned if the youth profile is already "
        "renewed or not in the renew window\n\n* `TODO`"
    )
    # TODO: Add the complete list of error codes
    approve_youth_profile = ApproveYouthProfileMutation.Field(
        description="Fetches a youth profile using the given token, updates the data based on the given input data and"
        " approves the youth profile so that it is considered active. A confirmation is sent to the youth "
        "profile's email address after a successful approval.\n\nThe token is no longer valid after "
        "it's been used to approve the youth profile.\n\nRequires authentication.\n\nPossible error "
        "codes:\n\n* `PROFILE_HAS_NO_PRIMARY_EMAIL_ERROR`: Returned if the youth profile doesn't have a "
        "primary email address.\n\n* `TODO`"
    )
    cancel_youth_profile = CancelYouthProfileMutation.Field(
        description="Cancels youth profile of given profile\n\nRequires Authentication."
    )
    cancel_my_youth_profile = CancelMyYouthProfileMutation.Field(
        description="Cancels youth profile for current user\n\nRequires Authentication."
    )
