from rest_framework.reverse import reverse

from utils.test_utils import check_disallowed_methods, get

CONCEPTS_OF_INTEREST_LIST = reverse("interest-concept-list")

GEO_DIVISION_LIST = reverse("geo-division-list")


def get_interest_concept_url(pk=1):
    return reverse("interest-concept-detail", kwargs={"pk": pk})


def get_geodivision_url(pk=1):
    return reverse("geo-division-detail", kwargs={"pk": pk})


def test_check_disallowed_method_util(user_api_client):
    # test only one method for one url
    only_put_method = "put"
    check_disallowed_methods(
        user_api_client, CONCEPTS_OF_INTEREST_LIST, only_put_method
    )

    # test multiple methods for multiple urls
    interest_concepts_urls = [get_interest_concept_url(1), get_interest_concept_url(2)]
    other_disallowed_methods = ("patch", "delete")
    check_disallowed_methods(
        user_api_client, interest_concepts_urls, other_disallowed_methods
    )


def test_concepts_of_interest_readonly(user_api_client):
    list_disallowed_methods = ("post", "put", "patch", "delete")
    check_disallowed_methods(
        user_api_client, CONCEPTS_OF_INTEREST_LIST, list_disallowed_methods
    )
    check_disallowed_methods(
        user_api_client, get_interest_concept_url(), list_disallowed_methods
    )


def test_geodivisions_readonly(user_api_client):
    list_disallowed_methods = ("post", "put", "patch", "delete")
    check_disallowed_methods(
        user_api_client, GEO_DIVISION_LIST, list_disallowed_methods
    )
    check_disallowed_methods(
        user_api_client, get_geodivision_url(), list_disallowed_methods
    )


def test_translations_formatting(api_client, concept):
    fi_label = "konsepti"
    en_label = "concept"

    concept.set_current_language("fi")
    concept.label = fi_label
    concept.save()

    concept.set_current_language("en")
    concept.label = en_label
    concept.save()

    concept_api_result = get(api_client, get_interest_concept_url(concept.pk))
    expected_result = {
        "code": concept.code,
        "vocabulary": concept.vocabulary.prefix,
        "label": {"en": en_label, "fi": fi_label},
    }

    assert concept_api_result == expected_result
