from styx.ir.core import (
    Documentation,
)


def _ensure_period(s: str) -> str:
    if not s.endswith("."):
        return f"{s}."
    return s


def _ensure_double_linebreak_if_not_empty(s: str) -> str:
    if s == "" or s.endswith("\n\n"):
        return s
    if s.endswith("\n"):
        return f"{s}\n"
    return f"{s}\n\n"


def docs_to_docstring(docs: Documentation) -> str | None:
    re = ""
    if docs.title:
        re += docs.title

    if docs.description:
        re = _ensure_double_linebreak_if_not_empty(re)
        re += _ensure_period(docs.description)

    if docs.authors:
        re = _ensure_double_linebreak_if_not_empty(re)
        if len(docs.authors) == 1:
            re += f"Author: {docs.authors[0]}"
        else:
            re += f"Authors: {', '.join(docs.authors)}"

    if docs.literature:
        re = _ensure_double_linebreak_if_not_empty(re)
        if len(docs.literature) == 1:
            re += f"Literature: {docs.literature[0]}"
        else:
            re += f"Literature:\n{'\n'.join(docs.literature)}"

    if docs.authors:
        re = _ensure_double_linebreak_if_not_empty(re)
        if len(docs.urls) == 1:
            re += f"URL: {docs.urls[0]}"
        else:
            re += f"URLs:\n{'\n'.join(docs.urls)}"

    if re:
        return re
    return None
