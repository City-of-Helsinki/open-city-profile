import graphene
import pytest
from django.conf import settings
from django.utils import translation
from django.utils.translation import gettext
from graphene.test import Client
from graphene_federation import build_schema
from graphql import specified_directives

from open_city_profile.graphene import (
    HelTranslationDirective,
    HelTranslationLanguageType,
    HelTranslationMiddleware,
)


@pytest.mark.parametrize("language", [lang[0] for lang in settings.LANGUAGES])
def test_translation_middleware_changes_language_for_field(language):
    class Query(graphene.ObjectType):
        text = graphene.String()

        def resolve_text(self, info):
            # The string "Text" is translated in Django
            return gettext("Text")

    schema = build_schema(
        Query,
        directives=specified_directives + [HelTranslationDirective],
        types=[HelTranslationLanguageType],
    )
    client = Client(schema, middleware=[HelTranslationMiddleware()])

    query = f"""
        {{
            text
            text_translated: text @hel_translation(in: {language.upper()})
            text_other_directive: text @skip(if: false)
        }}
    """

    expected_text = gettext("Text")
    with translation.override(language):
        expected_text_translated = gettext("Text")

    result = client.execute(query)

    assert "errors" not in result
    assert result["data"]["text"] == expected_text
    assert result["data"]["text_other_directive"] == expected_text
    assert result["data"]["text_translated"] == expected_text_translated
