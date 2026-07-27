import pytest
from helusers.oidc import AuthenticationError

from open_city_profile.settings import SENTRY_EVENT_SCRUBBER, sentry_before_send

test_cases = [
    (AuthenticationError("JWT verification failed."), True),
    (Exception("Some other error"), False),
]


@pytest.mark.parametrize(
    "exception,should_return_none",
    test_cases,
)
def test_sentry_before_send_ignores_defined_exceptions(exception, should_return_none):
    hint = {"exc_info": (type(exception), exception, None)}
    event = {"something": "test event is returned when not ignored"}

    result = sentry_before_send(event, hint)

    if should_return_none:
        assert result is None  # Ensure the event is dropped
    else:
        assert result == event  # Ensure the event is not dropped


def test_sentry_scrubs_verified_personal_information_input_recursively():
    sensitive_value = {
        "first_name": "Sensitive first name",
        "national_identification_number": "010101-0101",
    }
    event = {
        "request": {
            "data": {
                "variables": {
                    "verified_personal_information_input": sensitive_value,
                },
            },
        },
    }

    SENTRY_EVENT_SCRUBBER.scrub_event(event)

    assert "Sensitive first name" not in repr(event)
    assert "010101-0101" not in repr(event)
