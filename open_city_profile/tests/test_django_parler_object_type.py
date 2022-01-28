import pytest
from graphene import Field, ObjectType, Schema, String
from graphene_django.types import ALL_FIELDS

from open_city_profile.graphene import DjangoParlerObjectType
from open_city_profile.tests.app.models import NonTranslatedModel, TranslatedModel


def test_cannot_use_non_parler_model():
    with pytest.raises(AssertionError):

        class TranslatedModelType(DjangoParlerObjectType):
            class Meta:
                model = NonTranslatedModel


def test_translated_field_is_added_automatically():
    class TranslatedModelType(DjangoParlerObjectType):
        class Meta:
            model = TranslatedModel

    assert hasattr(TranslatedModelType, "translated_field")
    assert isinstance(TranslatedModelType.translated_field, String)


def test_translated_field_is_added_if_its_in_meta_fields():
    class TranslatedModelType(DjangoParlerObjectType):
        class Meta:
            model = TranslatedModel
            fields = ("translated_field",)

    assert hasattr(TranslatedModelType, "translated_field")
    assert isinstance(TranslatedModelType.translated_field, String)


def test_translated_field_is_added_if_all_fields_is_used():
    class TranslatedModelType(DjangoParlerObjectType):
        class Meta:
            model = TranslatedModel
            fields = ALL_FIELDS

    assert hasattr(TranslatedModelType, "translated_field")
    assert isinstance(TranslatedModelType.translated_field, String)


def test_translated_field_is_not_added_if_its_not_in_meta_fields():
    class TranslatedModelType(DjangoParlerObjectType):
        class Meta:
            model = TranslatedModel
            fields = ("non_translated_field",)

    assert not hasattr(TranslatedModelType, "translated_field")


def test_translated_field_is_not_added_if_its_excluded():
    class TranslatedModelType(DjangoParlerObjectType):
        class Meta:
            model = TranslatedModel
            exclude = ("translated_field",)

    assert not hasattr(TranslatedModelType, "translated_field")


def test_existing_attribute_is_not_overwritten_with_translated_field():
    class TranslatedModelType(DjangoParlerObjectType):
        translated_field = "dummy value"

        class Meta:
            model = TranslatedModel

    assert TranslatedModelType.translated_field == "dummy value"


def test_translated_field_query():
    class TranslatedModelType(DjangoParlerObjectType):
        class Meta:
            model = TranslatedModel

    tm = TranslatedModel.objects.create(non_translated_field="Test string")
    tm.set_current_language("fi")
    tm.translated_field = "Translated field in finnish"
    tm.set_current_language("en")
    tm.translated_field = "Translated field in english"
    tm.save()

    class Query(ObjectType):
        translated_model = Field(TranslatedModelType)

        def resolve_translated_model(self, info):
            return tm

    schema = Schema(query=Query)

    query = """
        query {
            translatedModel {
                nonTranslatedField
                translatedFieldInFinnish: translatedField(language: FI)
                translatedFieldInEnglish: translatedField(language: EN)
            }
        }
    """

    result = schema.execute(query)

    expected_data = {
        "translatedModel": {
            "nonTranslatedField": "Test string",
            "translatedFieldInFinnish": "Translated field in finnish",
            "translatedFieldInEnglish": "Translated field in english",
        }
    }

    assert result.data == expected_data
