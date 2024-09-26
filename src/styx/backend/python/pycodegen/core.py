"""Generic Python code generation utilities. Implemented on demand."""

from abc import ABC
from dataclasses import dataclass, field

from styx.backend.python.pycodegen.utils import enquote, ensure_endswith, linebreak_paragraph

LineBuffer = list[str]
INDENT = "    "


def indent(lines: LineBuffer, level: int = 1) -> LineBuffer:
    """Indent a LineBuffer by a given level."""
    if level == 0:
        return lines
    return [f"{INDENT * level}{line}" for line in lines]


def comment(lines: LineBuffer) -> LineBuffer:
    """Add a comment to a LineBuffer."""
    return [f"# {line}" for line in lines]


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


class PyGen(ABC):
    def generate(self) -> LineBuffer:
        """Generate the code."""
        raise NotImplementedError

    def text(self) -> str:
        """Generate the code and collapse it into a single string."""
        return collapse(self.generate())


@dataclass
class PyArg:
    """Python function argument."""

    name: str
    type: str | None = None
    default: str | None = None
    docstring: str | None = None

    def declaration(self) -> str:
        """Generate the argument declaration ("var[: type][ = default]")."""
        annot_type = f": {self.type}" if self.type is not None else ""
        if self.default is None:
            return f"{self.name}{annot_type}"
        return f"{self.name}{annot_type} = {self.default}"


@dataclass
class PyFunc(PyGen):
    """Python function."""

    name: str
    args: list[PyArg] = field(default_factory=list)
    docstring_body: str | None = None
    body: LineBuffer = field(default_factory=list)
    return_descr: str | None = None
    return_type: str | None = None

    def generate(self) -> LineBuffer:
        buf = []

        # Sort arguments so default arguments come last
        self.args.sort(key=lambda a: a.default is not None)

        # Function signature
        buf.append(f"def {self.name}(")

        # Add arguments
        for arg in self.args:
            buf.extend(indent([f"{arg.declaration()},"]))
        buf.append(f") -> {self.return_type}:")

        arg_docstr_buf = []
        for arg in self.args:
            if arg.name == "self":
                continue
            arg_docstr = linebreak_paragraph(
                f"{arg.name}: {arg.docstring if arg.docstring else ''}",
                width=80 - (4 * 3) - 1,
                first_line_width=80 - (4 * 2) - 1,
            )
            arg_docstr = ensure_endswith("\\\n".join(arg_docstr), ".").split("\n")
            arg_docstr_buf.append(arg_docstr[0])
            arg_docstr_buf.extend(indent(arg_docstr[1:]))

        # Add docstring (Google style)

        if self.docstring_body:
            docstring_linebroken = linebreak_paragraph(self.docstring_body, width=80 - 4)
        else:
            docstring_linebroken = [""]

        buf.extend(
            indent([
                '"""',
                *docstring_linebroken,
                "",
                "Args:",
                *indent(arg_docstr_buf),
                *(["Returns:", *indent([f"{self.return_descr}"])] if self.return_descr else []),
                '"""',
            ])
        )

        # Add function body
        if self.body:
            buf.extend(indent(self.body))
        else:
            buf.extend(indent(["pass"]))
        return buf


@dataclass
class PyDataClass(PyGen):
    """Python generate."""

    name: str
    docstring: str | None
    fields: list[PyArg] = field(default_factory=list)
    methods: list[PyFunc] = field(default_factory=list)
    is_named_tuple: bool = False

    def generate(self) -> LineBuffer:
        # Sort fields so default arguments come last
        self.fields.sort(key=lambda a: a.default is not None)

        def _arg_docstring(arg: PyArg) -> LineBuffer:
            if not arg.docstring:
                return []
            return linebreak_paragraph(f'"""{arg.docstring}"""', width=80 - 4, first_line_width=80 - 4)

        args = concat([[f.declaration(), *_arg_docstring(f)] for f in self.fields])
        methods = concat([method.generate() for method in self.methods], [""])

        if not self.is_named_tuple:
            buf = [
                "@dataclasses.dataclass",
                f"class {self.name}:",
                *indent([
                    *(
                        ['"""', *linebreak_paragraph(self.docstring, width=80 - 4, first_line_width=80 - 4), '"""']
                        if self.docstring
                        else []
                    ),
                    *args,
                    *blank_before(methods),
                ]),
            ]
        else:
            buf = [
                f"class {self.name}(typing.NamedTuple):",
                *indent([
                    '"""',
                    f"{self.docstring}",
                    '"""',
                    *args,
                    *blank_before(methods),
                ]),
            ]

        return buf


@dataclass
class PyModule(PyGen):
    """Python module."""

    imports: LineBuffer = field(default_factory=list)
    header: LineBuffer = field(default_factory=list)
    funcs_and_classes: list[PyFunc | PyDataClass] = field(default_factory=list)
    footer: LineBuffer = field(default_factory=list)
    exports: list[str] = field(default_factory=list)
    docstr: str | None = None

    def generate(self) -> LineBuffer:
        exports = (
            [
                "__all__ = [",
                *indent(list(map(lambda x: f"{enquote(x)},", sorted(self.exports)))),
                "]",
            ]
            if self.exports
            else []
        )

        return blank_after([
            *(['"""', *linebreak_paragraph(self.docstr), '"""'] if self.docstr else []),
            *comment([
                "This file was auto generated by Styx.",
                "Do not edit this file directly.",
            ]),
            *blank_before(self.imports),
            *blank_before(self.header),
            *[line for func in self.funcs_and_classes for line in blank_before(func.generate(), 2)],
            *blank_before(self.footer),
            *blank_before(exports, 2),
        ])
