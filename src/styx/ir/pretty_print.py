import dataclasses
from dataclasses import is_dataclass, fields
from typing import Any

from styx.pycodegen.core import LineBuffer


def indent(lines: LineBuffer, level: int = 1) -> LineBuffer:
    """Indent a LineBuffer by a given level."""
    if level == 0:
        return lines
    return [f"{' ' * level}{line}" for line in lines]


def indentation(level: int = 1):
    return ' ' * level


def _pretty_print(obj: Any, ind=0) -> str:

    def field_is_default(obj, field_):
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
            return f'\n{indentation(ind)}'.join([
                "{",
                *indent([
                    f"{_pretty_print(key, ind+1)}: {_pretty_print(value, ind+1)}" for key, value in obj
                ]),
                "}"
            ])
        case list():
            if len(obj) == 0:
                return "[]"
            return f'\n{indentation(ind)}'.join([
                "[",
                *indent([
                    f"{_pretty_print(value, ind+1)}" for value in obj
                ]),
                "]"
            ])
        case _:
            if is_dataclass(obj):
                return f'\n{indentation(ind)}'.join([
                    f"{obj.__class__.__name__}(",
                    *indent([
                        f"{field.name}={_pretty_print(getattr(obj, field.name), ind+1)}"
                        for field in fields(obj)
                        if not field_is_default(obj, field)
                    ]),
                    f")",
                ])
            else:
                return str(obj)


def pretty_print(obj: Any):
    from rich import print
    print(_pretty_print(obj))

