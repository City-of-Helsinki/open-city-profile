import pytest
from django.urls import reverse

from youths.models import YouthProfile

TRUE_VALUES = ["true", "True", "TRUE", "1", 1, True]
FALSE_VALUES = ["false", "False", "FALSE", "0", 0, False]


def test_disabled_gdpr_api_responds_with_404(settings, api_client, youth_profile):
    settings.GDPR_API_ENABLED = False
    response = api_client.get(
        reverse("youths:gdpr", kwargs={"pk": youth_profile.profile.id})
    )
    assert response.status_code == 404

    response = api_client.delete(
        reverse("youths:gdpr", kwargs={"pk": youth_profile.profile.id})
    )
    assert response.status_code == 404


def test_get_profile_information_from_gdpr_api(api_client, youth_profile, snapshot):
    response = api_client.get(
        reverse("youths:gdpr", kwargs={"pk": youth_profile.profile.id})
    )

    assert response.status_code == 200
    snapshot.assert_match(response.json())


@pytest.mark.parametrize("true_value", TRUE_VALUES)
def test_delete_profile_dry_run_data(true_value, api_client, youth_profile):
    response = api_client.delete(
        reverse("youths:gdpr", kwargs={"pk": youth_profile.profile.id}),
        data={"dry_run": true_value},
        format="json",
    )

    assert response.status_code == 204
    assert YouthProfile.objects.count() == 1


@pytest.mark.parametrize("true_value", TRUE_VALUES)
def test_delete_profile_dry_run_query_params(true_value, api_client, youth_profile):
    response = api_client.delete(
        reverse("youths:gdpr", kwargs={"pk": youth_profile.profile.id})
        + f"?dry_run={true_value}",
    )

    assert response.status_code == 204
    assert YouthProfile.objects.count() == 1


def test_delete_profile(api_client, youth_profile):
    response = api_client.delete(
        reverse("youths:gdpr", kwargs={"pk": youth_profile.profile.id})
    )

    assert response.status_code == 204
    assert YouthProfile.objects.count() == 0


@pytest.mark.parametrize("false_value", FALSE_VALUES)
def test_delete_profile_dry_run_query_params_false(
    false_value, api_client, youth_profile
):
    response = api_client.delete(
        reverse("youths:gdpr", kwargs={"pk": youth_profile.profile.id})
        + f"?dry_run={false_value}",
    )

    assert response.status_code == 204
    assert YouthProfile.objects.count() == 0


@pytest.mark.parametrize("false_value", FALSE_VALUES)
def test_delete_profile_dry_run_data_false(false_value, api_client, youth_profile):
    response = api_client.delete(
        reverse("youths:gdpr", kwargs={"pk": youth_profile.profile.id}),
        data={"dry_run": false_value},
        format="json",
    )

    assert response.status_code == 204
    assert YouthProfile.objects.count() == 0
