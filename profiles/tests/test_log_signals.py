import json

import pytest
from django.conf import settings
from django.test.utils import patch_logger

from profiles.models import Profile

from .factories import ProfileFactory


@pytest.fixture()
def enable_audit_log():
    settings.AUDIT_LOGGING_ENABLED = True


def test_audit_log_read(user, enable_audit_log):
    ProfileFactory()
    with patch_logger("audit", "info") as cm:
        profile = Profile.objects.first()
        assert len(cm) == 1
        log_message = json.loads(cm[0])
        assert log_message["profile_event"]["status"] == "SUCCESS"
        assert log_message["profile_event"]["actor_user"]["role"] == "system"
        assert not log_message["profile_event"]["actor_user"]["user_id"]
        assert log_message["profile_event"]["operation"] == "read"
        assert log_message["profile_event"]["target_profile"] == {
            "user_id": profile.user_id,
            "profile_id": str(profile.pk),
            "profile_part": "base profile",
        }


def test_audit_log_update(user, enable_audit_log, profile):
    with patch_logger("audit", "info") as cm:
        profile.first_name = "John"
        profile.save()
        assert len(cm) == 1
        log_message = json.loads(cm[0])
        assert log_message["profile_event"]["status"] == "SUCCESS"
        assert log_message["profile_event"]["actor_user"]["role"] == "system"
        assert not log_message["profile_event"]["actor_user"]["user_id"]
        assert log_message["profile_event"]["operation"] == "update"
        assert log_message["profile_event"]["target_profile"] == {
            "user_id": profile.user_id,
            "profile_id": str(profile.pk),
            "profile_part": "base profile",
        }


def test_audit_log_delete(user, enable_audit_log, profile):
    with patch_logger("audit", "info") as cm:
        profile.delete()
        assert len(cm) == 1
        log_message = json.loads(cm[0])
        assert log_message["profile_event"]["status"] == "SUCCESS"
        assert log_message["profile_event"]["actor_user"]["role"] == "system"
        assert not log_message["profile_event"]["actor_user"]["user_id"]
        assert log_message["profile_event"]["operation"] == "delete"


def test_audit_log_create(user, enable_audit_log):
    with patch_logger("audit", "info") as cm:
        profile = ProfileFactory()
        assert len(cm) == 2  # profile is accessed here as well, thus the 2 log entries
        log_message = json.loads(cm[1])
        assert log_message["profile_event"]["status"] == "SUCCESS"
        assert log_message["profile_event"]["actor_user"]["role"] == "system"
        assert not log_message["profile_event"]["actor_user"]["user_id"]
        assert log_message["profile_event"]["operation"] == "create"
        assert log_message["profile_event"]["target_profile"] == {
            "user_id": profile.user_id,
            "profile_id": str(profile.pk),
            "profile_part": "base profile",
        }
