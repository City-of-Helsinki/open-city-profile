# -*- coding: utf-8 -*-
# snapshottest: v1 - https://goo.gl/zC4yUc
from __future__ import unicode_literals

from snapshottest import Snapshot

snapshots = Snapshot()

snapshots["test_get_profile_information_from_gdpr_api 1"] = {
    "children": [
        {"key": "BIRTH_DATE", "value": "2002-02-02"},
        {"key": "SCHOOL_NAME", "value": "Kontulan Alakoulu"},
        {"key": "SCHOOL_CLASS", "value": "1A"},
        {"key": "LANGUAGE_AT_HOME", "value": "fi"},
        {"key": "APPROVER_FIRST_NAME", "value": ""},
        {"key": "APPROVER_LAST_NAME", "value": ""},
        {"key": "APPROVER_PHONE", "value": ""},
        {"key": "APPROVER_EMAIL", "value": "patricia30@adams.com"},
        {"key": "EXPIRATION", "value": "2021-08-31 00:00"},
        {"key": "PHOTO_USAGE_APPROVED", "value": None},
        {"children": [], "key": "ADDITIONAL_CONTACT_PERSONS"},
    ],
    "key": "YOUTHPROFILE",
}
