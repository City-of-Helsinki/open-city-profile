import json
import logging
from datetime import datetime, timedelta, timezone

import pytest
from django.conf import settings

from open_city_profile.tests.asserts import assert_almost_equal
from open_city_profile.tests.conftest import get_unix_timestamp_now
from open_city_profile.tests.graphql_test_helpers import do_graphql_call_as_user
from profiles.audit_log import flush_audit_log
from profiles.models import Profile

from .factories import ProfileFactory


@pytest.fixture()
def enable_audit_log():
    settings.AUDIT_LOGGING_ENABLED = True


@pytest.fixture()
def enable_audit_log_username():
    settings.AUDIT_LOG_USERNAME = True


@pytest.fixture
def cap_audit_log(caplog):
    flush_audit_log()
    caplog.clear()

    def get_logs(self):
        flush_audit_log()

        audit_records = [
            r for r in self.records if r.name == "audit" and r.levelno == logging.INFO
        ]
        return [json.loads(r.getMessage()) for r in audit_records]

    caplog.get_logs = get_logs.__get__(caplog)
    return caplog


def assert_common_fields(log_message, actor_role="SYSTEM"):
    assert log_message["audit_event"]["origin"] == "PROFILE-BE"
    assert log_message["audit_event"]["status"] == "SUCCESS"
    assert log_message["audit_event"]["actor"]["role"] == actor_role
    now = get_unix_timestamp_now()
    assert_almost_equal(log_message["audit_event"]["date_time_epoch"], now)

    now_dt = datetime.fromtimestamp(now, tz=timezone.utc)
    log_dt = datetime.strptime(
        log_message["audit_event"]["date_time"], "%Y-%m-%dT%H:%M:%S.%fZ"
    ).replace(tzinfo=timezone.utc)
    assert_almost_equal(log_dt, now_dt, timedelta(seconds=1))


def test_audit_log_read(user, enable_audit_log, profile, cap_audit_log):
    profile_from_db = Profile.objects.first()
    audit_logs = cap_audit_log.get_logs()
    assert len(audit_logs) == 1
    log_message = audit_logs[0]
    assert_common_fields(log_message)
    assert log_message["audit_event"]["operation"] == "READ"
    assert log_message["audit_event"]["target"] == {
        "user_id": str(profile_from_db.user.uuid),
        "profile_id": str(profile_from_db.pk),
        "profile_part": "base profile",
    }


def test_audit_log_update(user, enable_audit_log, profile, cap_audit_log):
    profile.first_name = "John"
    profile.save()
    audit_logs = cap_audit_log.get_logs()
    assert len(audit_logs) == 1
    log_message = audit_logs[0]
    assert_common_fields(log_message)
    assert log_message["audit_event"]["operation"] == "UPDATE"
    assert log_message["audit_event"]["target"] == {
        "user_id": str(profile.user.uuid),
        "profile_id": str(profile.pk),
        "profile_part": "base profile",
    }


def test_audit_log_delete(user, enable_audit_log, profile, cap_audit_log):
    profile.delete()
    audit_logs = cap_audit_log.get_logs()
    assert len(audit_logs) == 1
    log_message = audit_logs[0]
    assert_common_fields(log_message)
    assert log_message["audit_event"]["operation"] == "DELETE"


def test_audit_log_create(
    user, enable_audit_log, enable_audit_log_username, cap_audit_log
):
    profile = ProfileFactory()
    audit_logs = cap_audit_log.get_logs()
    assert (
        len(audit_logs) == 2
    )  # profile is accessed here as well, thus the 2 log entries
    log_message = audit_logs[1]
    assert_common_fields(log_message)
    assert log_message["audit_event"]["operation"] == "CREATE"
    assert log_message["audit_event"]["target"] == {
        "user_id": str(profile.user.uuid),
        "user_name": profile.user.username,
        "profile_id": str(profile.pk),
        "profile_part": "base profile",
    }


MY_PROFILE_QUERY = """
    query {
        myProfile {
            id
        }
    }
"""


def test_actor_is_resolved_in_graphql_call(
    enable_audit_log, enable_audit_log_username, live_server, profile, cap_audit_log
):
    user = profile.user

    do_graphql_call_as_user(live_server, user, MY_PROFILE_QUERY)
    audit_logs = cap_audit_log.get_logs()
    assert len(audit_logs) == 1
    log_message = audit_logs[0]
    assert_common_fields(log_message, actor_role="OWNER")
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
        self, header, enable_audit_log, live_server, profile, cap_audit_log
    ):
        request_args = {"headers": {"X-Forwarded-For": header}}
        self.execute_ip_address_test(
            live_server, profile, "12.23.34.45", cap_audit_log, request_args
        )

    def test_do_not_use_x_forwarded_for_header_if_it_is_denied_in_settings(
        self, enable_audit_log, live_server, settings, profile, cap_audit_log
    ):
        settings.USE_X_FORWARDED_FOR = False
        request_args = {"headers": {"X-Forwarded-For": "should ignore"}}

        self.execute_ip_address_test(
            live_server, profile, "127.0.0.1", cap_audit_log, request_args
        )

    def test_requester_ip_address_is_extracted_from_remote_addr_meta(
        self, enable_audit_log, live_server, profile, cap_audit_log
    ):
        self.execute_ip_address_test(live_server, profile, "127.0.0.1", cap_audit_log)