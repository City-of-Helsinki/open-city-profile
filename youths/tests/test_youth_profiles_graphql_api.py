import uuid
from datetime import date, datetime
from string import Template

from django.utils import timezone
from freezegun import freeze_time
from graphql_relay.node.node import to_global_id

from open_city_profile.consts import (
    CANNOT_SET_PHOTO_USAGE_PERMISSION_IF_UNDER_15_YEARS_ERROR,
)
from profiles.tests.factories import EmailFactory
from youths.enums import YouthLanguage
from youths.tests.factories import ProfileFactory, YouthProfileFactory


def test_anon_user_query_should_fail(rf, youth_profile, anon_user_gql_client):
    request = rf.post("/graphql")
    request.user = anon_user_gql_client.user

    t = Template(
        """
        {
            youthProfile(profileId: "${profileId}") {
                schoolClass
            }
        }
        """
    )
    query = t.substitute(profileId=uuid.uuid4())
    expected_data = {"youthProfile": None}
    executed = anon_user_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data


def test_normal_user_query_by_id_should_fail(rf, youth_profile, user_gql_client):
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    t = Template(
        """
        {
            youthProfile(profileId: "${profileId}") {
                schoolClass
            }
        }
        """
    )
    query = t.substitute(profileId=uuid.uuid4())
    expected_data = {"youthProfile": None}
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data


def test_normal_user_can_query_own_youth_profile(rf, user_gql_client):
    request = rf.post("/graphql")
    request.user = user_gql_client.user
    profile = ProfileFactory(user=user_gql_client.user)
    youth_profile = YouthProfileFactory(profile=profile)

    query = """
        {
            youthProfile {
                schoolClass
                membershipNumber
            }
        }
    """
    expected_data = {
        "youthProfile": {
            "schoolClass": youth_profile.school_class,
            "membershipNumber": youth_profile.membership_number,
        }
    }
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data


def test_normal_user_can_query_own_youth_profile_through_my_profile(
    rf, user_gql_client
):
    request = rf.post("/graphql")
    request.user = user_gql_client.user
    profile = ProfileFactory(user=user_gql_client.user)
    youth_profile = YouthProfileFactory(profile=profile)

    query = """
        {
            myProfile{
                youthProfile {
                    schoolClass
                    membershipNumber
                }
            }
        }
    """
    expected_data = {
        "myProfile": {
            "youthProfile": {
                "schoolClass": youth_profile.school_class,
                "membershipNumber": youth_profile.membership_number,
            }
        }
    }
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data


def test_superuser_can_query_by_id(rf, youth_profile, superuser_gql_client):
    request = rf.post("/graphql")
    request.user = superuser_gql_client.user

    t = Template(
        """
        {
            youthProfile(profileId: "${profileId}") {
                schoolClass
            }
        }
        """
    )
    query = t.substitute(
        profileId=to_global_id(type="ProfileNode", id=youth_profile.profile.pk)
    )
    expected_data = {"youthProfile": {"schoolClass": youth_profile.school_class}}
    executed = superuser_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data


def test_normal_user_can_create_youth_profile_mutation(rf, user_gql_client):
    request = rf.post("/graphql")
    request.user = user_gql_client.user
    profile = ProfileFactory(user=user_gql_client.user)

    t = Template(
        """
        mutation{
            createMyYouthProfile(
                input: {
                    youthProfile: {
                        schoolClass: "${schoolClass}"
                        schoolName: "${schoolName}"
                        languageAtHome: ${language}
                        approverEmail: "${approverEmail}"
                        birthDate: "${birthDate}"
                    }

                }
            )
            {
                youthProfile {
                    schoolClass
                    schoolName
                    approverEmail
                    birthDate
                }
            }
        }
        """
    )
    creation_data = {
        "profileId": profile.pk,
        "schoolClass": "2A",
        "schoolName": "Alakoulu",
        "approverEmail": "hyvaksyja@ex.com",
        "language": YouthLanguage.FINNISH.name,
        "birthDate": "2004-04-11",
    }
    query = t.substitute(**creation_data)
    expected_data = {
        "youthProfile": {
            "schoolClass": creation_data["schoolClass"],
            "schoolName": creation_data["schoolName"],
            "approverEmail": creation_data["approverEmail"],
            "birthDate": creation_data["birthDate"],
        }
    }
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]["createMyYouthProfile"]) == expected_data


def test_user_can_create_youth_profile_with_photo_usage_field_if_over_15_years_old(
    rf, user_gql_client
):
    request = rf.post("/graphql")
    request.user = user_gql_client.user
    profile = ProfileFactory(user=user_gql_client.user)
    today = date.today()

    t = Template(
        """
        mutation{
            createMyYouthProfile(
                input: {
                    youthProfile: {
                        photoUsageApproved: ${photoUsageApproved}
                        approverEmail: "${approverEmail}"
                        birthDate: "${birthDate}"
                    }

                }
            )
            {
                youthProfile {
                    photoUsageApproved
                    approverEmail
                    birthDate
                }
            }
        }
        """
    )
    creation_data = {
        "profileId": profile.pk,
        "approverEmail": "hyvaksyja@ex.com",
        "photoUsageApproved": "true",
        "birthDate": today.replace(year=today.year - 15, day=today.day - 1).strftime(
            "%Y-%m-%d"
        ),
    }
    query = t.substitute(**creation_data)
    expected_data = {
        "youthProfile": {
            "photoUsageApproved": True,
            "approverEmail": creation_data["approverEmail"],
            "birthDate": creation_data["birthDate"],
        }
    }
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]["createMyYouthProfile"]) == expected_data


def test_user_cannot_create_youth_profile_with_photo_usage_field_if_under_15_years_old(
    rf, user_gql_client
):
    request = rf.post("/graphql")
    request.user = user_gql_client.user
    profile = ProfileFactory(user=user_gql_client.user)
    today = date.today()

    t = Template(
        """
        mutation{
            createMyYouthProfile(
                input: {
                    youthProfile: {
                        photoUsageApproved: ${photoUsageApproved}
                        approverEmail: "${approverEmail}"
                        birthDate: "${birthDate}"
                    }

                }
            )
            {
                youthProfile {
                    photoUsageApproved
                    approverEmail
                    birthDate
                }
            }
        }
        """
    )
    creation_data = {
        "profileId": profile.pk,
        "approverEmail": "hyvaksyja@ex.com",
        "photoUsageApproved": "true",
        "birthDate": today.replace(year=today.year - 15, day=today.day + 1).strftime(
            "%Y-%m-%d"
        ),
    }
    query = t.substitute(**creation_data)
    executed = user_gql_client.execute(query, context=request)
    assert "errors" in executed
    assert (
        executed["errors"][0]["extensions"]["code"]
        == CANNOT_SET_PHOTO_USAGE_PERMISSION_IF_UNDER_15_YEARS_ERROR
    )


def test_normal_user_can_create_youth_profile_through_my_profile_mutation(
    rf, user_gql_client
):
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    t = Template(
        """
            mutation {
                createMyProfile(
                    input: {
                        profile: {
                            nickname: \"${nickname}\",
                            youthProfile: {
                                schoolClass: "${schoolClass}"
                                schoolName: "${schoolName}"
                                languageAtHome: ${language}
                                approverEmail: "${approverEmail}"
                                birthDate: "${birthDate}"
                            }
                        }
                    }
                ) {
                profile{
                    nickname,
                    youthProfile {
                        schoolClass
                        schoolName
                        approverEmail
                        birthDate
                    }
                }
            }
            }
        """
    )

    creation_data = {
        "nickname": "Larry",
        "schoolClass": "2A",
        "schoolName": "Alakoulu",
        "approverEmail": "hyvaksyja@ex.com",
        "language": YouthLanguage.FINNISH.name,
        "birthDate": "2004-04-11",
    }

    query = t.substitute(**creation_data)

    expected_data = {
        "createMyProfile": {
            "profile": {
                "nickname": "Larry",
                "youthProfile": {
                    "schoolClass": creation_data["schoolClass"],
                    "schoolName": creation_data["schoolName"],
                    "approverEmail": creation_data["approverEmail"],
                    "birthDate": creation_data["birthDate"],
                },
            }
        }
    }
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data


def test_normal_user_can_update_youth_profile_mutation(rf, user_gql_client):
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    profile = ProfileFactory(user=user_gql_client.user)
    youth_profile = YouthProfileFactory(profile=profile)

    t = Template(
        """
        mutation{
            updateMyYouthProfile(
                input: {
                    youthProfile: {
                        schoolClass: "${schoolClass}"
                        birthDate: "${birthDate}"
                    }
                }
            )
            {
                youthProfile {
                    schoolClass
                    schoolName
                    birthDate
                }
            }
        }
        """
    )
    creation_data = {"schoolClass": "2A", "birthDate": "2002-02-02"}
    query = t.substitute(**creation_data)
    expected_data = {
        "youthProfile": {
            "schoolClass": creation_data["schoolClass"],
            "schoolName": youth_profile.school_name,
            "birthDate": creation_data["birthDate"],
        }
    }
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]["updateMyYouthProfile"]) == expected_data


def test_user_can_update_youth_profile_with_photo_usage_field_if_over_15_years_old(
    rf, user_gql_client
):
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    profile = ProfileFactory(user=user_gql_client.user)
    YouthProfileFactory(profile=profile)
    today = date.today()

    t = Template(
        """
        mutation{
            updateMyYouthProfile(
                input: {
                    youthProfile: {
                        photoUsageApproved: ${photoUsageApproved}
                        birthDate: "${birthDate}"
                    }
                }
            )
            {
                youthProfile {
                    photoUsageApproved
                    birthDate
                }
            }
        }
        """
    )
    creation_data = {
        "photoUsageApproved": "true",
        "birthDate": today.replace(year=today.year - 15, day=today.day - 1).strftime(
            "%Y-%m-%d"
        ),
    }
    query = t.substitute(**creation_data)
    expected_data = {
        "youthProfile": {
            "photoUsageApproved": True,
            "birthDate": creation_data["birthDate"],
        }
    }
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]["updateMyYouthProfile"]) == expected_data


def test_user_cannot_update_youth_profile_with_photo_usage_field_if_under_15_years_old(
    rf, user_gql_client
):
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    profile = ProfileFactory(user=user_gql_client.user)
    YouthProfileFactory(profile=profile)
    today = date.today()

    t = Template(
        """
        mutation{
            updateMyYouthProfile(
                input: {
                    youthProfile: {
                        photoUsageApproved: ${photoUsageApproved}
                        birthDate: "${birthDate}"
                    }
                }
            )
            {
                youthProfile {
                    photoUsageApproved
                    birthDate
                }
            }
        }
        """
    )
    creation_data = {
        "photoUsageApproved": "true",
        "birthDate": today.replace(year=today.year - 15, day=today.day + 1).strftime(
            "%Y-%m-%d"
        ),
    }
    query = t.substitute(**creation_data)
    executed = user_gql_client.execute(query, context=request)
    assert "errors" in executed
    assert (
        executed["errors"][0]["extensions"]["code"]
        == CANNOT_SET_PHOTO_USAGE_PERMISSION_IF_UNDER_15_YEARS_ERROR
    )


def test_user_can_update_youth_profile_with_photo_usage_field_if_over_15_years_old_based_on_existing_birth_date(
    rf, user_gql_client
):
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    profile = ProfileFactory(user=user_gql_client.user)
    today = date.today()
    birth_date = today.replace(year=today.year - 15, day=today.day - 1)
    YouthProfileFactory(profile=profile, birth_date=birth_date)

    t = Template(
        """
        mutation{
            updateMyYouthProfile(
                input: {
                    youthProfile: {
                        photoUsageApproved: ${photoUsageApproved}
                    }
                }
            )
            {
                youthProfile {
                    photoUsageApproved
                }
            }
        }
        """
    )
    creation_data = {
        "photoUsageApproved": "true",
    }
    query = t.substitute(**creation_data)
    expected_data = {"youthProfile": {"photoUsageApproved": True}}
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]["updateMyYouthProfile"]) == expected_data


def test_user_cannot_update_youth_profile_with_photo_usage_field_if_under_15_years_old_based_on_existing_birth_date(
    rf, user_gql_client
):
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    profile = ProfileFactory(user=user_gql_client.user)
    today = date.today()
    birth_date = today.replace(year=today.year - 15, day=today.day + 1)
    YouthProfileFactory(profile=profile, birth_date=birth_date)

    t = Template(
        """
        mutation{
            updateMyYouthProfile(
                input: {
                    youthProfile: {
                        photoUsageApproved: ${photoUsageApproved}
                    }
                }
            )
            {
                youthProfile {
                    photoUsageApproved
                }
            }
        }
        """
    )
    creation_data = {
        "photoUsageApproved": "true",
    }
    query = t.substitute(**creation_data)
    executed = user_gql_client.execute(query, context=request)
    assert "errors" in executed
    assert (
        executed["errors"][0]["extensions"]["code"]
        == CANNOT_SET_PHOTO_USAGE_PERMISSION_IF_UNDER_15_YEARS_ERROR
    )


def test_normal_user_can_update_youth_profile__through_my_profile_mutation(
    rf, user_gql_client
):
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    profile = ProfileFactory(user=user_gql_client.user)
    youth_profile = YouthProfileFactory(profile=profile)

    t = Template(
        """
            mutation {
                updateMyProfile(
                    input: {
                        profile: {
                            nickname: \"${nickname}\",
                            youthProfile: {
                                schoolClass: "${schoolClass}"
                                birthDate: "${birthDate}"
                            }
                        }
                    }
                ) {
                profile{
                    nickname,
                    youthProfile {
                        schoolClass
                        schoolName
                        birthDate
                    }
                }
            }
            }
        """
    )

    creation_data = {
        "nickname": "Larry",
        "schoolClass": "2A",
        "birthDate": "2002-02-02",
    }

    query = t.substitute(**creation_data)

    expected_data = {
        "updateMyProfile": {
            "profile": {
                "nickname": "Larry",
                "youthProfile": {
                    "schoolClass": creation_data["schoolClass"],
                    "schoolName": youth_profile.school_name,
                    "birthDate": creation_data["birthDate"],
                },
            }
        }
    }
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data


def test_anon_user_query_with_token(rf, youth_profile, anon_user_gql_client):
    request = rf.post("/graphql")
    request.user = anon_user_gql_client.user

    t = Template(
        """
        {
            youthProfileByApprovalToken(token: "${approvalToken}") {
                schoolClass
            }
        }
        """
    )
    query = t.substitute(approvalToken=youth_profile.approval_token)
    expected_data = {
        "youthProfileByApprovalToken": {"schoolClass": youth_profile.school_class}
    }
    executed = anon_user_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data


def test_anon_user_can_approve_with_token(rf, anon_user_gql_client):
    profile = ProfileFactory()
    EmailFactory(primary=True, profile=profile)
    youth_profile = YouthProfileFactory(profile=profile)

    request = rf.post("/graphql")
    request.user = anon_user_gql_client.user

    t = Template(
        """
        mutation{
            approveYouthProfile(
                input: {
                    approvalToken: "${token}",
                    approvalData: {
                        photoUsageApproved: true
                        approverFirstName: "${approver_first_name}"
                        approverLastName: "${approver_last_name}"
                        approverPhone: "${approver_phone}"
                        approverEmail: "${approver_email}"
                        birthDate: "${birthDate}"
                    }
                }
            )
            {
                youthProfile {
                    photoUsageApproved
                    approverFirstName
                    approverLastName
                    approverPhone
                    approverEmail
                    birthDate
                }
            }
        }
        """
    )
    approval_data = {
        "token": youth_profile.approval_token,
        "approver_first_name": "Teppo",
        "approver_last_name": "Testi",
        "approver_phone": "0401234567",
        "approver_email": "teppo@testi.com",
        "birthDate": "2002-02-02",
    }
    query = t.substitute(**approval_data)
    expected_data = {
        "youthProfile": {
            "photoUsageApproved": True,
            "approverFirstName": approval_data["approver_first_name"],
            "approverLastName": approval_data["approver_last_name"],
            "approverPhone": approval_data["approver_phone"],
            "approverEmail": approval_data["approver_email"],
            "birthDate": approval_data["birthDate"],
        }
    }
    executed = anon_user_gql_client.execute(query, context=request)
    assert dict(executed["data"]["approveYouthProfile"]) == expected_data


def test_missing_primary_email_error(rf, youth_profile, anon_user_gql_client):
    request = rf.post("/graphql")
    request.user = anon_user_gql_client.user

    t = Template(
        """
        mutation{
            approveYouthProfile(
                input: {
                    approvalToken: "${token}",
                    approvalData: {
                        photoUsageApproved: true
                        approverFirstName: "${approver_first_name}"
                        approverLastName: "${approver_last_name}"
                        approverPhone: "${approver_phone}"
                        approverEmail: "${approver_email}"
                        birthDate: "${birthDate}"
                    }
                }
            )
            {
                youthProfile {
                    photoUsageApproved
                    approverFirstName
                    approverLastName
                    approverPhone
                    approverEmail
                    birthDate
                }
            }
        }
        """
    )
    approval_data = {
        "token": youth_profile.approval_token,
        "approver_first_name": "Teppo",
        "approver_last_name": "Testi",
        "approver_phone": "0401234567",
        "approver_email": "teppo@testi.com",
        "birthDate": "2002-02-02",
    }
    query = t.substitute(**approval_data)
    executed = anon_user_gql_client.execute(query, context=request)

    assert (
        executed["errors"][0].get("extensions").get("code")
        == "PROFILE_HAS_NO_PRIMARY_EMAIL_ERROR"
    )


def test_youth_profile_should_show_correct_membership_status(rf, user_gql_client):
    request = rf.post("/graphql")
    request.user = user_gql_client.user
    profile = ProfileFactory(user=user_gql_client.user)
    youth_profile = YouthProfileFactory(profile=profile)

    query = """
        {
            youthProfile {
                membershipStatus
            }
        }
    """
    expected_data = {"youthProfile": {"membershipStatus": "PENDING"}}
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data

    youth_profile.approved_time = timezone.now()
    youth_profile.save()
    expected_data = {"youthProfile": {"membershipStatus": "ACTIVE"}}
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data

    youth_profile.expiration = date.today()
    youth_profile.save()
    expected_data = {"youthProfile": {"membershipStatus": "EXPIRED"}}
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]) == expected_data

    query = """
        {
            youthProfile {
                membershipStatus
                renewable
            }
        }
    """

    with freeze_time("2020-05-01"):
        youth_profile.expiration = date(2020, 7, 31)
        youth_profile.approved_time = date(2019, 8, 1)
        youth_profile.save()
        expected_data = {
            "youthProfile": {"membershipStatus": "ACTIVE", "renewable": True}
        }
        executed = user_gql_client.execute(query, context=request)
        assert dict(executed["data"]) == expected_data

    with freeze_time("2020-08-01"):
        youth_profile.expiration = date(2021, 7, 31)
        youth_profile.approved_time = date(2020, 4, 30)
        youth_profile.save()
        expected_data = {
            "youthProfile": {"membershipStatus": "EXPIRED", "renewable": False}
        }
        executed = user_gql_client.execute(query, context=request)
        assert dict(executed["data"]) == expected_data

    with freeze_time("2020-05-01"):
        youth_profile.approved_time = timezone.datetime(2020, 1, 1)
        youth_profile.expiration = date(2021, 7, 31)
        youth_profile.save()
        expected_data = {
            "youthProfile": {"membershipStatus": "RENEWING", "renewable": False}
        }
        executed = user_gql_client.execute(query, context=request)
        assert dict(executed["data"]) == expected_data


def test_youth_profile_expiration_should_renew_and_be_approvable(
    rf, user_gql_client, anon_user_gql_client
):
    request = rf.post("/graphql")
    request.user = user_gql_client.user
    profile = ProfileFactory(user=user_gql_client.user)
    EmailFactory(primary=True, profile=profile)

    # Let's create a youth profile in the 2020
    with freeze_time("2020-05-02"):
        youth_profile = YouthProfileFactory(
            profile=profile, approved_time=datetime.today()
        )

    # In the year 2021, let's renew it
    with freeze_time("2021-05-01"):
        mutation = """
            mutation {
                renewMyYouthProfile(input:{}) {
                    youthProfile {
                        membershipStatus
                    }
                }
            }
        """
        executed = user_gql_client.execute(mutation, context=request)
        expected_data = {
            "renewMyYouthProfile": {"youthProfile": {"membershipStatus": "RENEWING"}}
        }
        assert dict(executed["data"]) == expected_data

    # Later in the year 2021, let's check our membership status
    with freeze_time("2021-08-01"):
        query = """
            {
                youthProfile {
                    membershipStatus
                }
            }
        """
        expected_data = {"youthProfile": {"membershipStatus": "EXPIRED"}}
        executed = user_gql_client.execute(query, context=request)
        assert dict(executed["data"]) == expected_data

    # Let's go back in time a few months and re-approve the membership
    with freeze_time("2021-05-02"):
        request.user = anon_user_gql_client.user

        t = Template(
            """
            mutation{
                approveYouthProfile(
                    input: {
                        approvalToken: "${token}",
                        approvalData: {}
                    }
                )
                {
                    youthProfile {
                        membershipStatus
                    }
                }
            }
            """
        )
        youth_profile.refresh_from_db()
        approval_data = {"token": youth_profile.approval_token}
        query = t.substitute(**approval_data)
        expected_data = {
            "approveYouthProfile": {"youthProfile": {"membershipStatus": "ACTIVE"}}
        }
        executed = anon_user_gql_client.execute(query, context=request)
        assert dict(executed["data"]) == expected_data
