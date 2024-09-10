import dataclasses
from dataclasses import fields, is_dataclass
from typing import Any

_LineBuffer = list[str]


def _expand(text: str) -> _LineBuffer:
    """Expand a string into a LineBuffer."""
    return text.splitlines()


def _indent(lines: _LineBuffer, level: int = 1) -> _LineBuffer:
    """Indent a LineBuffer by a given level."""
    if level == 0:
        return lines
    return [f"{' ' * level}{line}" for line in lines]


def _indentation(level: int = 1) -> str:
    return " " * level


def _pretty_print(obj: Any, ind: int = 0) -> str:  # noqa: ANN401
    def field_is_default(obj: Any, field_: dataclasses.Field) -> bool:  # noqa: ANN401
        val = getattr(obj, field_.name)
        if val == field_.default:
            return True
        if field_.default_factory != dataclasses.MISSING:
            return val == field_.default_factory()
        return False

    match obj:
        case bool():
            return f"{obj}"
        case str():
            return obj.__repr__()
        case int():
            return f"{obj}"
        case float():
            return f"{obj}"
        case dict():
            if len(obj) == 0:
                return "{}"
            return f"\n{_indentation(ind)}".join([
                "{",
                *_expand(",\n".join([f" {_pretty_print(key, 1)}: {_pretty_print(value, 1)}" for key, value in obj])),
                "}",
            ])
        case list():
            if len(obj) == 0:
                return "[]"
            return f"\n{_indentation(ind)}".join([
                "[",
                *_expand(",\n".join([f" {_pretty_print(value, 1)}" for value in obj])),
                "]",
            ])
        case _:
            if is_dataclass(obj):
                return f"\n{_indentation(ind)}".join([
                    f"{obj.__class__.__name__}(",
                    *_expand(
                        ",\n".join([
                            f" {field.name}={_pretty_print(getattr(obj, field.name), 1)}"
                            for field in fields(obj)
                            if not field_is_default(obj, field)
                        ])
                    ),
                    ")",
                ])
            else:
                return str(obj)


def pretty_print(obj: Any) -> None:  # noqa: ANN401
    from rich import print

    print(_pretty_print(obj))
