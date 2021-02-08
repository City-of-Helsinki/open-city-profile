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


@pytest.fixture()
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


def test_audit_log_read(user, enable_audit_log, cap_audit_log):
    ProfileFactory()

    cap_audit_log.clear()
    profile = Profile.objects.first()
    audit_logs = cap_audit_log.get_logs()
    assert len(audit_logs) == 1
    log_message = audit_logs[0]
    assert_common_fields(log_message)
    assert log_message["audit_event"]["operation"] == "READ"
    assert log_message["audit_event"]["target"] == {
        "user_id": str(profile.user.uuid),
        "profile_id": str(profile.pk),
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


def test_actor_is_resolved_in_graphql_call(
    enable_audit_log, enable_audit_log_username, live_server, profile, cap_audit_log
):
    user = profile.user
    query = """
        query {
            myProfile {
                id
            }
        }"""

    do_graphql_call_as_user(live_server, user, query)
    audit_logs = cap_audit_log.get_logs()
    assert len(audit_logs) == 1
    log_message = audit_logs[0]
    assert_common_fields(log_message, actor_role="OWNER")
    assert log_message["audit_event"]["actor"]["user_id"] == str(user.uuid)
    assert log_message["audit_event"]["actor"]["user_name"] == user.username
