from datetime import datetime, timedelta

import pytest


def assert_almost_equal(a, b, epsilon=None):
    __tracebackhide__ = True

    if isinstance(a, datetime) and isinstance(b, datetime):
        delta = abs(a - b)
        epsilon = epsilon if epsilon is not None else timedelta(milliseconds=1)
        if delta > epsilon:
            pytest.fail(
                f"{a} is not almost equal to {b} (difference {delta} is more than allowd {epsilon})"
            )
    else:
        raise NotImplementedError(
            f"assert_almost_equal not implemented for types {type(a)} and {type(b)}"
        )
