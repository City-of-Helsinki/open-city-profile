from datetime import datetime, timedelta

import pytest


def assert_almost_equal(a, b, epsilon=None):
    __tracebackhide__ = True

    def _both_of_type(typ):
        return isinstance(a, typ) and isinstance(b, typ)

    def _absolute_delta_equality(default_epsilon):
        delta = abs(a - b)
        eps = epsilon if epsilon is not None else default_epsilon
        if delta > eps:
            pytest.fail(
                f"{a} is not almost equal to {b} (difference {delta} is more than allowed {eps})"
            )

    if _both_of_type(datetime):
        _absolute_delta_equality(timedelta(milliseconds=1))
    elif _both_of_type(int):
        _absolute_delta_equality(1)
    else:
        raise NotImplementedError(
            f"assert_almost_equal not implemented for types {type(a)} and {type(b)}"
        )


def assert_match_error_code(response, error_code):
    assert response["errors"][0].get("extensions").get("code") == error_code
