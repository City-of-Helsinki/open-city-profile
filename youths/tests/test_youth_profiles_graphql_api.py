import uuid
from datetime import date, datetime
from string import Template

from django.utils import timezone
from freezegun import freeze_time
from graphql_relay.node.node import to_global_id
from guardian.shortcuts import assign_perm

from open_city_profile.consts import (
    APPROVER_EMAIL_CANNOT_BE_EMPTY_FOR_MINORS_ERROR,
    CANNOT_CREATE_YOUTH_PROFILE_IF_UNDER_13_YEARS_OLD_ERROR,
    CANNOT_PERFORM_THIS_ACTION_WITH_GIVEN_SERVICE_TYPE_ERROR,
    CANNOT_SET_PHOTO_USAGE_PERMISSION_IF_UNDER_15_YEARS_ERROR,
    PERMISSION_DENIED_ERROR,
)
from open_city_profile.tests.factories import GroupFactory
from profiles.models import Profile
from profiles.tests.factories import EmailFactory
from services.enums import ServiceType
from services.tests.factories import ServiceFactory
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


def test_normal_user_over_18_years_old_can_create_approved_youth_profile_mutation(
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
                        schoolClass: "${schoolClass}"
                        schoolName: "${schoolName}"
                        birthDate: "${birthDate}"
                    }

                }
            )
            {
                youthProfile {
                    schoolClass
                    schoolName
                    birthDate
                    membershipStatus
                }
            }
        }
        """
    )
    creation_data = {
        "profileId": profile.pk,
        "schoolClass": "2A",
        "schoolName": "Alakoulu",
        "birthDate": today.replace(year=today.year - 18, day=today.day - 1).strftime(
            "%Y-%m-%d"
        ),
    }
    query = t.substitute(**creation_data)
    expected_data = {
        "youthProfile": {
            "schoolClass": creation_data["schoolClass"],
            "schoolName": creation_data["schoolName"],
            "birthDate": creation_data["birthDate"],
            "membershipStatus": "ACTIVE",
        }
    }
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]["createMyYouthProfile"]) == expected_data


def test_user_cannot_create_youth_profile_without_approver_email_field_if_under_18_years_old(
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
                        birthDate: "${birthDate}"
                    }

                }
            )
            {
                youthProfile {
                    birthDate
                }
            }
        }
        """
    )
    creation_data = {
        "profileId": profile.pk,
        "birthDate": today.replace(year=today.year - 18, day=today.day + 1).strftime(
            "%Y-%m-%d"
        ),
    }
    query = t.substitute(**creation_data)
    executed = user_gql_client.execute(query, context=request)
    assert "errors" in executed
    assert (
        executed["errors"][0]["extensions"]["code"]
        == APPROVER_EMAIL_CANNOT_BE_EMPTY_FOR_MINORS_ERROR
    )


def test_user_cannot_create_youth_profile_if_under_13_years_old(rf, user_gql_client):
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
        "birthDate": today.replace(year=today.year - 13, day=today.day + 1).strftime(
            "%Y-%m-%d"
        ),
    }
    query = t.substitute(**creation_data)
    executed = user_gql_client.execute(query, context=request)
    assert "errors" in executed
    assert (
        executed["errors"][0]["extensions"]["code"]
        == CANNOT_CREATE_YOUTH_PROFILE_IF_UNDER_13_YEARS_OLD_ERROR
    )


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
    creation_data = {"photoUsageApproved": "true"}
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
    creation_data = {"photoUsageApproved": "true"}
    query = t.substitute(**creation_data)
    executed = user_gql_client.execute(query, context=request)
    assert "errors" in executed
    assert (
        executed["errors"][0]["extensions"]["code"]
        == CANNOT_SET_PHOTO_USAGE_PERMISSION_IF_UNDER_15_YEARS_ERROR
    )


def test_normal_user_can_update_youth_profile_through_my_profile_mutation(
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


def test_normal_user_can_add_youth_profile_through_update_my_profile_mutation(
    rf, user_gql_client
):
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    ProfileFactory(user=user_gql_client.user)

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
                        birthDate
                        membershipStatus
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
                    "birthDate": creation_data["birthDate"],
                    "membershipStatus": "ACTIVE",
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
        youth_profile.expiration = date(2020, 8, 31)
        youth_profile.approved_time = date(2019, 8, 1)
        youth_profile.save()
        expected_data = {
            "youthProfile": {"membershipStatus": "ACTIVE", "renewable": True}
        }
        executed = user_gql_client.execute(query, context=request)
        assert dict(executed["data"]) == expected_data

    with freeze_time("2020-09-01"):
        youth_profile.expiration = date(2021, 8, 31)
        youth_profile.approved_time = date(2020, 4, 30)
        youth_profile.save()
        expected_data = {
            "youthProfile": {"membershipStatus": "EXPIRED", "renewable": False}
        }
        executed = user_gql_client.execute(query, context=request)
        assert dict(executed["data"]) == expected_data

        youth_profile.approved_time = timezone.datetime(2020, 1, 1)
        youth_profile.expiration = date(2021, 8, 31)
        youth_profile.save()
        expected_data = {
            "youthProfile": {"membershipStatus": "RENEWING", "renewable": False}
        }
        with freeze_time("2020-05-01"):
            executed = user_gql_client.execute(query, context=request)
            assert dict(executed["data"]) == expected_data
        with freeze_time("2020-08-31"):
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
        today = date.today()
        youth_profile = YouthProfileFactory(
            profile=profile,
            approved_time=datetime.today(),
            birth_date=today.replace(year=today.year - 15),
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
    with freeze_time("2021-09-01"):
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


def test_youth_profile_expiration_should_be_renewable_by_staff_user(
    rf, user_gql_client, anon_user_gql_client
):
    service = ServiceFactory(service_type=ServiceType.YOUTH_MEMBERSHIP)
    group = GroupFactory()
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_manage_profiles", group, service)
    profile = ProfileFactory()
    request = rf.post("/graphql")
    request.user = user
    EmailFactory(primary=True, profile=profile)

    # Let's create a youth profile in the 2020
    with freeze_time("2020-05-02"):
        today = date.today()
        youth_profile = YouthProfileFactory(
            profile=profile,
            approved_time=datetime.today(),
            birth_date=today.replace(year=today.year - 15),
        )

    # In the year 2021, let's renew it
    with freeze_time("2021-05-01"):
        t = Template(
            """
            mutation {
                renewYouthProfile(input:{
                    serviceType: ${service_type},
                    profileId: \"${profile_id}\"
                }) {
                    youthProfile {
                        membershipStatus
                    }
                }
            }
        """
        )
        mutation = t.substitute(
            service_type=ServiceType.YOUTH_MEMBERSHIP.name,
            profile_id=to_global_id(type="ProfileNode", id=profile.pk),
        )

        executed = user_gql_client.execute(mutation, context=request)
        expected_data = {
            "renewYouthProfile": {"youthProfile": {"membershipStatus": "RENEWING"}}
        }
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


def test_youth_profile_expiration_for_over_18_years_old_should_renew_and_change_to_active(
    rf, user_gql_client, anon_user_gql_client
):
    request = rf.post("/graphql")
    request.user = user_gql_client.user
    profile = ProfileFactory(user=user_gql_client.user)

    # Let's create a youth profile in the 2020
    with freeze_time("2020-05-02"):
        today = date.today()
        YouthProfileFactory(
            profile=profile,
            approved_time=datetime.today(),
            birth_date=today.replace(year=today.year - 18, day=today.day - 1),
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
            "renewMyYouthProfile": {"youthProfile": {"membershipStatus": "ACTIVE"}}
        }
        assert dict(executed["data"]) == expected_data


def test_staff_user_can_create_youth_profile(rf, user_gql_client, phone_data):
    service = ServiceFactory(service_type=ServiceType.YOUTH_MEMBERSHIP)
    group = GroupFactory()
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_manage_profiles", group, service)
    profile = ProfileFactory()
    request = rf.post("/graphql")
    request.user = user

    today = date.today()
    youth_profile_data = {
        "birth_date": today.replace(year=today.year - 13, day=today.day - 1).strftime(
            "%Y-%m-%d"
        ),
        "school_name": "Koulu",
        "school_class": "2B",
        "language_at_home": YouthLanguage.ENGLISH.name,
        "approver_first_name": "Jane",
        "approver_last_name": "Doe",
        "approver_phone": "040-1234567",
        "approver_email": "jane.doe@example.com",
    }

    t = Template(
        """
        mutation {
            createYouthProfile(
                input: {
                    serviceType: ${service_type},
                    profileId: \"${profile_id}\",
                    youthProfile: {
                        birthDate: \"${birth_date}\",
                        schoolName: \"${school_name}\",
                        schoolClass: \"${school_class}\",
                        languageAtHome: ${language_at_home},
                        approverEmail: \"${approver_email}\",
                        approverPhone: \"${approver_phone}\",
                        approverFirstName: \"${approver_first_name}\",
                        approverLastName: \"${approver_last_name}\",
                    }
                }
            ) {
                youthProfile {
                    birthDate
                    schoolName
                    schoolClass
                    languageAtHome
                    approverEmail
                    approverPhone
                    approverFirstName
                    approverLastName
                }
            }
        }
    """
    )
    query = t.substitute(
        service_type=ServiceType.YOUTH_MEMBERSHIP.name,
        profile_id=to_global_id(type="ProfileNode", id=profile.pk),
        birth_date=youth_profile_data["birth_date"],
        school_name=youth_profile_data["school_name"],
        school_class=youth_profile_data["school_class"],
        language_at_home=youth_profile_data["language_at_home"],
        approver_email=youth_profile_data["approver_email"],
        approver_phone=youth_profile_data["approver_phone"],
        approver_first_name=youth_profile_data["approver_first_name"],
        approver_last_name=youth_profile_data["approver_last_name"],
    )
    expected_data = {
        "createYouthProfile": {
            "youthProfile": {
                "birthDate": youth_profile_data["birth_date"],
                "schoolName": youth_profile_data["school_name"],
                "schoolClass": youth_profile_data["school_class"],
                "languageAtHome": youth_profile_data["language_at_home"],
                "approverEmail": youth_profile_data["approver_email"],
                "approverPhone": youth_profile_data["approver_phone"],
                "approverFirstName": youth_profile_data["approver_first_name"],
                "approverLastName": youth_profile_data["approver_last_name"],
            }
        }
    }
    executed = user_gql_client.execute(query, context=request)
    assert executed["data"] == expected_data


def test_staff_user_can_create_youth_profile_for_under_13_years_old(
    rf, user_gql_client, phone_data
):
    service = ServiceFactory(service_type=ServiceType.YOUTH_MEMBERSHIP)
    group = GroupFactory()
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_manage_profiles", group, service)
    profile = ProfileFactory()
    request = rf.post("/graphql")
    request.user = user

    today = date.today()
    youth_profile_data = {
        "birth_date": today.replace(year=today.year - 13, day=today.day + 1).strftime(
            "%Y-%m-%d"
        ),
        "approver_email": "jane.doe@example.com",
    }

    t = Template(
        """
        mutation {
            createYouthProfile(
                input: {
                    serviceType: ${service_type},
                    profileId: \"${profile_id}\",
                    youthProfile: {
                        birthDate: \"${birth_date}\",
                        approverEmail: \"${approver_email}\",
                    }
                }
            ) {
                youthProfile {
                    birthDate
                    approverEmail
                }
            }
        }
    """
    )
    query = t.substitute(
        service_type=ServiceType.YOUTH_MEMBERSHIP.name,
        profile_id=to_global_id(type="ProfileNode", id=profile.pk),
        birth_date=youth_profile_data["birth_date"],
        approver_email=youth_profile_data["approver_email"],
    )
    expected_data = {
        "createYouthProfile": {
            "youthProfile": {
                "birthDate": youth_profile_data["birth_date"],
                "approverEmail": youth_profile_data["approver_email"],
            }
        }
    }
    executed = user_gql_client.execute(query, context=request)
    assert executed["data"] == expected_data


def test_staff_user_can_create_youth_profile_via_create_profile(rf, user_gql_client):
    service = ServiceFactory(service_type=ServiceType.YOUTH_MEMBERSHIP)
    group = GroupFactory()
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_manage_profiles", group, service)
    request = rf.post("/graphql")
    request.user = user

    today = date.today()
    birth_date = today.replace(year=today.year - 13, day=today.day - 1).strftime(
        "%Y-%m-%d"
    )

    t = Template(
        """
        mutation {
            createProfile(
                input: {
                    serviceType: ${service_type},
                    profile: {
                        firstName: \"${first_name}\",
                        lastName: \"${last_name}\",
                        youthProfile: {
                            birthDate: \"${birth_date}\",
                            approverEmail: \"${approver_email}\",
                        }
                    }
                }
            ) {
                profile {
                    firstName
                    lastName
                    youthProfile {
                        birthDate
                        approverEmail
                    }
                    serviceConnections {
                        edges {
                            node {
                                service {
                                    type
                                }
                            }
                        }
                    }
                }
            }
        }
    """
    )
    query = t.substitute(
        service_type=ServiceType.YOUTH_MEMBERSHIP.name,
        first_name="John",
        last_name="Doe",
        birth_date=birth_date,
        approver_email="jane.doe@example.com",
    )
    expected_data = {
        "createProfile": {
            "profile": {
                "firstName": "John",
                "lastName": "Doe",
                "youthProfile": {
                    "birthDate": birth_date,
                    "approverEmail": "jane.doe@example.com",
                },
                "serviceConnections": {
                    "edges": [
                        {
                            "node": {
                                "service": {"type": ServiceType.YOUTH_MEMBERSHIP.name}
                            }
                        }
                    ]
                },
            }
        }
    }
    executed = user_gql_client.execute(query, context=request)
    assert executed["data"] == expected_data


def test_staff_user_cannot_create_youth_profile_with_invalid_service_type(
    rf, user_gql_client
):
    service_youth = ServiceFactory(service_type=ServiceType.YOUTH_MEMBERSHIP)
    service_berth = ServiceFactory(service_type=ServiceType.BERTH)
    group_youth = GroupFactory(name="Youth")
    group_berth = GroupFactory(name="Berth")
    user = user_gql_client.user
    user.groups.add(group_youth)
    user.groups.add(group_berth)
    assign_perm("can_manage_profiles", group_youth, service_youth)
    assign_perm("can_manage_profiles", group_berth, service_berth)
    profile = ProfileFactory()
    request = rf.post("/graphql")
    request.user = user

    today = date.today()
    youth_profile_data = {
        "birth_date": today.replace(year=today.year - 13, day=today.day - 1).strftime(
            "%Y-%m-%d"
        ),
        "approver_email": "jane.doe@example.com",
    }

    t = Template(
        """
        mutation {
            createYouthProfile(
                input: {
                    serviceType: ${service_type},
                    profileId: \"${profile_id}\",
                    youthProfile: {
                        birthDate: \"${birth_date}\",
                        approverEmail: \"${approver_email}\",
                    }
                }
            ) {
                youthProfile {
                    birthDate
                    approverEmail
                }
            }
        }
    """
    )
    query = t.substitute(
        service_type=ServiceType.BERTH.name,
        profile_id=to_global_id(type="ProfileNode", id=profile.pk),
        birth_date=youth_profile_data["birth_date"],
        approver_email=youth_profile_data["approver_email"],
    )
    executed = user_gql_client.execute(query, context=request)
    assert (
        executed["errors"][0].get("extensions").get("code")
        == CANNOT_PERFORM_THIS_ACTION_WITH_GIVEN_SERVICE_TYPE_ERROR
    )


def test_normal_user_cannot_use_create_youth_profile_mutation(rf, user_gql_client):
    ServiceFactory(service_type=ServiceType.YOUTH_MEMBERSHIP)
    user = user_gql_client.user
    profile = ProfileFactory()
    request = rf.post("/graphql")
    request.user = user

    today = date.today()
    youth_profile_data = {
        "birth_date": today.replace(year=today.year - 13, day=today.day - 1).strftime(
            "%Y-%m-%d"
        ),
        "approver_email": "jane.doe@example.com",
    }

    t = Template(
        """
        mutation {
            createYouthProfile(
                input: {
                    serviceType: ${service_type},
                    profileId: \"${profile_id}\",
                    youthProfile: {
                        birthDate: \"${birth_date}\",
                        approverEmail: \"${approver_email}\",
                    }
                }
            ) {
                youthProfile {
                    birthDate
                    approverEmail
                }
            }
        }
    """
    )
    query = t.substitute(
        service_type=ServiceType.YOUTH_MEMBERSHIP.name,
        profile_id=to_global_id(type="ProfileNode", id=profile.pk),
        birth_date=youth_profile_data["birth_date"],
        approver_email=youth_profile_data["approver_email"],
    )
    executed = user_gql_client.execute(query, context=request)
    assert (
        executed["errors"][0].get("extensions").get("code") == PERMISSION_DENIED_ERROR
    )


def test_nested_youth_profile_create_failure_also_fails_profile_creation(
    rf, user_gql_client
):
    service = ServiceFactory(service_type=ServiceType.YOUTH_MEMBERSHIP)
    group = GroupFactory()
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_manage_profiles", group, service)
    request = rf.post("/graphql")
    request.user = user

    t = Template(
        """
        mutation {
            createProfile(
                input: {
                    serviceType: ${service_type},
                    profile: {
                        firstName: \"${first_name}\",
                        lastName: \"${last_name}\",
                        youthProfile: {
                            approverEmail: \"${approver_email}\",
                        }
                    }
                }
            ) {
                profile {
                    firstName
                    youthProfile {
                        birthDate
                    }
                }
            }
        }
    """
    )
    query = t.substitute(
        service_type=ServiceType.YOUTH_MEMBERSHIP.name,
        first_name="John",
        last_name="Doe",
        approver_email="jane.doe@example.com",
    )

    assert Profile.objects.count() == 0
    user_gql_client.execute(query, context=request)
    # Nested CreateYouthProfile mutation failed and CreateProfile should also fail
    assert Profile.objects.count() == 0


def test_staff_user_can_cancel_youth_membership_on_selected_date(rf, user_gql_client):
    profile = ProfileFactory()
    YouthProfileFactory(profile=profile)
    service = ServiceFactory(service_type=ServiceType.YOUTH_MEMBERSHIP)
    group = GroupFactory()
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_manage_profiles", group, service)
    request = rf.post("/graphql")
    request.user = user

    today = date.today()
    youth_profile_data = {
        "profile_id": to_global_id(type="ProfileNode", id=profile.pk),
        "expiration": today.replace(year=today.year, day=today.day + 1).strftime(
            "%Y-%m-%d"
        ),
    }

    t = Template(
        """
        mutation {
            cancelYouthProfile(
                input: {
                    serviceType: ${service_type},
                    profileId: \"${profile_id}\",
                    expiration: \"${expiration}\"
                }
            ) {
                youthProfile {
                    expiration
                }
            }
        }
    """
    )
    query = t.substitute(
        service_type=ServiceType.YOUTH_MEMBERSHIP.name,
        profile_id=youth_profile_data["profile_id"],
        expiration=youth_profile_data["expiration"],
    )
    expected_data = {
        "cancelYouthProfile": {
            "youthProfile": {"expiration": youth_profile_data["expiration"]}
        }
    }
    executed = user_gql_client.execute(query, context=request)
    assert executed["data"] == expected_data


def test_staff_user_can_cancel_youth_membership_now(rf, user_gql_client):
    profile = ProfileFactory()
    YouthProfileFactory(profile=profile)
    service = ServiceFactory(service_type=ServiceType.YOUTH_MEMBERSHIP)
    group = GroupFactory()
    user = user_gql_client.user
    user.groups.add(group)
    assign_perm("can_manage_profiles", group, service)
    request = rf.post("/graphql")
    request.user = user

    youth_profile_data = {"profile_id": to_global_id(type="ProfileNode", id=profile.pk)}

    t = Template(
        """
        mutation {
            cancelYouthProfile(
                input: {
                    serviceType: ${service_type},
                    profileId: \"${profile_id}\",
                }
            ) {
                youthProfile {
                    expiration
                }
            }
        }
    """
    )
    query = t.substitute(
        service_type=ServiceType.YOUTH_MEMBERSHIP.name,
        profile_id=youth_profile_data["profile_id"],
    )
    expected_data = {
        "cancelYouthProfile": {
            "youthProfile": {"expiration": date.today().strftime("%Y-%m-%d")}
        }
    }
    executed = user_gql_client.execute(query, context=request)
    assert executed["data"] == expected_data


def test_normal_user_can_cancel_youth_membership(rf, user_gql_client):
    request = rf.post("/graphql")
    request.user = user_gql_client.user
    profile = ProfileFactory(user=user_gql_client.user)
    YouthProfileFactory(profile=profile, approved_time=datetime.now())

    today = date.today()
    expiration = today.replace(year=today.year, day=today.day + 1).strftime("%Y-%m-%d")

    t = Template(
        """
        mutation{
            cancelMyYouthProfile(
                input: {
                    expiration: \"${expiration}\"
                }
            )
            {
                youthProfile {
                    expiration
                    membershipStatus
                }
            }
        }
        """
    )
    query = t.substitute(expiration=expiration)

    expected_data = {
        "youthProfile": {"expiration": expiration, "membershipStatus": "EXPIRED"}
    }
    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]["cancelMyYouthProfile"]) == expected_data


def test_normal_user_can_cancel_youth_membership_now(rf, user_gql_client):
    request = rf.post("/graphql")
    request.user = user_gql_client.user
    profile = ProfileFactory(user=user_gql_client.user)
    YouthProfileFactory(profile=profile, approved_time=datetime.now())

    query = """
        mutation{
            cancelMyYouthProfile(
                input: {}
            )
            {
                youthProfile {
                    expiration
                    membershipStatus
                }
            }
        }
    """
    expected_data = {
        "youthProfile": {
            "expiration": date.today().strftime("%Y-%m-%d"),
            "membershipStatus": "EXPIRED",
        }
    }

    executed = user_gql_client.execute(query, context=request)
    assert dict(executed["data"]["cancelMyYouthProfile"]) == expected_data
