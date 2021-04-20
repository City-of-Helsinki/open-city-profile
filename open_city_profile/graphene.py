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
    if not hasattr(info.context, "service"):
        info.context.service = None

    return next(root, info, **kwargs)
