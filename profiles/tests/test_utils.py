from enum import Enum

import pytest

from profiles.utils import enum_values, force_list


@pytest.mark.parametrize(
    "input_value,expected",
    [
        ([1, 2, 3], [1, 2, 3]),
        ([], []),
        (None, []),
        ("foo", ["foo"]),
        ((1, 2), [(1, 2)]),  # tuples are treated as single values
    ],
)
def test_force_list(input_value, expected):
    assert force_list(input_value) == expected


def test_enum_values():
    class TestEnum(Enum):
        FOO = "foo"
        BAR = "bar"

    assert enum_values(TestEnum) == ["foo", "bar"]
