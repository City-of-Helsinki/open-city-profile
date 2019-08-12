from datetime import date

import reversion
from freezegun import freeze_time
from rest_framework.reverse import reverse
from reversion.models import Version

from utils.test_utils import delete, get, patch_update, post_create
from youths.models import YouthProfile
from youths.tests.factories import YouthProfileFactory

PROFILE_URL = reverse("profile-list")
YOUTH_PROFILE_URL = reverse("youthprofile-list")

NEW_YOUTH_DATA = {
    "ssn": "010110ASDF",
    "school_name": "Kontulan Alakoulu",
    "school_class": "1A",
}


def get_youth_profile_url(youth_profile):
    return reverse(
        "youthprofile-detail",
        kwargs={"profile__user__uuid": youth_profile.profile.user.uuid},
    )


def test_unauthenticated_user_cannot_access(api_client):
    get(api_client, YOUTH_PROFILE_URL, 401)


def test_user_can_see_only_own_youth_profile(user_api_client, youth_profile):
    other_youth_profile = YouthProfileFactory()

    data = get(user_api_client, YOUTH_PROFILE_URL)
    results = data["results"]
    assert len(results) == 1
    assert YouthProfile.objects.count() > 1

    get(user_api_client, get_youth_profile_url(other_youth_profile), status_code=404)


def test_superuser_can_view_all_youth_profiles(superuser_api_client):
    a_youth_profile = YouthProfileFactory()
    other_youth_profile = YouthProfileFactory()  # noqa

    data = get(superuser_api_client, YOUTH_PROFILE_URL)
    results = data["results"]
    assert len(results) == YouthProfile.objects.count()

    get(superuser_api_client, get_youth_profile_url(a_youth_profile), status_code=200)


def test_post_create_own_youth_profile(user_api_client):
    assert YouthProfile.objects.count() == 0

    post_create(user_api_client, PROFILE_URL)
    post_create(user_api_client, YOUTH_PROFILE_URL, data=NEW_YOUTH_DATA)

    assert YouthProfile.objects.count() == 1
    youth_profile = YouthProfile.objects.latest("id")
    assert youth_profile.profile.user == user_api_client.user


def test_cannot_create_multiple_youth_profiles(user_api_client, youth_profile):
    assert YouthProfile.objects.count() == 1

    post_create(user_api_client, YOUTH_PROFILE_URL, NEW_YOUTH_DATA, status_code=409)

    assert YouthProfile.objects.count() == 1


def test_user_can_delete_own_youth_profile(user_api_client, youth_profile):
    assert YouthProfile.objects.count() == 1

    youth_profile_url = get_youth_profile_url(youth_profile)
    delete(user_api_client, youth_profile_url)

    assert YouthProfile.objects.count() == 0


def test_user_cannot_delete_other_youth_profiles(user_api_client, youth_profile):
    other_youth_profile = YouthProfileFactory()
    assert YouthProfile.objects.count() == 2

    # Response status should be 404 as other profiles are hidden from the user
    delete(user_api_client, get_youth_profile_url(other_youth_profile), status_code=404)

    assert YouthProfile.objects.count() == 2


def test_patch_update_own_youth_profile(user_api_client, youth_profile):
    assert YouthProfile.objects.count() == 1

    youth_profile_url = get_youth_profile_url(youth_profile)
    new_school_data = {"school_class": "6C"}

    patch_update(user_api_client, youth_profile_url, new_school_data)

    youth_profile.refresh_from_db()
    assert youth_profile.school_class == new_school_data["school_class"]


def test_superuser_can_patch_update_youth_profile(superuser_api_client, youth_profile):
    new_allergy_data = {"allergies": "foods, animals"}
    assert youth_profile.allergies != new_allergy_data["allergies"]

    patch_update(
        superuser_api_client, get_youth_profile_url(youth_profile), new_allergy_data
    )
    youth_profile.refresh_from_db()
    assert youth_profile.allergies == new_allergy_data["allergies"]
    assert youth_profile.profile.user != superuser_api_client.user


def test_expected_profile_data_fields(user_api_client, youth_profile):
    expected_fields = {
        "profile",
        "ssn",
        "school_name",
        "school_class",
        "expiration",
        "preferred_language",
        "volunteer_info",
        "gender",
        "illnesses",
        "allergies",
        "notes",
    }

    youth_profile_url = get_youth_profile_url(youth_profile)
    youth_profile_endpoint_data = get(user_api_client, youth_profile_url)

    assert set(youth_profile_endpoint_data.keys()) == expected_fields


def test_update_own_profile_creates_change_log_entry(user_api_client):
    post_create(user_api_client, PROFILE_URL)
    with reversion.create_revision():
        post_create(user_api_client, YOUTH_PROFILE_URL, NEW_YOUTH_DATA)

    youth_profile = YouthProfile.objects.latest("id")
    versions = Version.objects.get_for_object(youth_profile)
    assert len(versions) == 1

    youth_profile_url = get_youth_profile_url(youth_profile)
    allergy_data = {"allergies": "foods, animals"}
    patch_update(user_api_client, youth_profile_url, allergy_data)

    youth_profile.refresh_from_db()
    versions = Version.objects.get_for_object(youth_profile)
    assert len(versions) == 2
    assert versions[0].revision.user == user_api_client.user
    assert versions[0].field_dict["allergies"] == allergy_data["allergies"]


def test_admin_update_profile_creates_change_log_entry(
    user_api_client, superuser_api_client
):
    post_create(user_api_client, PROFILE_URL)
    with reversion.create_revision():
        post_create(user_api_client, YOUTH_PROFILE_URL, NEW_YOUTH_DATA)

    youth_profile = YouthProfile.objects.latest("id")
    versions = Version.objects.get_for_object(youth_profile)
    assert len(versions) == 1
    assert versions[0].revision.user == user_api_client.user

    youth_profile_url = get_youth_profile_url(youth_profile)
    allergy_data = {"allergies": "foods, animals"}
    patch_update(superuser_api_client, youth_profile_url, allergy_data)

    youth_profile.refresh_from_db()
    versions = Version.objects.get_for_object(youth_profile)
    assert len(versions) == 2
    assert versions[0].revision.user == superuser_api_client.user


@freeze_time("2019-01-01T00:00:00Z")
def test_spring_signup_expires_same_year(user_api_client):
    post_create(user_api_client, PROFILE_URL)
    post_create(user_api_client, YOUTH_PROFILE_URL, data=NEW_YOUTH_DATA)
    youth_profile = YouthProfile.objects.latest("id")
    assert youth_profile.expiration == date(year=2019, month=6, day=30)


@freeze_time("2019-09-01T00:00:00Z")
def test_fall_signup_expires_next_year(user_api_client):
    post_create(user_api_client, PROFILE_URL)
    post_create(user_api_client, YOUTH_PROFILE_URL, data=NEW_YOUTH_DATA)
    youth_profile = YouthProfile.objects.latest("id")
    assert youth_profile.expiration == date(year=2020, month=6, day=30)
