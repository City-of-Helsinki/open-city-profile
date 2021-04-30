import functools
from typing import Any, Iterable, Mapping

from django.core.exceptions import ValidationError as DjangoValidationError
from graphene_validator.errors import ValidationError


class MultiValidationError(ValidationError):
    def __init__(self, error_details, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._error_details = error_details

    @property
    def error_details(self) -> Iterable[Mapping[str, Any]]:
        return self._error_details

    @staticmethod
    def from_django_validation_error(django_error):
        errors = []

        for err in django_error.error_list:
            msg = err.message % err.params
            errors.append({"code": err.code, "message": msg})

        return MultiValidationError(errors)


def _field_validator(model, field, value, info, **input):
    try:
        return field.clean(value, model)
    except DjangoValidationError as e:
        raise MultiValidationError.from_django_validation_error(e)


def field_validations(**kwargs):
    model_classes = set(v[0] for v in kwargs.values())
    models = dict((model_class, model_class()) for model_class in model_classes)

    def decorator(cls):
        for field_name, (model_class, model_field_name) in kwargs.items():
            model = models[model_class]
            field = model._meta.get_field(model_field_name)

            validator = staticmethod(functools.partial(_field_validator, model, field))

            setattr(cls, f"validate_{field_name}", validator)

        return cls

    return decorator
