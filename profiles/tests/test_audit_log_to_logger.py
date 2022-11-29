import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from string import Template
from typing import Any, List, Optional

import pytest
from graphql_relay import to_global_id
from guardian.shortcuts import assign_perm

from open_city_profile.tests import to_graphql_name
from open_city_profile.tests.asserts import assert_almost_equal
from open_city_profile.tests.graphql_test_helpers import (
    do_graphql_call,
    do_graphql_call_as_user,
)
from profiles.models import (
    Profile,
    VerifiedPersonalInformationPermanentAddress,
    VerifiedPersonalInformationPermanentForeignAddress,
    VerifiedPersonalInformationTemporaryAddress,
)
from services.tests.factories import ServiceConnectionFactory

from .factories import (
    AddressFactory,
    EmailFactory,
    PhoneFactory,
    ProfileFactory,
    SensitiveDataFactory,
    TemporaryReadAccessTokenFactory,
    VerifiedPersonalInformationFactory,
)


@pytest.fixture(autouse=True)
def enable_audit_log(settings):
    settings.AUDIT_LOG_TO_LOGGER_ENABLED = True


@pytest.fixture
def cap_audit_log(caplog):
    def get_logs(self):
        audit_records = [
            r for r in self.records if r.name == "audit" and r.levelno == logging.INFO
        ]
        return [json.loads(r.getMessage()) for r in audit_records]

    caplog.get_logs = get_logs.__get__(caplog)
    return caplog


def partition_logs_by_target_type(logs, target_type):
    matches = []
    rest = []

    for log in logs:
        if log["audit_event"]["target"]["type"] == target_type:
            matches.append(log)
        else:
            rest.append(log)

    return matches, rest


def discard_audit_logs(audit_logs, operation):
    return list(
        filter(lambda e: e["audit_event"]["operation"] != operation, audit_logs)
    )


def assert_common_fields(
    log_message,
    target_profile,
    operation,
    actor_role="SYSTEM",
    target_profile_part="base profile",
):
    now_dt = datetime.now(tz=timezone.utc)
    now_ms_timestamp = int(now_dt.timestamp() * 1000)
    leeway_ms = 200

    if isinstance(log_message, list):
        assert len(log_message) == 1
        log_message = log_message[0]

    audit_event = log_message["audit_event"]

    assert audit_event["origin"] == "PROFILE-BE"
    assert audit_event["status"] == "SUCCESS"
    assert audit_event["operation"] == operation
    assert audit_event["actor"]["role"] == actor_role

    assert_almost_equal(audit_event["date_time_epoch"], now_ms_timestamp, leeway_ms)

    log_dt = datetime.strptime(
        audit_event["date_time"], "%Y-%m-%dT%H:%M:%S.%fZ"
    ).replace(tzinfo=timezone.utc)
    assert_almost_equal(log_dt, now_dt, timedelta(milliseconds=leeway_ms))

    expected_target = {
        "id": str(target_profile.pk),
        "type": target_profile_part,
        "user_id": str(target_profile.user.uuid),
    }
    assert audit_event["target"] == expected_target


@dataclass
class ProfileWithRelated:
    profile: Profile
    related_part: Optional[Any]
    related_name: Optional[str]
    profile_part_name: Optional[str]
    additional_profile_part_names: List[str]

    @property
    def all_profile_part_names(self):
        return [
            name
            for name in [self.profile_part_name] + self.additional_profile_part_names
            if name is not None
        ]


def vpi_factory_with_addresses(*wanted_address_models):
    def factory():
        address_args = dict()
        for address_model in [
            VerifiedPersonalInformationPermanentAddress,
            VerifiedPersonalInformationTemporaryAddress,
            VerifiedPersonalInformationPermanentForeignAddress,
        ]:
            if address_model not in wanted_address_models:
                address_args[address_model.RELATED_NAME] = None

        return VerifiedPersonalInformationFactory(**address_args)

    return factory


@pytest.fixture(
    params=[
        (ProfileFactory, None, None, []),
        (SensitiveDataFactory, "sensitivedata", "sensitive data", []),
        (
            vpi_factory_with_addresses(),
            "verified_personal_information",
            "verified personal information",
            [],
        ),
        (
            vpi_factory_with_addresses(VerifiedPersonalInformationPermanentAddress),
            "verified_personal_information__permanent_address",
            "verified personal information permanent address",
            ["verified personal information"],
        ),
        (
            vpi_factory_with_addresses(VerifiedPersonalInformationTemporaryAddress),
            "verified_personal_information__temporary_address",
            "verified personal information temporary address",
            ["verified personal information"],
        ),
        (
            vpi_factory_with_addresses(
                VerifiedPersonalInformationPermanentForeignAddress
            ),
            "verified_personal_information__permanent_foreign_address",
            "verified personal information permanent foreign address",
            ["verified personal information"],
        ),
        (PhoneFactory, "phones", "phone", [],),
        (EmailFactory, "emails", "email", [],),
        (AddressFactory, "addresses", "address", [],),
    ]
)
def profile_with_related(request):
    (
        factory,
        related_name,
        profile_part_name,
        additional_profile_part_names,
    ) = request.param
    created = factory()
    if related_name:
        profile = getattr(created, "profile")
        related_part = profile
        for field_name in related_name.split("__"):
            related_part = getattr(related_part, field_name)
    else:
        profile = created
        related_part = None

    return ProfileWithRelated(
        profile,
        related_part,
        related_name,
        profile_part_name,
        additional_profile_part_names,
    )


MY_PROFILE_QUERY = """
    query {
        myProfile {
            id
            sensitivedata {
                id
            }
            verifiedPersonalInformation {
                firstName
                permanentAddress {
                    streetAddress
                }
                temporaryAddress {
                    streetAddress
                }
                permanentForeignAddress {
                    streetAddress
                }
            }
            phones {
                edges {
                    node {
                        phone
                        phoneType
                        primary
                    }
                }
            }
            emails {
                edges {
                    node {
                        email
                        emailType
                        primary
                    }
                }
            }
            addresses {
                edges {
                    node {
                        address
                        primary
                    }
                }
            }
        }
    }
"""


def test_audit_log_read(live_server, profile_with_related, cap_audit_log):
    profile = profile_with_related.profile
    user = profile.user
    do_graphql_call_as_user(
        live_server, user, extra_claims={"loa": "substantial"}, query=MY_PROFILE_QUERY
    )

    audit_logs = cap_audit_log.get_logs()

    for profile_part_name in profile_with_related.all_profile_part_names:
        related_logs, audit_logs = partition_logs_by_target_type(
            audit_logs, profile_part_name
        )

        assert_common_fields(
            related_logs,
            profile,
            "READ",
            actor_role="OWNER",
            target_profile_part=profile_part_name,
        )

    assert_common_fields(audit_logs, profile, "READ", actor_role="OWNER")


def test_audit_log_update(live_server, profile_with_related, cap_audit_log):
    profile = profile_with_related.profile
    user = profile.user
    assign_perm("profiles.manage_verified_personal_information", user)

    related_name = profile_with_related.related_name

    if related_name == "sensitivedata":
        query = """
            mutation {
                updateMyProfile(input: {
                    profile: {
                        sensitivedata: {
                            ssn: "121256-7890"
                        }
                    }
                }) {
                    profile {
                        firstName
                    }
                }
            }
        """
    elif related_name == "phones":
        t = Template(
            """
            mutation {
                updateMyProfile(input: {
                    profile: {
                        updatePhones: [
                            {
                                id: "${phone_id}",
                                phone: "12345",
                                primary: true
                            }
                        ]
                    }
                }) {
                    profile {
                        firstName
                    }
                }
            }
            """
        )
        phone = profile.phones.first()
        query = t.substitute(phone_id=to_global_id("PhoneNode", phone.pk))
    elif related_name == "emails":
        t = Template(
            """
            mutation {
                updateMyProfile(input: {
                    profile: {
                        updateEmails: [
                            {
                                id: "${email_id}",
                                email: "example@example.com",
                                primary: true
                            }
                        ]
                    }
                }) {
                    profile {
                        firstName
                    }
                }
            }
            """
        )
        email = profile.emails.first()
        query = t.substitute(email_id=to_global_id("EmailNode", email.pk))
    elif related_name == "addresses":
        t = Template(
            """
            mutation {
                updateMyProfile(input: {
                    profile: {
                        updateAddresses: [
                            {
                                id: "${address_id}",
                                address: "example address",
                                primary: true
                            }
                        ]
                    }
                }) {
                    profile {
                        firstName
                    }
                }
            }
            """
        )
        address = profile.addresses.first()
        query = t.substitute(address_id=to_global_id("AddressNode", address.pk))
    else:
        if related_name and "verified" in related_name:
            if "address" in related_name:
                address_name = related_name.split("__")[1]
                vpi_content = (
                    to_graphql_name(address_name)
                    + ': { streetAddress: "New street address" }'
                )
            else:
                vpi_content = 'lastName: "Verified last name"'
            vpi_input = "verifiedPersonalInformation: {" + vpi_content + "}"
        else:
            vpi_input = ""

        t = Template(
            """
            mutation {
                createOrUpdateUserProfile(input: {
                    userId: "${user_id}"
                    profile: {
                        firstName: "New name"
                        ${vpi_input}
                    }
                }) {
                    profile {
                        firstName
                    }
                }
            }
        """
        )
        query = t.substitute(user_id=str(user.uuid), vpi_input=vpi_input)

    do_graphql_call_as_user(live_server, user, query=query)

    audit_logs = cap_audit_log.get_logs()
    # Audit logging the Profile UPDATE with a related object causes some READs
    # for the involved models.
    # This is unnecessary, but it's a feature of the current implementation.
    # We ignore the READ events in this test for now.
    audit_logs = discard_audit_logs(audit_logs, "READ")

    for profile_part_name in profile_with_related.all_profile_part_names:
        related_logs, audit_logs = partition_logs_by_target_type(
            audit_logs, profile_part_name
        )

        assert_common_fields(
            related_logs,
            profile,
            "UPDATE",
            actor_role="OWNER",
            target_profile_part=profile_part_name,
        )

    assert_common_fields(audit_logs, profile, "UPDATE", actor_role="OWNER")


def test_audit_log_delete(live_server, profile_with_related, cap_audit_log):
    profile = profile_with_related.profile
    user = profile.user

    query = """
        mutation {
            deleteMyProfile(input: {
                authorizationCode: ""
            }) {
                clientMutationId
            }
        }
    """
    do_graphql_call_as_user(live_server, user, query=query)

    audit_logs = cap_audit_log.get_logs()
    # Audit logging the Profile DELETE with a related object causes some READs
    # for the involved models.
    # This is unnecessary, but it's a feature of the current implementation.
    # We ignore the READ events in this test for now.
    audit_logs = discard_audit_logs(audit_logs, "READ")

    for profile_part_name in profile_with_related.all_profile_part_names:
        related_logs, audit_logs = partition_logs_by_target_type(
            audit_logs, profile_part_name
        )

        assert_common_fields(
            related_logs,
            profile,
            "DELETE",
            actor_role="OWNER",
            target_profile_part=profile_part_name,
        )

    assert_common_fields(audit_logs, profile, "DELETE", actor_role="OWNER")


def test_audit_log_create(live_server, user, cap_audit_log):
    query = """
        mutation {
            createMyProfile(input: {
                profile: {
                    firstName: "New profile"
                }
            }) {
                profile {
                    firstName
                }
            }
        }
    """
    do_graphql_call_as_user(live_server, user, query=query)

    audit_logs = cap_audit_log.get_logs()
    profile = Profile.objects.get()
    assert_common_fields(audit_logs, profile, "CREATE", actor_role="OWNER")


def test_actor_is_resolved_in_graphql_call(
    live_server, profile, service_client_id, cap_audit_log
):
    service = service_client_id.service
    ServiceConnectionFactory(profile=profile, service=service)
    user = profile.user
    do_graphql_call_as_user(live_server, user, service=service, query=MY_PROFILE_QUERY)
    audit_logs = cap_audit_log.get_logs()
    assert_common_fields(audit_logs, profile, "READ", actor_role="OWNER")
    log_message = audit_logs[0]
    assert log_message["audit_event"]["actor"]["user_id"] == str(user.uuid)


def test_system_user_actor_is_resolved_in_graphql_call(
    live_server, system_user, cap_audit_log
):
    assign_perm("profiles.manage_verified_personal_information", system_user)

    query = """
        mutation {
            createOrUpdateUserProfile(
                input: {
                    userId: "9940aaea-f0e0-11ea-9089-c2a5d7831f23"
                    profile: {
                        firstName: "Test"
                    }
                },
            ) {
                profile {
                    id
                }
            }
        }
    """

    do_graphql_call_as_user(live_server, system_user, service=None, query=query)

    audit_logs = cap_audit_log.get_logs()
    profile = Profile.objects.get()
    assert_common_fields(audit_logs, profile, "CREATE", actor_role="SYSTEM")


def test_anonymous_user_actor_is_resolved_in_graphql_call(
    live_server, profile, cap_audit_log
):
    token = TemporaryReadAccessTokenFactory(profile=profile)

    query = Template(
        """
        query {
            profileWithAccessToken(token: "${token}") {
                id
            }
        }
    """
    ).substitute(token=token.token)

    do_graphql_call(live_server, query=query)

    audit_logs = cap_audit_log.get_logs()
    assert_common_fields(audit_logs, profile, "READ", actor_role="ANONYMOUS")
    log_message = audit_logs[0]
    assert "user_id" not in log_message["audit_event"]["actor"]


def test_service_is_resolved_in_graphql_call(
    live_server, profile, service_client_id, cap_audit_log
):
    user = profile.user
    service = service_client_id.service
    ServiceConnectionFactory(profile=profile, service=service)
    do_graphql_call_as_user(live_server, user, service=service, query=MY_PROFILE_QUERY)
    audit_logs = cap_audit_log.get_logs()
    assert_common_fields(audit_logs, profile, "READ", actor_role="OWNER")
    log_message = audit_logs[0]
    actor_log = log_message["audit_event"]["actor"]
    assert "service_name" in actor_log
    assert actor_log["service_name"] == service.name
    assert "client_id" in actor_log
    assert actor_log["client_id"] == service_client_id.client_id


def test_actor_service(live_server, user, group, service_client_id, cap_audit_log):
    profile = ProfileFactory()
    service = service_client_id.service
    ServiceConnectionFactory(profile=profile, service=service)
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service)

    # serviceType is included in query just to ensure that it has NO affect on the audit log
    query = """
        {
            profiles(serviceType: GODCHILDREN_OF_CULTURE) {
                edges {
                    node {
                        firstName
                    }
                }
            }
        }
    """

    cap_audit_log.clear()

    do_graphql_call_as_user(live_server, user, service=service, query=query)

    audit_logs = cap_audit_log.get_logs()
    assert_common_fields(audit_logs, profile, "READ", actor_role="ADMIN")
    log_message = audit_logs[0]
    actor_log = log_message["audit_event"]["actor"]
    assert actor_log["service_name"] == service.name
    assert "client_id" in actor_log
    assert actor_log["client_id"] == service_client_id.client_id


class TestIPAddressLogging:
    @staticmethod
    def execute_ip_address_test(
        live_server, profile, expected_ip, cap_audit_log, request_args=None
    ):
        if request_args is None:
            request_args = {}

        user = profile.user

        do_graphql_call_as_user(
            live_server, user, query=MY_PROFILE_QUERY, extra_request_args=request_args
        )
        audit_logs = cap_audit_log.get_logs()
        assert len(audit_logs) == 1
        log_message = audit_logs[0]
        assert log_message["audit_event"]["actor"]["ip_address"] == expected_ip

    @pytest.mark.parametrize(
        "header", ["12.23.34.45", "12.23.34.45,1.1.1.1", "12.23.34.45, 1.1.1.1"]
    )
    def test_requester_ip_address_is_extracted_from_x_forwarded_for_header(
        self, header, live_server, profile, cap_audit_log
    ):
        request_args = {"headers": {"X-Forwarded-For": header}}
        self.execute_ip_address_test(
            live_server, profile, "12.23.34.45", cap_audit_log, request_args
        )

    def test_do_not_use_x_forwarded_for_header_if_it_is_denied_in_settings(
        self, live_server, settings, profile, cap_audit_log
    ):
        settings.USE_X_FORWARDED_FOR = False
        request_args = {"headers": {"X-Forwarded-For": "should ignore"}}

        self.execute_ip_address_test(
            live_server, profile, "127.0.0.1", cap_audit_log, request_args
        )

    def test_requester_ip_address_is_extracted_from_remote_addr_meta(
        self, live_server, profile, cap_audit_log
    ):
        self.execute_ip_address_test(live_server, profile, "127.0.0.1", cap_audit_log)
