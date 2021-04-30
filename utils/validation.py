from typing import Any, Iterable, Mapping

from django.core.exceptions import ValidationError as DjangoValidationError
from graphene_validator.errors import ValidationError


class MultiValidationError(ValidationError):
    def __init__(self, error_details, *args):
        super().__init__(*args)
        self._error_details = error_details

    @property
    def error_details(self) -> Iterable[Mapping[str, Any]]:
        return self._error_details


def _multi_validation_error_from_django_validation_error(django_error):
    errors = []

    for err in django_error.error_list:
        msg = err.message % err.params
        errors.append({"code": err.code, "message": msg})

    return MultiValidationError(errors)


def model_field_validation(model_class, field_name, value):
    model = model_class()
    field = model._meta.get_field(field_name)

    try:
        return field.clean(value, model)
    except DjangoValidationError as e:
        raise _multi_validation_error_from_django_validation_error(e)
