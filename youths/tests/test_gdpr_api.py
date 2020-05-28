from django.urls import reverse


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
