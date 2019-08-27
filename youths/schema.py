import uuid
from datetime import datetime

import graphene
from django.utils.translation import override
from django.utils.translation import ugettext_lazy as _
from django_ilmoitin.utils import send_notification
from graphene_django.types import DjangoObjectType
from graphql import GraphQLError
from graphql_jwt.decorators import login_required

from profiles.models import Profile

from .consts import GENDERS, LANGUAGES
from .enums import NotificationType
from .models import YouthProfile


class YouthProfileType(DjangoObjectType):
    gender = graphene.Field(graphene.String, source="gender")

    class Meta:
        model = YouthProfile
        exclude = ("id", "approval_token")


with override("en"):
    PreferredLanguage = graphene.Enum(
        "PreferredLanguage", [(l[1].upper(), l[0]) for l in LANGUAGES]
    )
Gender = graphene.Enum("Gender", [(g[0].upper(), g[0]) for g in GENDERS])


# Abstract base fields
class YouthProfileFields(graphene.InputObjectType):
    school_name = graphene.String()
    school_class = graphene.String()
    preferred_language = PreferredLanguage()
    volunteer_info = graphene.String()
    gender = Gender()
    diabetes = graphene.Boolean()
    epilepsy = graphene.Boolean()
    heart_disease = graphene.Boolean()
    extra_illnesses_info = graphene.String()
    serious_allergies = graphene.Boolean()
    allergies = graphene.String()
    notes = graphene.String()
    approver_email = graphene.String()


# Subset of abstract fields are required for creation
class CreateYouthProfileInput(YouthProfileFields):
    ssn = graphene.String(required=True)
    school_name = graphene.String(required=True)
    school_class = graphene.String(required=True)
    approver_email = graphene.String(required=True)


class CreateYouthProfile(graphene.Mutation):
    class Arguments:
        youth_profile_data = CreateYouthProfileInput(required=True)
        profile_id = graphene.ID()

    youth_profile = graphene.Field(YouthProfileType)

    @login_required
    def mutate(self, info, **kwargs):
        input_data = kwargs.get("youth_profile_data")
        profile_id = kwargs.get("profile_id")

        if info.context.user.is_superuser:
            try:
                profile = Profile.objects.get(pk=profile_id)
            except Profile.DoesNotExist:
                raise GraphQLError(_("Invalid profile id."))
        else:
            try:
                profile = Profile.objects.get(user=info.context.user)
            except Profile.DoesNotExist:
                raise GraphQLError(_("No profile found, please create one!"))

        youth_profile, created = YouthProfile.objects.get_or_create(
            profile=profile, defaults=input_data
        )
        if not created:
            raise GraphQLError(_("Youth profile already exists for this profile!"))

        youth_profile.approval_token = uuid.uuid4()
        send_notification(
            email=youth_profile.approver_email,
            notification_type=NotificationType.YOUTH_PROFILE_CONFIRMATION_NEEDED.value,
            context={"youth_profile": youth_profile},
        )
        youth_profile.approval_notification_timestamp = datetime.now()
        youth_profile.save()

        return CreateYouthProfile(youth_profile=youth_profile)


class UpdateYouthProfileInput(YouthProfileFields):
    resend_request_notification = graphene.Boolean()


class UpdateYouthProfile(graphene.Mutation):
    class Arguments:
        youth_profile_data = UpdateYouthProfileInput(required=True)
        profile_id = graphene.ID()

    youth_profile = graphene.Field(YouthProfileType)

    @login_required
    def mutate(self, info, **kwargs):
        input_data = kwargs.get("youth_profile_data")
        profile_id = kwargs.get("profile_id")
        resend_request_notification = input_data.pop(
            "resend_request_notification", False
        )

        if info.context.user.is_superuser:
            try:
                profile = Profile.objects.get(pk=profile_id)
            except Profile.DoesNotExist:
                raise GraphQLError(_("Invalid profile id."))
        else:
            try:
                profile = Profile.objects.get(user=info.context.user)
            except Profile.DoesNotExist:
                raise GraphQLError(_("No profile found, please create one!"))

        youth_profile = YouthProfile.objects.get(profile=profile)
        for field, value in input_data.items():
            setattr(youth_profile, field, value)
        youth_profile.save()

        if resend_request_notification:
            youth_profile.approval_token = uuid.uuid4()
            send_notification(
                email=youth_profile.approver_email,
                notification_type=NotificationType.YOUTH_PROFILE_CONFIRMATION_NEEDED.value,
                context={"youth_profile": youth_profile},
            )
            youth_profile.approval_notification_timestamp = datetime.now()
            youth_profile.save()

        return UpdateYouthProfile(youth_profile=youth_profile)


class ApproveYouthProfileInput(graphene.InputObjectType):
    diabetes = graphene.Boolean()
    epilepsy = graphene.Boolean()
    heart_disease = graphene.Boolean()
    extra_illnesses_info = graphene.String()
    serious_allergies = graphene.Boolean()
    allergies = graphene.String()
    photo_usage_approved = graphene.Boolean()


class ApproveYouthProfile(graphene.Mutation):
    class Arguments:
        approval_token = graphene.String(required=True)
        approval_data = ApproveYouthProfileInput(required=True)

    youth_profile = graphene.Field(YouthProfileType)

    def mutate(self, info, **kwargs):
        youth_data = kwargs.get("approval_data")
        token = kwargs.get("approval_token")

        try:
            youth_profile = YouthProfile.objects.get(approval_token=token)
        except YouthProfile.DoesNotExist:
            raise GraphQLError(_("Invalid approval token."))

        for field, value in youth_data.items():
            setattr(youth_profile, field, value)

        youth_profile.approved_time = datetime.now()
        youth_profile.approval_token = ""  # invalidate
        youth_profile.save()
        send_notification(
            email=youth_profile.profile.email,
            notification_type=NotificationType.YOUTH_PROFILE_CONFIRMED.value,
            context={"youth_profile": youth_profile},
        )
        return ApproveYouthProfile(youth_profile=youth_profile)


class Query(graphene.ObjectType):
    youth_profile = graphene.Field(YouthProfileType, profile_id=graphene.ID())

    # TODO should we hide some fields (e.g. gender) from the approver?
    youth_profile_by_approval_token = graphene.Field(
        YouthProfileType, token=graphene.String()
    )

    @login_required
    def resolve_youth_profile(self, info, **kwargs):
        if info.context.user.is_superuser:
            try:
                return YouthProfile.objects.get(profile_id=kwargs.get("profile_id"))
            except YouthProfile.DoesNotExist:
                raise GraphQLError(_("No youth profile found for provided profile id."))
        try:
            return YouthProfile.objects.get(profile__user=info.context.user)
        except YouthProfile.DoesNotExist:
            raise GraphQLError(_("No youth profile found for this profile."))

    def resolve_youth_profile_by_approval_token(self, info, **kwargs):
        try:
            return YouthProfile.objects.get(approval_token=kwargs.get("token"))
        except YouthProfile.DoesNotExist:
            raise GraphQLError(_("Invalid approval token"))


class Mutation(graphene.ObjectType):
    create_youth_profile = CreateYouthProfile.Field()
    update_youth_profile = UpdateYouthProfile.Field()
    approve_youth_profile = ApproveYouthProfile.Field()
