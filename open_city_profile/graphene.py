import logging
import uuid
from functools import partial

import graphene
from django.conf import settings
from django.forms import MultipleChoiceField
from django_filters import MultipleChoiceFilter
from graphene.utils.str_converters import to_snake_case
from graphene_django import DjangoObjectType
from graphene_django.forms.converter import convert_form_field
from graphene_django.types import ALL_FIELDS
from graphql_sync_dataloaders import SyncDataLoader
from parler.models import TranslatableModel

from open_city_profile.exceptions import FieldNotAllowedError, ServiceNotIdentifiedError
from profiles.loaders import (
    addresses_by_profile_id_loader,
    emails_by_profile_id_loader,
    phones_by_profile_id_loader,
    primary_address_for_profile_loader,
    primary_email_for_profile_loader,
    primary_phone_for_profile_loader,
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
    "addresses_by_profile_id_loader": addresses_by_profile_id_loader,
    "emails_by_profile_id_loader": emails_by_profile_id_loader,
    "phones_by_profile_id_loader": phones_by_profile_id_loader,
    "primary_address_for_profile_loader": primary_address_for_profile_loader,
    "primary_email_for_profile_loader": primary_email_for_profile_loader,
    "primary_phone_for_profile_loader": primary_phone_for_profile_loader,
}


class GQLDataLoaders:
    def __init__(self):
        self.cached_loaders = False

    def resolve(self, next, root, info, **kwargs):
        context = info.context

        if not self.cached_loaders:
            for loader_name, loader_function in _LOADERS.items():
                setattr(context, loader_name, SyncDataLoader(loader_function))
            self.cached_loaders = True

        return next(root, info, **kwargs)


def _parler_field_resolver(attname, instance, info, language=None):
    if language:
        return instance.safe_translation_getter(attname, language_code=language.value)

    return getattr(instance, attname)


def _get_language_choices_from_parler_settings():
    site_id = getattr(settings, "SITE_ID", None)
    parler_languages = settings.PARLER_LANGUAGES.get(site_id, [])

    choices = []
    for parler_language in parler_languages:
        language_code = parler_language["code"]
        choices.append((language_code.upper(), language_code))

    return choices


TranslationLanguage = graphene.Enum(
    "TranslationLanguage", _get_language_choices_from_parler_settings()
)


class DjangoParlerObjectType(DjangoObjectType):
    class Meta:
        abstract = True

    @classmethod
    def _add_parler_fields_to_type(cls, model, fields=None, exclude=None):
        """Adds fields in the model that are translated with Parler to the Object Type

        If the class defines an attribute with the same name already, the attribute is
        left as is and the translated field is not added to the class.
        """
        for parler_field_name in model._parler_meta.get_all_fields():
            if (
                hasattr(cls, parler_field_name)
                or (
                    fields is not None
                    and fields != ALL_FIELDS
                    and parler_field_name not in fields
                )
                or (exclude is not None and parler_field_name in exclude)
            ):
                continue

            setattr(
                cls,
                parler_field_name,
                graphene.String(
                    language=TranslationLanguage(),
                    resolver=partial(_parler_field_resolver, parler_field_name),
                ),
            )

    @classmethod
    def __init_subclass_with_meta__(
        cls,
        model=None,
        registry=None,
        skip_registry=False,
        only_fields=None,
        fields=None,
        exclude_fields=None,
        exclude=None,
        filter_fields=None,
        filterset_class=None,
        connection=None,
        connection_class=None,
        use_connection=None,
        interfaces=(),
        convert_choices_to_enum=True,
        _meta=None,
        **options,
    ):
        assert issubclass(model, TranslatableModel), (
            'You need to pass a valid Django Parler Model in {}.Meta, received "{}".'
        ).format(cls.__name__, model)

        # Notice: only_fields and exclude_fields are deprecated and are not used here
        cls._add_parler_fields_to_type(model, fields, exclude)

        super().__init_subclass_with_meta__(
            model=model,
            registry=registry,
            skip_registry=skip_registry,
            only_fields=only_fields,
            fields=fields,
            exclude_fields=exclude_fields,
            exclude=exclude,
            filter_fields=filter_fields,
            filterset_class=filterset_class,
            connection=connection,
            connection_class=connection_class,
            use_connection=use_connection,
            interfaces=interfaces,
            convert_choices_to_enum=convert_choices_to_enum,
            _meta=_meta,
            **options,
        )


class AllowedDataFieldsMiddleware:

    def resolve(self, next, root, info, **kwargs):
        if getattr(root, "check_allowed_data_fields", False):
            field_name = to_snake_case(getattr(info, "field_name", ""))

            service = getattr(info.context, "service", None)
            if not service:
                if settings.ENABLE_ALLOWED_DATA_FIELDS_RESTRICTION:
                    raise ServiceNotIdentifiedError("Service not identified")

                logging.warning(
                    "Allowed data field exception would occur: Service not identified. Field name: %s",
                    field_name,
                )

                return next(root, info, **kwargs)

            if not root.is_field_allowed_for_service(field_name, service):
                if settings.ENABLE_ALLOWED_DATA_FIELDS_RESTRICTION:
                    raise FieldNotAllowedError(
                        "Field is not allowed for service.", field_name=field_name
                    )

                logging.warning(
                    "Allowed data field exception would occur. Field (%s) is not allowed for service %s.",
                    field_name,
                    info.context.service,
                )

        return next(root, info, **kwargs)
