import json

import pytest
from django.conf import settings
from django.test.utils import patch_logger

from profiles.models import Profile

from .factories import ProfileFactory


@pytest.fixture()
def enable_audit_log():
    settings.AUDIT_LOGGING_ENABLED = True


@pytest.fixture()
def enable_audit_log_username():
    settings.AUDIT_LOG_USERNAME = True


def assert_common_fields(log_message):
    assert log_message["audit_event"]["origin"] == "PROFILE-BE"
    assert log_message["audit_event"]["status"] == "SUCCESS"
    assert log_message["audit_event"]["actor"]["role"] == "SYSTEM"
    assert log_message["audit_event"]["date_time_epoch"] is not None
    assert log_message["audit_event"]["date_time"] is not None


def test_audit_log_read(user, enable_audit_log):
    ProfileFactory()
    with patch_logger("audit", "info") as cm:
        profile = Profile.objects.first()
        assert len(cm) == 1
        log_message = json.loads(cm[0])
        assert_common_fields(log_message)
        assert log_message["audit_event"]["operation"] == "READ"
        assert log_message["audit_event"]["target"] == {
            "user_id": str(profile.user.uuid),
            "profile_id": str(profile.pk),
            "profile_part": "base profile",
        }


def test_audit_log_update(user, enable_audit_log, profile):
    with patch_logger("audit", "info") as cm:
        profile.first_name = "John"
        profile.save()
        assert len(cm) == 1
        log_message = json.loads(cm[0])
        assert_common_fields(log_message)
        assert log_message["audit_event"]["operation"] == "UPDATE"
        assert log_message["audit_event"]["target"] == {
            "user_id": str(profile.user.uuid),
            "profile_id": str(profile.pk),
            "profile_part": "base profile",
        }


def test_audit_log_delete(user, enable_audit_log, profile):
    with patch_logger("audit", "info") as cm:
        profile.delete()
        assert len(cm) == 1
        log_message = json.loads(cm[0])
        assert_common_fields(log_message)
        assert log_message["audit_event"]["operation"] == "DELETE"


def test_audit_log_create(user, enable_audit_log, enable_audit_log_username):
    with patch_logger("audit", "info") as cm:
        profile = ProfileFactory()
        assert len(cm) == 2  # profile is accessed here as well, thus the 2 log entries
        log_message = json.loads(cm[1])
        assert_common_fields(log_message)
        assert log_message["audit_event"]["operation"] == "CREATE"
        assert log_message["audit_event"]["target"] == {
            "user_id": str(profile.user.uuid),
            "user_name": profile.user.username,
            "profile_id": str(profile.pk),
            "profile_part": "base profile",
        }
