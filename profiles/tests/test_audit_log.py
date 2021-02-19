import json
import logging
from datetime import datetime, timedelta, timezone

import pytest
from django.conf import settings

from open_city_profile.tests.asserts import assert_almost_equal
from open_city_profile.tests.conftest import get_unix_timestamp_now
from open_city_profile.tests.graphql_test_helpers import do_graphql_call_as_user
from profiles.models import Profile

from .factories import ProfileFactory


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


def assert_common_fields(log_message, target_profile, operation, actor_role="SYSTEM"):
    now = get_unix_timestamp_now()
    audit_event = log_message["audit_event"]

    assert audit_event["origin"] == "PROFILE-BE"
    assert audit_event["status"] == "SUCCESS"
    assert audit_event["operation"] == operation
    assert audit_event["actor"]["role"] == actor_role

    assert_almost_equal(audit_event["date_time_epoch"], now)

    now_dt = datetime.fromtimestamp(now, tz=timezone.utc)
    log_dt = datetime.strptime(
        audit_event["date_time"], "%Y-%m-%dT%H:%M:%S.%fZ"
    ).replace(tzinfo=timezone.utc)
    assert_almost_equal(log_dt, now_dt, timedelta(seconds=1))

    expected_target = {
        "profile_id": str(target_profile.pk),
        "profile_part": "base profile",
        "user_id": str(target_profile.user.uuid),
    }
    if settings.AUDIT_LOG_USERNAME:
        expected_target["user_name"] = target_profile.user.username
    assert audit_event["target"] == expected_target


def test_audit_log_read(cap_audit_log):
    ProfileFactory()

    cap_audit_log.clear()
    profile = Profile.objects.first()
    audit_logs = cap_audit_log.get_logs()
    assert len(audit_logs) == 1
    log_message = audit_logs[0]
    assert_common_fields(log_message, profile, "READ")


def test_audit_log_update(profile, cap_audit_log):
    profile.first_name = "John"
    profile.save()
    audit_logs = cap_audit_log.get_logs()
    assert len(audit_logs) == 1
    log_message = audit_logs[0]
    assert_common_fields(log_message, profile, "UPDATE")


def test_audit_log_delete(profile, cap_audit_log):
    deleted_pk = profile.pk
    profile.delete()
    profile.pk = deleted_pk
    audit_logs = cap_audit_log.get_logs()
    assert len(audit_logs) == 1
    log_message = audit_logs[0]
    assert_common_fields(log_message, profile, "DELETE")


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

    do_graphql_call_as_user(live_server, user, MY_PROFILE_QUERY)
    audit_logs = cap_audit_log.get_logs()
    assert len(audit_logs) == 1
    log_message = audit_logs[0]
    assert_common_fields(log_message, profile, "READ", actor_role="OWNER")
    assert log_message["audit_event"]["actor"]["user_id"] == str(user.uuid)
    assert log_message["audit_event"]["actor"]["user_name"] == user.username


class TestIPAddressLogging:
    @staticmethod
    def execute_ip_address_test(
        live_server, profile, expected_ip, cap_audit_log, request_args=dict()
    ):
        user = profile.user

        do_graphql_call_as_user(
            live_server, user, MY_PROFILE_QUERY, extra_request_args=request_args
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
