import uuid
from collections import OrderedDict

import graphene
import graphql
from django.conf import settings
from django.forms import MultipleChoiceField
from django.utils import translation
from django_filters import MultipleChoiceFilter
from graphene_django.forms.converter import convert_form_field
from parler.models import TranslatableModel
from parler.utils.context import switch_language

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


HelTranslationLanguageType = graphql.GraphQLEnumType(
    name="HelTranslationLanguage",
    values=OrderedDict(
        {
            lang[0].upper(): graphql.GraphQLEnumValue(lang[0], description=lang[1])
            for lang in settings.LANGUAGES
        }
    ),
)


HelTranslationDirective = graphql.GraphQLDirective(
    name="hel_translation",
    locations=[graphql.DirectiveLocation.FIELD],
    args={
        "in": graphql.GraphQLArgument(
            graphql.GraphQLNonNull(HelTranslationLanguageType),
            description="The language",
        ),
    },
    description="Get value translated in language",
)


class HelTranslationMiddleware:
    def resolve(self, next_middleware, root, info, **kwargs):
        directives = info.field_asts[0].directives

        hel_translation_directives = [
            directive
            for directive in directives
            if directive.name.value == "hel_translation"
        ]
        if not hel_translation_directives:
            return next_middleware(root, info, **kwargs)

        directive = hel_translation_directives[0]
        in_argument = next(arg for arg in directive.arguments if arg.name.value == "in")
        language = graphql.value_from_ast(
            in_argument.value, HelTranslationLanguageType, info.variable_values
        )

        if isinstance(root, TranslatableModel):
            # switch_language will change Django language too
            with switch_language(root, language):
                return_value = next_middleware(root, info, **kwargs)
        else:
            with translation.override(language):
                return_value = next_middleware(root, info, **kwargs)

        return return_value
