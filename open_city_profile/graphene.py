import uuid

import graphene
from django.forms import MultipleChoiceField
from django_filters import MultipleChoiceFilter
from graphene_django.forms.converter import convert_form_field


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
