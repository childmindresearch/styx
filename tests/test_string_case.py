"""Test convertsions to and from snake_case and camelCase."""

import pytest

from styx.backend.generic.string_case import (
    camel_case,
    pascal_case,
    screaming_snake_case,
    snake_case,
)


@pytest.mark.parametrize(
    "input,expected",
    [
        ("", ""),
        ("snake_case", "snake_case"),
        ("SNAKE_CASE", "snake_case"),
        ("camelCase", "camel_case"),
        ("CamelCase", "camel_case"),
        ("snake_case_with_underscores", "snake_case_with_underscores"),
        ("SNAKE_CASE_WITH_UNDERSCORES", "snake_case_with_underscores"),
        ("camelCaseWithUnderscores", "camel_case_with_underscores"),
        ("CamelCaseWithUnderscores", "camel_case_with_underscores"),
        ("123", "123"),
        ("123_456", "123_456"),
        ("A123", "a123"),
        ("A123b456", "a123b456"),
        ("A123B456", "a123_b456"),
        ("A123B456C789", "a123_b456_c789"),
        ("a123_b456_c789", "a123_b456_c789"),
    ],
)
def test_ensure_snake_case(input: str, expected: str) -> None:
    assert snake_case(input) == expected


@pytest.mark.parametrize(
    "input,expected",
    [
        ("", ""),
        ("snake_case", "snakeCase"),
        ("SNAKE_CASE", "snakeCase"),
        ("camelCase", "camelCase"),
        ("CamelCase", "camelCase"),
        ("snake_case_with_underscores", "snakeCaseWithUnderscores"),
        ("SNAKE_CASE_WITH_UNDERSCORES", "snakeCaseWithUnderscores"),
        ("camelCaseWithUnderscores", "camelCaseWithUnderscores"),
        ("CamelCaseWithUnderscores", "camelCaseWithUnderscores"),
        ("123", "123"),
        ("123_456", "123456"),
        ("A123", "a123"),
        ("A123b456", "a123b456"),
        ("A123B456", "a123B456"),
        ("A123B456C789", "a123B456C789"),
        ("a123_b456_c789", "a123B456C789"),
    ],
)
def test_ensure_camel_case(input: str, expected: str) -> None:
    assert camel_case(input) == expected


@pytest.mark.parametrize(
    "input,expected",
    [
        ("", ""),
        ("snake_case", "SnakeCase"),
        ("SNAKE_CASE", "SnakeCase"),
        ("camelCase", "CamelCase"),
        ("CamelCase", "CamelCase"),
        ("snake_case_with_underscores", "SnakeCaseWithUnderscores"),
        ("SNAKE_CASE_WITH_UNDERSCORES", "SnakeCaseWithUnderscores"),
        ("camelCaseWithUnderscores", "CamelCaseWithUnderscores"),
        ("CamelCaseWithUnderscores", "CamelCaseWithUnderscores"),
        ("123", "123"),
        ("123_456", "123456"),
        ("A123", "A123"),
        ("A123b456", "A123b456"),
        ("A123B456", "A123B456"),
        ("A123B456C789", "A123B456C789"),
        ("a123_b456_c789", "A123B456C789"),
    ],
)
def test_ensure_pascal_case(input: str, expected: str) -> None:
    assert pascal_case(input) == expected


@pytest.mark.parametrize(
    "input,expected",
    [
        ("", ""),
        ("snake_case", "SNAKE_CASE"),
        ("SNAKE_CASE", "SNAKE_CASE"),
        ("camelCase", "CAMEL_CASE"),
        ("CamelCase", "CAMEL_CASE"),
        ("snake_case_with_underscores", "SNAKE_CASE_WITH_UNDERSCORES"),
        ("SNAKE_CASE_WITH_UNDERSCORES", "SNAKE_CASE_WITH_UNDERSCORES"),
        ("camelCaseWithUnderscores", "CAMEL_CASE_WITH_UNDERSCORES"),
        ("CamelCaseWithUnderscores", "CAMEL_CASE_WITH_UNDERSCORES"),
        ("123", "123"),
        ("123_456", "123_456"),
        ("A123", "A123"),
        ("A123b456", "A123B456"),
        ("A123B456", "A123_B456"),
        ("A123B456C789", "A123_B456_C789"),
        ("a123_b456_c789", "A123_B456_C789"),
    ],
)
def test_ensure_screaming_snake_case(input: str, expected: str) -> None:
    assert screaming_snake_case(input) == expected
