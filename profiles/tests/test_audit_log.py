import json
import logging
from datetime import datetime, timedelta, timezone

import pytest
from django.conf import settings
from guardian.shortcuts import assign_perm

from open_city_profile.tests.asserts import assert_almost_equal
from open_city_profile.tests.graphql_test_helpers import do_graphql_call_as_user
from profiles.models import Profile
from services.tests.factories import ServiceConnectionFactory

from .factories import ProfileFactory, SensitiveDataFactory


@pytest.fixture(autouse=True)
def enable_audit_log():
    settings.AUDIT_LOGGING_ENABLED = True


@pytest.fixture()
def enable_audit_log_username():
    settings.AUDIT_LOG_USERNAME = True


@pytest.fixture
def cap_audit_log(caplog):
    def get_logs(self):
        audit_records = [
            r for r in self.records if r.name == "audit" and r.levelno == logging.INFO
        ]
        return [json.loads(r.getMessage()) for r in audit_records]

    caplog.get_logs = get_logs.__get__(caplog)
    return caplog


def assert_common_fields(
    log_message,
    target_profile,
    operation,
    actor_role="SYSTEM",
    target_profile_part="base profile",
):
    now_dt = datetime.now(tz=timezone.utc)
    now_ms_timestamp = int(now_dt.timestamp() * 1000)
    leeway_ms = 20

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
        "profile_id": str(target_profile.pk),
        "profile_part": target_profile_part,
        "user_id": str(target_profile.user.uuid),
    }
    if settings.AUDIT_LOG_USERNAME:
        expected_target["user_name"] = target_profile.user.username
    assert audit_event["target"] == expected_target


@pytest.fixture(
    params=[
        (ProfileFactory, (None, None)),
        (SensitiveDataFactory, ("sensitivedata", "sensitive data")),
    ]
)
def profile_with_related(request):
    factory, related_info = request.param
    created = factory()
    if related_info[0]:
        profile = getattr(created, "profile")
        related_part = created
    else:
        profile = created
        related_part = None
    return profile, related_part, related_info


def test_audit_log_read(profile_with_related, cap_audit_log):
    _, _, (related_name, profile_part_name) = profile_with_related
    profile_from_db = Profile.objects.select_related(related_name).first()
    audit_logs = cap_audit_log.get_logs()
    assert len(audit_logs) == 1 + (2 if related_name else 0)

    assert_common_fields(audit_logs[0], profile_from_db, "READ")
    if profile_part_name:
        # Audit logging the Profile related object READ causes another READ
        # for the base Profile.
        # This is unnecessary, but it's a feature of the current implementation.
        assert_common_fields(audit_logs[1], profile_from_db, "READ")
        assert_common_fields(
            audit_logs[2],
            profile_from_db,
            "READ",
            target_profile_part=profile_part_name,
        )


def test_audit_log_update(profile_with_related, cap_audit_log):
    profile, related_part, (related_name, profile_part_name) = profile_with_related
    profile.first_name = "John"
    profile.save()
    if related_part:
        related_part.save()

    audit_logs = cap_audit_log.get_logs()
    assert len(audit_logs) == 1 + (1 if related_name else 0)

    assert_common_fields(audit_logs[0], profile, "UPDATE")
    if profile_part_name:
        assert_common_fields(
            audit_logs[1], profile, "UPDATE", target_profile_part=profile_part_name
        )


def test_audit_log_delete(profile_with_related, cap_audit_log):
    profile, related_part, (related_name, profile_part_name) = profile_with_related
    deleted_pk = profile.pk
    profile.delete()
    profile.pk = deleted_pk
    audit_logs = cap_audit_log.get_logs()
    # Audit logging the Profile DELETE with a related object causes some READs
    # for the involved models.
    # This is unnecessary, but it's a feature of the current implementation.
    # We ignore the READ events in this test for now.
    audit_logs = list(
        filter(lambda e: e["audit_event"]["operation"] != "READ", audit_logs)
    )
    assert len(audit_logs) == 1 + (1 if related_name else 0)

    if profile_part_name:
        assert_common_fields(
            audit_logs.pop(0), profile, "DELETE", target_profile_part=profile_part_name
        )
    assert_common_fields(audit_logs[0], profile, "DELETE")


def test_audit_log_create(enable_audit_log_username, cap_audit_log):
    profile = ProfileFactory()
    audit_logs = cap_audit_log.get_logs()
    assert (
        len(audit_logs) == 2
    )  # profile is accessed here as well, thus the 2 log entries
    log_message = audit_logs[1]
    assert_common_fields(log_message, profile, "CREATE")


MY_PROFILE_QUERY = """
    query {
        myProfile {
            id
        }
    }
"""


def test_actor_is_resolved_in_graphql_call(
    enable_audit_log_username, live_server, profile, cap_audit_log
):
    user = profile.user

    do_graphql_call_as_user(live_server, user, query=MY_PROFILE_QUERY)
    audit_logs = cap_audit_log.get_logs()
    assert len(audit_logs) == 1
    log_message = audit_logs[0]
    assert_common_fields(log_message, profile, "READ", actor_role="OWNER")
    assert log_message["audit_event"]["actor"]["user_id"] == str(user.uuid)
    assert log_message["audit_event"]["actor"]["user_name"] == user.username


def test_actor_service(live_server, user, group, service_client_id, cap_audit_log):
    profile = ProfileFactory()
    service = service_client_id.service
    ServiceConnectionFactory(profile=profile, service=service)
    user.groups.add(group)
    assign_perm("can_view_profiles", group, service)

    query = """
        {
            profiles {
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
    assert len(audit_logs) == 1
    log_message = audit_logs[0]
    assert_common_fields(log_message, profile, "READ", actor_role="ADMIN")
    actor_log = log_message["audit_event"]["actor"]
    assert actor_log["service_name"] == service.name


class TestIPAddressLogging:
    @staticmethod
    def execute_ip_address_test(
        live_server, profile, expected_ip, cap_audit_log, request_args=dict()
    ):
        user = profile.user

        do_graphql_call_as_user(
            live_server, user, query=MY_PROFILE_QUERY, extra_request_args=request_args
        )
        audit_logs = cap_audit_log.get_logs()
        assert len(audit_logs) == 1
        log_message = audit_logs[0]
        assert log_message["audit_event"]["profilebe"]["ip_address"] == expected_ip

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
