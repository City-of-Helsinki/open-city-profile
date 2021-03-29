import uuid

import graphene
from django.forms import MultipleChoiceField
from django_filters import MultipleChoiceFilter
from graphene_django.forms.converter import convert_form_field

from profiles.loaders import (
    AddressesByProfileIdLoader,
    EmailsByProfileIdLoader,
    PhonesByProfileIdLoader,
    PrimaryAddressForProfileLoader,
    PrimaryEmailForProfileLoader,
    PrimaryPhoneForProfileLoader,
)
from profiles.utils import set_current_service
from services.models import Service


class JWTMiddleware:
    def resolve(self, next, root, info, **kwargs):
        request = info.context

        auth_error = getattr(request, "auth_error", None)
        if isinstance(auth_error, Exception):
            raise auth_error

        return next(root, info, **kwargs)


class UUIDMultipleChoiceField(MultipleChoiceField):
    def to_python(self, value):
        if not value:
            return []
        # It's already a list of UUIDs, ensured and converted by Graphene
        return value

    def valid_value(self, value):
        return isinstance(value, uuid.UUID)


@convert_form_field.register(UUIDMultipleChoiceField)
def convert_form_field_to_uuid_list(field):
    return graphene.List(graphene.NonNull(graphene.UUID), required=field.required)


class UUIDMultipleChoiceFilter(MultipleChoiceFilter):
    field_class = UUIDMultipleChoiceField


_LOADERS = {
    "addresses_by_profile_id_loader": AddressesByProfileIdLoader,
    "emails_by_profile_id_loader": EmailsByProfileIdLoader,
    "phones_by_profile_id_loader": PhonesByProfileIdLoader,
    "primary_address_for_profile_loader": PrimaryAddressForProfileLoader,
    "primary_email_for_profile_loader": PrimaryEmailForProfileLoader,
    "primary_phone_for_profile_loader": PrimaryPhoneForProfileLoader,
}


class GQLDataLoaders:
    def __init__(self):
        self.cached_loaders = False

    def resolve(self, next, root, info, **kwargs):
        context = info.context

        if not self.cached_loaders:
            for loader_name, loader_class in _LOADERS.items():
                setattr(context, loader_name, loader_class())

            self.cached_loaders = True

        return next(root, info, **kwargs)


def determine_service_middleware(next, root, info, **kwargs):
    """Determine service from the context or from a service type argument

    The service read from an argument is only enabled for the duration of the resolve
    and the original service is restored after the resolve has run. (Reading from an
    argument is only for backwards compatibility and should be removed after the
    "service_type" fields are removed)"""
    if not hasattr(info.context, "service"):
        info.context.service = None

    # Determine service_type from the arguments
    service_type = None
    if "input" in kwargs:
        input_argument = kwargs.get("input", {})
        # Most of the mutations
        if "service_type" in input_argument:
            service_type = input_argument.get("service_type")
        # AddServiceConnectionMutation
        elif "service_connection" in input_argument:
            service_type = (
                input_argument.get("service_connection", {})
                .get("service", {})
                .get("type")
            )
    else:
        # Queries
        service_type = kwargs.get("service_type")

    old_service = None
    if service_type:
        old_service = getattr(info.context, "service", None)
        info.context.service = Service.objects.get(service_type=service_type)

    if info.context.service:
        set_current_service(info.context.service)

    try:
        return_value = next(root, info, **kwargs)
    finally:
        if old_service:
            info.context.service = old_service
            set_current_service(old_service)

    return return_value
