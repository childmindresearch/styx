import json
import typing
from dataclasses import dataclass
from enum import Enum

from styx.boutiques import model as bt
from styx.boutiques.utils import boutiques_split_command

from .pycodegen import INDENT as PY_INDENT
from .pycodegen import PyArg, PyFunc, PyModule, indent
from .utils import enquote, ensure_camel_case, ensure_python_symbol, ensure_snake_case

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
                    "Called after all `Execution.input_file()` calls and "
                    "before `Execution.output_file()` calls.",
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
                    "Called (potentially multiple times) after "
                    "`Runner.run()` and before `Execution.finalize()`.",
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
            "Possible examples would be `LocalRunner`, "
            "`DockerRunner`, `DebugRunner`, ...",
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
        self.list_separator = (
            bt_input.list_separator if bt_input.list_separator is not None else " "
        )

        # Resolve type

        bt_is_list = bt_input.list is True
        bt_is_optional = bt_input.optional is True
        bt_is_enum = bt_input.value_choices is not None
        if bt_input.type == bt.Type4.String:  # type: ignore
            self.type = BtType(
                BtPrimitive.String, bt_is_list, bt_is_optional, bt_is_enum
            )
        elif bt_input.type == bt.Type4.File:  # type: ignore
            assert not bt_is_enum
            self.type = BtType(BtPrimitive.File, bt_is_list, bt_is_optional, False)
        elif bt_input.type == bt.Type4.Flag:  # type: ignore
            self.type = BtType(BtPrimitive.Flag, False, True, False)
        elif bt_input.type == bt.Type4.Number and not bt_input.integer:  # type: ignore
            self.type = BtType(
                BtPrimitive.Number, bt_is_list, bt_is_optional, bt_is_enum
            )
        elif bt_input.type == bt.Type4.Number and bt_input.integer:  # type: ignore
            self.type = BtType(
                BtPrimitive.Integer, bt_is_list, bt_is_optional, bt_is_enum
            )
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


def as_py_literal(obj: str | float | int | bool) -> str:
    if isinstance(obj, str):
        return enquote(obj)
    else:
        return str(obj)


def text_from_boutiques_json(json_data: typing.Any) -> str:  # noqa: ANN401
    tool = bt.Tool(**json_data)  # type: ignore

    mod = PyModule()

    # Function name
    name = ensure_snake_case(ensure_python_symbol(tool.name))

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

    # Sort arguments by occurrence in command line
    cmd = boutiques_split_command(tool.command_line)
    cmd_lookup = {v: i for i, v in enumerate(cmd)}
    args.sort(key=lambda a: cmd_lookup[a.bt_ref])

    pyargs = [
        PyArg(
            name="runner", type="Runner[P, R]", default=None, docstring="Command runner"
        )
    ]
    pyargs += [
        PyArg(name=i.name, type=i.py_type, default=i.py_default, docstring=i.docstring)
        for i in args
    ]
    for i in args:
        buf_body.extend(i.py_expr)

    buf_body.append("execution.run(cargs)")

    # named tuple return

    out_cls = f"{ensure_camel_case(tool.name)}Outputs"

    buf_header = []
    buf_header.extend(
        [
            *RUNTIME_DECLARATIONS,
            "",
            "",
            f"class {out_cls}(typing.NamedTuple, typing.Generic[R]):",
            *indent(
                [
                    '"""',
                    f"Output object returned when calling `{name}(...)`.",
                    '"""',
                ]
            ),
        ]
    )

    for o in tool.output_files:
        # Field
        buf_header.append(f"{PY_INDENT}{o.id}: R")
        # Docstring
        buf_header.append(f'{PY_INDENT}"""{o.description}"""')

    buf_body.append(f"ret = {out_cls}(")
    for o in tool.output_files:
        s = o.path_template
        for i in args:
            s = s.replace(f"{i.bt_ref}", f"{{{i.name}}}")

        buf_body.append(f"{PY_INDENT}{o.id}=execution.output_file(f{enquote(s)}),")

    buf_body.append(")")
    buf_body.append("execution.finalize()")
    buf_body.append("return ret")

    mod.header.extend(buf_header)

    mod.funcs.append(
        PyFunc(
            name=name,
            args=pyargs,
            return_type=f"{out_cls}[R]",
            return_descr=f"NamedTuple of outputs (described in `{out_cls}`).",
            docstring_body=docstring,
            body=buf_body,
        )
    )

    mod.imports.extend(["import typing"])
    mod.imports.sort()

    return mod.text()


def main() -> None:
    with open("desc.json", "r") as json_file:
        json_data = json.load(json_file)

    print(text_from_boutiques_json(json_data))


if __name__ == "__main__":
    main()
