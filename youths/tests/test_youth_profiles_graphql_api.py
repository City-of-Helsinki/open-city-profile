from string import Template

from youths.tests.factories import ProfileFactory, YouthProfileFactory


def test_anon_user_query_should_fail(rf, youth_profile, anon_user_gql_client):
    request = rf.post("/graphql")
    request.user = anon_user_gql_client.user

    query = """
        {
            youthProfile(profileId: 1) {
                ssn
                gender
                schoolClass
            }
        }
    """
    expected_data = {"youthProfile": None}
    executed = anon_user_gql_client.execute(query, context_value=request)
    assert dict(executed["data"]) == expected_data


def test_normal_user_query_by_id_should_fail(rf, youth_profile, user_gql_client):
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    query = """
        {
            youthProfile(profileId: 666) {
                ssn
                gender
                schoolClass
            }
        }
    """
    expected_data = {"youthProfile": None}
    executed = user_gql_client.execute(query, context_value=request)
    assert dict(executed["data"]) == expected_data


def test_normal_user_can_query_own_youth_profile(rf, user_gql_client):
    request = rf.post("/graphql")
    request.user = user_gql_client.user
    profile = ProfileFactory(user=user_gql_client.user)
    youth_profile = YouthProfileFactory(profile=profile)

    query = """
        {
            youthProfile {
                ssn
                gender
                schoolClass
            }
        }
    """
    expected_data = {
        "youthProfile": {
            "ssn": youth_profile.ssn,
            "gender": youth_profile.gender,
            "schoolClass": youth_profile.school_class,
        }
    }
    executed = user_gql_client.execute(query, context_value=request)
    assert dict(executed["data"]) == expected_data


def test_superuser_can_query_by_id(rf, youth_profile, superuser_gql_client):
    request = rf.post("/graphql")
    request.user = superuser_gql_client.user

    t = Template(
        """
        {
            youthProfile(profileId: ${profileId}) {
                ssn
                gender
                schoolClass
            }
        }
        """
    )
    query = t.substitute(profileId=youth_profile.profile.pk)
    expected_data = {
        "youthProfile": {
            "ssn": youth_profile.ssn,
            "gender": youth_profile.gender,
            "schoolClass": youth_profile.school_class,
        }
    }
    executed = superuser_gql_client.execute(query, context_value=request)
    assert dict(executed["data"]) == expected_data


def test_normal_user_can_create_youth_profile_mutation(rf, user_gql_client):
    request = rf.post("/graphql")
    request.user = user_gql_client.user
    profile = ProfileFactory(user=user_gql_client.user)

    t = Template(
        """
        mutation{
            createYouthProfile(
                profileId: ${profileId}
                youthProfileData: {
                    ssn: "${ssn}"
                    schoolClass: "${schoolClass}"
                    schoolName: "${schoolName}"
                    diabetes: true
                    preferredLanguage: ${language}
                    approverEmail: "${approverEmail}"
                }
            )
            {
                youthProfile {
                    ssn
                    diabetes
                    schoolClass
                    schoolName
                    approverEmail
                }
            }
        }
        """
    )
    creation_data = {
        "profileId": profile.pk,
        "ssn": "101010ASDF",
        "schoolClass": "2A",
        "schoolName": "Alakoulu",
        "approverEmail": "hyvaksyja@ex.com",
        "language": "FINNISH",
    }
    query = t.substitute(**creation_data)
    expected_data = {
        "youthProfile": {
            "ssn": creation_data["ssn"],
            "diabetes": True,
            "schoolClass": creation_data["schoolClass"],
            "schoolName": creation_data["schoolName"],
            "approverEmail": creation_data["approverEmail"],
        }
    }
    executed = user_gql_client.execute(query, context_value=request)
    assert dict(executed["data"]["createYouthProfile"]) == expected_data


def test_normal_user_can_update_youth_profile_mutation(rf, user_gql_client):
    request = rf.post("/graphql")
    request.user = user_gql_client.user

    profile = ProfileFactory(user=user_gql_client.user)
    youth_profile = YouthProfileFactory(profile=profile)

    t = Template(
        """
        mutation{
            updateYouthProfile(
                youthProfileData: {
                    schoolClass: "${schoolClass}"
                    diabetes: true
                    gender: MALE
                }
            )
            {
                youthProfile {
                    ssn
                    diabetes
                    gender
                    schoolClass
                    schoolName
                    approverEmail
                }
            }
        }
        """
    )
    creation_data = {"schoolClass": "2A"}
    query = t.substitute(**creation_data)
    expected_data = {
        "youthProfile": {
            "ssn": youth_profile.ssn,
            "diabetes": True,
            "gender": "male",
            "schoolClass": creation_data["schoolClass"],
            "schoolName": youth_profile.school_name,
            "approverEmail": youth_profile.approver_email,
        }
    }
    executed = user_gql_client.execute(query, context_value=request)
    assert dict(executed["data"]["updateYouthProfile"]) == expected_data


def test_superuser_can_create_youth_profile_mutation(rf, superuser_gql_client, user):
    request = rf.post("/graphql")
    request.user = superuser_gql_client.user
    profile = ProfileFactory(user=user)

    t = Template(
        """
        mutation{
            createYouthProfile(
                profileId: ${profileId}
                youthProfileData: {
                    ssn: "${ssn}"
                    schoolClass: "${schoolClass}"
                    schoolName: "${schoolName}"
                    diabetes: true
                    preferredLanguage: ${language}
                    approverEmail: "${approverEmail}"
                }
            )
            {
                youthProfile {
                    ssn
                    diabetes
                    schoolClass
                    schoolName
                    approverEmail
                }
            }
        }
        """
    )
    creation_data = {
        "profileId": profile.pk,
        "ssn": "101010ASDF",
        "schoolClass": "2A",
        "schoolName": "Alakoulu",
        "approverEmail": "hyvaksyja@ex.com",
        "language": "FINNISH",
    }
    query = t.substitute(**creation_data)
    expected_data = {
        "youthProfile": {
            "ssn": creation_data["ssn"],
            "diabetes": True,
            "schoolClass": creation_data["schoolClass"],
            "schoolName": creation_data["schoolName"],
            "approverEmail": creation_data["approverEmail"],
        }
    }
    executed = superuser_gql_client.execute(query, context_value=request)
    assert dict(executed["data"]["createYouthProfile"]) == expected_data


def test_superuser_can_update_youth_profile_mutation(
    rf, youth_profile, superuser_gql_client
):
    request = rf.post("/graphql")
    request.user = superuser_gql_client.user

    t = Template(
        """
        mutation{
            updateYouthProfile(
                profileId: ${profileId}
                youthProfileData: {
                    schoolClass: "${schoolClass}"
                    diabetes: true
                    gender: MALE
                }
            )
            {
                youthProfile {
                    ssn
                    diabetes
                    gender
                    schoolClass
                    schoolName
                    approverEmail
                }
            }
        }
        """
    )
    creation_data = {"schoolClass": "2A", "profileId": youth_profile.profile.pk}
    query = t.substitute(**creation_data)
    expected_data = {
        "youthProfile": {
            "ssn": youth_profile.ssn,
            "diabetes": True,
            "gender": "male",
            "schoolClass": creation_data["schoolClass"],
            "schoolName": youth_profile.school_name,
            "approverEmail": youth_profile.approver_email,
        }
    }
    executed = superuser_gql_client.execute(query, context_value=request)
    assert dict(executed["data"]["updateYouthProfile"]) == expected_data


def test_anon_user_query_with_token(rf, youth_profile, anon_user_gql_client):
    request = rf.post("/graphql")
    request.user = anon_user_gql_client.user

    t = Template(
        """
        {
            youthProfileByApprovalToken(token: "${approvalToken}") {
                ssn
                gender
                schoolClass
            }
        }
        """
    )
    query = t.substitute(approvalToken=youth_profile.approval_token)
    expected_data = {
        "youthProfileByApprovalToken": {
            "ssn": youth_profile.ssn,
            "gender": youth_profile.gender,
            "schoolClass": youth_profile.school_class,
        }
    }
    executed = anon_user_gql_client.execute(query, context_value=request)
    assert dict(executed["data"]) == expected_data


def test_anon_user_can_approve_with_token(rf, youth_profile, anon_user_gql_client):
    request = rf.post("/graphql")
    request.user = anon_user_gql_client.user

    t = Template(
        """
        mutation{
            approveYouthProfile(
                approvalToken: "${token}",
                approvalData: {
                    diabetes: false
                    epilepsy: true
                    photoUsageApproved: true
                    allergies: "${allergies}"
                }
            )
            {
                youthProfile {
                    ssn
                    diabetes
                    epilepsy
                    photoUsageApproved
                    allergies
                }
            }
        }
        """
    )
    approval_data = {
        "token": youth_profile.approval_token,
        "allergies": "Horse, apples",
    }
    query = t.substitute(**approval_data)
    expected_data = {
        "youthProfile": {
            "ssn": youth_profile.ssn,
            "diabetes": False,
            "epilepsy": True,
            "photoUsageApproved": True,
            "allergies": approval_data["allergies"],
        }
    }
    executed = anon_user_gql_client.execute(query, context_value=request)
    assert dict(executed["data"]["approveYouthProfile"]) == expected_data
