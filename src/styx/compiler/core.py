from dataclasses import dataclass
from enum import Enum

from styx.boutiques import model as bt
from styx.boutiques.utils import boutiques_split_command
from styx.compiler.settings import CompilerSettings, DefsMode
from styx.compiler.utils import optional_float_to_int
from styx.pycodegen.core import INDENT as PY_INDENT
from styx.pycodegen.core import LineBuffer, PyArg, PyFunc, PyModule, collapse, indent
from styx.pycodegen.utils import (
    as_py_literal,
    enquote,
    ensure_camel_case,
    ensure_python_symbol,
    ensure_snake_case,
)

RUNTIME_DECLARATIONS = [
    'P = typing.TypeVar("P")',
    '"""Input host file type."""',
    'R = typing.TypeVar("R")',
    '"""Output host file type."""',
    "",
    "",
    "class Execution(typing.Protocol[P, R]):",
    *indent(
        [
            '"""',
            "Execution object used to execute commands.",
            "Created by `Runner.start_execution()`.",
            '"""',
            "def input_file(self, host_file: P) -> str:",
            *indent(
                [
                    '"""',
                    "Resolve host input files.",
                    "Returns a local filepath.",
                    "Called (potentially multiple times) after "
                    "`Runner.start_execution()` and before `Runner.run()`.",
                    '"""',
                    "...",
                ]
            ),
            "def run(self, cargs: list[str]) -> None:",
            *indent(
                [
                    '"""',
                    "Run the command.",
                    "Called after all `Execution.input_file()` calls and " "before `Execution.output_file()` calls.",
                    '"""',
                    "...",
                ]
            ),
            "def output_file(self, local_file: str) -> R:",
            *indent(
                [
                    '"""',
                    "Resolve local output files.",
                    "Returns a host filepath.",
                    "Called (potentially multiple times) after " "`Runner.run()` and before `Execution.finalize()`.",
                    '"""',
                    "...",
                ]
            ),
            "def finalize(self) -> None:",
            *indent(
                [
                    '"""',
                    "Finalize the execution.",
                    "Called after all `Execution.output_file()` calls.",
                    '"""',
                    "...",
                ]
            ),
        ]
    ),
    "",
    "",
    "class Runner(typing.Protocol[P, R]):",
    *indent(
        [
            '"""',
            "Runner object used to execute commands.",
            "Possible examples would be `LocalRunner`, " "`DockerRunner`, `DebugRunner`, ...",
            "Used as a factory for `Execution` objects.",
            '"""',
            "def start_execution(self, tool_name: str) -> Execution[P, R]:",
            *indent(
                [
                    '"""',
                    "Start an execution.",
                    "Called before any `Execution.input_file()` calls.",
                    '"""',
                    "...",
                ]
            ),
        ]
    ),
]


class BtPrimitive(Enum):
    String = 1
    Number = 2
    Integer = 3
    File = 4
    Flag = 5


@dataclass
class BtType:
    primitive: BtPrimitive
    is_list: bool
    is_optional: bool
    is_enum: bool


class BtInput:
    def __init__(self, bt_input: bt.Inputs) -> None:  # type: ignore
        self.bt_ref = bt_input.value_key
        self.name = ensure_snake_case(ensure_python_symbol(bt_input.id))
        self.docstring = bt_input.description
        self.command_line_flag = bt_input.command_line_flag
        self.list_separator = bt_input.list_separator if bt_input.list_separator is not None else " "

        # Validation

        self.minimum: float | int | None = None
        self.minimum_exclusive: bool = False
        self.maximum: float | int | None = None
        self.maximum_exclusive: bool = False
        self.list_minimum: int | None = None
        self.list_maximum: int | None = None

        if bt_input.type == bt.Type4.Number:  # type: ignore
            if bt_input.minimum is not None:
                self.minimum = int(bt_input.minimum) if bt_input.integer else bt_input.minimum
                self.minimum_exclusive = bt_input.exclusive_minimum is True
            if bt_input.maximum is not None:
                self.maximum = int(bt_input.maximum) if bt_input.integer else bt_input.maximum
                self.maximum_exclusive = bt_input.exclusive_maximum is True
        if bt_input.list is True:
            self.list_minimum = optional_float_to_int(bt_input.min_list_entries)
            self.list_maximum = optional_float_to_int(bt_input.max_list_entries)

        # Resolve type

        bt_is_list = bt_input.list is True
        bt_is_optional = bt_input.optional is True
        bt_is_enum = bt_input.value_choices is not None
        if bt_input.type == bt.Type4.String:  # type: ignore
            self.type = BtType(BtPrimitive.String, bt_is_list, bt_is_optional, bt_is_enum)
        elif bt_input.type == bt.Type4.File:  # type: ignore
            assert not bt_is_enum
            self.type = BtType(BtPrimitive.File, bt_is_list, bt_is_optional, False)
        elif bt_input.type == bt.Type4.Flag:  # type: ignore
            self.type = BtType(BtPrimitive.Flag, False, True, False)
        elif bt_input.type == bt.Type4.Number and not bt_input.integer:  # type: ignore
            self.type = BtType(BtPrimitive.Number, bt_is_list, bt_is_optional, bt_is_enum)
        elif bt_input.type == bt.Type4.Number and bt_input.integer:  # type: ignore
            self.type = BtType(BtPrimitive.Integer, bt_is_list, bt_is_optional, bt_is_enum)
        else:
            raise NotImplementedError

        # Python type
        self.py_type = self.bt_type_to_py_type(self.type, bt_input.value_choices)

        # Python default value
        self.py_default: str | None
        if self.type.primitive == BtPrimitive.Flag:
            self.py_default = "False"
        elif not self.type.is_optional:
            self.py_default = None
        else:
            self.py_default = "None"

        self.py_expr = self._make_py_expr()

    @classmethod
    def bt_type_to_py_type(cls, bt_type: BtType, enum_values: list | None) -> str:
        if bt_type.is_enum:
            assert enum_values is not None
            assert bt_type.primitive != BtPrimitive.Flag
            base = f"typing.Literal[{', '.join(map(as_py_literal, enum_values))}]"
        elif bt_type.primitive == BtPrimitive.String:
            base = "str"
        elif bt_type.primitive == BtPrimitive.Number:
            base = "float | int"
        elif bt_type.primitive == BtPrimitive.Integer:
            base = "int"
        elif bt_type.primitive == BtPrimitive.File:
            base = "P"
        elif bt_type.primitive == BtPrimitive.Flag:
            base = "bool"
        else:
            raise NotImplementedError

        if bt_type.primitive != BtPrimitive.Flag:
            if bt_type.is_list:
                base = f"list[{base}]"

            if bt_type.is_optional:
                base = f"{base} | None"

        return base

    def _make_py_expr(self) -> list[str]:
        buf = []

        if self.type.primitive == BtPrimitive.Flag:
            buf.extend(
                [
                    f"if {self.name}:",
                    *indent([f"cargs.append({enquote(self.command_line_flag)})"]),
                ]
            )
            return buf

        lvl = 0

        if self.type.is_optional:
            buf.append(f"if {self.name} is not None:")
            lvl += 1

        py_obj = self.name

        if self.type.primitive == BtPrimitive.File:
            py_obj = f"execution.input_file({py_obj})"

        if self.type.is_list:
            if self.type.primitive != BtPrimitive.String:
                py_obj = f"map(str, {py_obj})"
            py_obj = f'"{self.list_separator}".join({py_obj})'

        if self.command_line_flag:
            buf.extend(
                indent(
                    [f"cargs.extend([{enquote(self.command_line_flag)}, {py_obj}])"],
                    lvl,
                )
            )
        else:
            buf.extend(indent([f"cargs.append({py_obj})"], lvl))

        return buf


def _generate_raise_value_err(obj: str, expectation: str, reality: str | None = None) -> LineBuffer:
    fstr = ""
    if "{" in obj or "{" in expectation or (reality is not None and "{" in reality):
        fstr = "f"

    return (
        [f'raise ValueError({fstr}"{obj} must be {expectation} but was {reality}")']
        if reality is not None
        else [f'raise ValueError({fstr}"{obj} must be {expectation}")']
    )


def _generate_validation_expr(
    buf: LineBuffer,
    bt_input: BtInput,
) -> None:
    val_opt = ""
    if bt_input.type.is_optional:
        val_opt = f"{bt_input.name} is not None and "

    # List argument length validation
    if bt_input.list_minimum is not None and bt_input.list_maximum is not None:
        assert bt_input.list_minimum <= bt_input.list_maximum
        if bt_input.list_minimum == bt_input.list_maximum:
            buf.extend(
                [
                    f"if {val_opt}(len({bt_input.name}) != {bt_input.list_minimum}): ",
                    *indent(
                        _generate_raise_value_err(
                            f"Length of '{bt_input.name}'",
                            f"{bt_input.list_minimum}",
                            f"{{len({bt_input.name})}}",
                        )
                    ),
                ]
            )
        else:
            buf.extend(
                [
                    f"if {val_opt}not ({bt_input.list_minimum} <= len({bt_input.name}) <= {bt_input.list_maximum}): ",
                    *indent(
                        _generate_raise_value_err(
                            f"Length of '{bt_input.name}'",
                            f"between {bt_input.list_minimum} and {bt_input.list_maximum}",
                            f"{{len({bt_input.name})}}",
                        )
                    ),
                ]
            )
    elif bt_input.list_minimum is not None:
        buf.extend(
            [
                f"if {val_opt}not ({bt_input.list_minimum} <= len({bt_input.name})): ",
                *indent(
                    _generate_raise_value_err(
                        f"Length of '{bt_input.name}'",
                        f"greater than {bt_input.list_minimum}",
                        f"{{len({bt_input.name})}}",
                    )
                ),
            ]
        )
    elif bt_input.list_maximum is not None:
        buf.extend(
            [
                f"if {val_opt}not (len({bt_input.name}) <= {bt_input.list_maximum}): ",
                *indent(
                    _generate_raise_value_err(
                        f"Length of '{bt_input.name}'",
                        f"less than {bt_input.list_maximum}",
                        f"{{len({bt_input.name})}}",
                    )
                ),
            ]
        )

    # Numeric argument range validation
    op_min = "<" if bt_input.minimum_exclusive else "<="
    op_max = "<" if bt_input.maximum_exclusive else "<="
    if bt_input.minimum is not None and bt_input.maximum is not None:
        assert bt_input.minimum <= bt_input.maximum
        if bt_input.type.is_list:
            buf.extend(
                [
                    f"if {val_opt}not ({bt_input.minimum} {op_min} min({bt_input.name}) "
                    f"and max({bt_input.name}) {op_max} {bt_input.maximum}): ",
                    *indent(
                        _generate_raise_value_err(
                            f"All elements of '{bt_input.name}'",
                            f"between {bt_input.minimum} {op_min} x {op_max} {bt_input.maximum}",
                        )
                    ),
                ]
            )
        else:
            buf.extend(
                [
                    f"if {val_opt}not ({bt_input.minimum} {op_min} {bt_input.name} {op_max} {bt_input.maximum}): ",
                    *indent(
                        _generate_raise_value_err(
                            f"'{bt_input.name}'",
                            f"between {bt_input.minimum} {op_min} x {op_max} {bt_input.maximum}",
                            f"{{{bt_input.name}}}",
                        )
                    ),
                ]
            )
    elif bt_input.minimum is not None:
        if bt_input.type.is_list:
            buf.extend(
                [
                    f"if {val_opt}not ({bt_input.minimum} {op_min} min({bt_input.name})): ",
                    *indent(
                        _generate_raise_value_err(
                            f"All elements of '{bt_input.name}'",
                            f"greater than {bt_input.minimum} {op_min} x",
                        )
                    ),
                ]
            )
        else:
            buf.extend(
                [
                    f"if {val_opt}not ({bt_input.minimum} {op_min} {bt_input.name}): ",
                    *indent(
                        _generate_raise_value_err(
                            f"'{bt_input.name}'",
                            f"greater than {bt_input.minimum} {op_min} x",
                            f"{{{bt_input.name}}}",
                        )
                    ),
                ]
            )
    elif bt_input.maximum is not None:
        if bt_input.type.is_list:
            buf.extend(
                [
                    f"if {val_opt}not (max({bt_input.name}) {op_max} {bt_input.maximum}): ",
                    *indent(
                        _generate_raise_value_err(
                            f"All elements of '{bt_input.name}'",
                            f"less than x {op_max} {bt_input.maximum}",
                        )
                    ),
                ]
            )
        else:
            buf.extend(
                [
                    f"if {val_opt}not ({bt_input.name} {op_max} {bt_input.maximum}): ",
                    *indent(
                        _generate_raise_value_err(
                            f"'{bt_input.name}'",
                            f"less than x {op_max} {bt_input.maximum}",
                            f"{{{bt_input.name}}}",
                        )
                    ),
                ]
            )


def py_from_boutiques(tool: bt.Tool, settings: CompilerSettings) -> str:  # type: ignore
    mod = PyModule()

    # Python names
    py_func_name = ensure_snake_case(ensure_python_symbol(tool.name))
    py_output_class_name = f"{ensure_camel_case(tool.name)}Outputs"

    # Arguments
    args: list[BtInput] = []
    for i in tool.inputs:
        args.append(BtInput(i))

    # Docstring
    docstring = tool.description

    # Function body
    buf_body: list[str] = [
        f"execution = runner.start_execution({enquote(tool.name)})",
        "cargs = []",
    ]

    # Arguments
    cmd = boutiques_split_command(tool.command_line)
    args_lookup = {a.bt_ref: a for a in args}

    pyargs = [PyArg(name="runner", type="Runner[P, R]", default=None, docstring="Command runner")]
    pyargs += [PyArg(name=i.name, type=i.py_type, default=i.py_default, docstring=i.docstring) for i in args]

    # Input validation
    for i in args:
        _generate_validation_expr(buf_body, i)

    # Command line args building
    for segment in cmd:
        if segment in args_lookup:
            i = args_lookup[segment]
            buf_body.extend(i.py_expr)
        else:
            buf_body.append(f"cargs.append({enquote(segment)})")

    buf_body.append("execution.run(cargs)")

    # Definitions
    if settings.defs_mode == DefsMode.INLINE:
        defs = RUNTIME_DECLARATIONS
    elif settings.defs_mode == DefsMode.IMPORT:
        defs = ["from styx.runners.styxdefs import *"]
    else:
        return collapse(RUNTIME_DECLARATIONS)

    buf_header = []
    buf_header.extend(
        [
            *defs,
            "",
            "",
            f"class {py_output_class_name}(typing.NamedTuple, typing.Generic[R]):",
            *indent(
                [
                    '"""',
                    f"Output object returned when calling `{py_func_name}(...)`.",
                    '"""',
                ]
            ),
        ]
    )

    # Outputs
    for o in tool.output_files:
        # Field
        buf_header.append(f"{PY_INDENT}{o.id}: R")
        # Docstring
        buf_header.append(f'{PY_INDENT}"""{o.description}"""')

    buf_body.append(f"ret = {py_output_class_name}(")
    for o in tool.output_files:
        s = o.path_template
        for i in args:
            s = s.replace(f"{i.bt_ref}", f"{{{i.name}}}")

        buf_body.append(f"{PY_INDENT}{o.id}=execution.output_file(f{enquote(s)}),")

    buf_body.extend(
        [
            ")",
            "execution.finalize()",
            "return ret",
        ]
    )

    mod.header.extend(buf_header)

    mod.funcs.append(
        PyFunc(
            name=py_func_name,
            args=pyargs,
            return_type=f"{py_output_class_name}[R]",
            return_descr=f"NamedTuple of outputs " f"(described in `{py_output_class_name}`).",
            docstring_body=docstring,
            body=buf_body,
        )
    )

    mod.imports.extend(["import typing"])
    mod.imports.sort()

    return mod.text()


def compile_descriptor(descriptor: bt.Tool, settings: CompilerSettings) -> str:  # type: ignore
    """Compile a Boutiques descriptor to Python code."""
    return py_from_boutiques(descriptor, settings)
