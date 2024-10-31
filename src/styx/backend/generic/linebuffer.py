"""Probably pretty slow but convenient."""

LineBuffer = list[str]
INDENT = "    "


def indent(lines: LineBuffer, level: int = 1) -> LineBuffer:
    """Indent a LineBuffer by a given level."""
    if level == 0:
        return lines
    return [f"{INDENT * level}{line}" for line in lines]


def comment(lines: LineBuffer, line_comment_indicator: str = "#") -> LineBuffer:
    """Add a comment to a LineBuffer."""
    return [f"{line_comment_indicator} {line}" for line in lines]


def collapse(lines: LineBuffer) -> str:
    """Collapse a LineBuffer into a single string."""
    return "\n".join(lines)


def expand(text: str) -> LineBuffer:
    """Expand a string into a LineBuffer."""
    return text.splitlines()


def concat(line_buffers: list[LineBuffer], separator: LineBuffer | None = None) -> LineBuffer:
    """Concatenate multiple LineBuffers."""
    if separator is None:
        return sum(line_buffers, [])
    ret = []
    for i, buf in enumerate(line_buffers):
        if i > 0:
            ret.extend(separator)
        ret.extend(buf)
    return ret


def blank_before(lines: LineBuffer, blanks: int = 1) -> LineBuffer:
    """Add blank lines at the beginning of a LineBuffer if it is not empty."""
    return [*([""] * blanks), *lines] if len(lines) > 0 else lines


def blank_after(lines: LineBuffer, blanks: int = 1) -> LineBuffer:
    """Add blank lines at the end of a LineBuffer if it is not empty."""
    return [*lines, *([""] * blanks)] if len(lines) > 0 else lines
