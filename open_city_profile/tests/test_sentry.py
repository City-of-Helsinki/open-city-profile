import pytest
from helusers.oidc import AuthenticationError

from open_city_profile.settings import sentry_before_send

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
