import pathlib
import re

from styx.backend.generic.languageprovider import _TYPE_PYLITERAL, LanguageProvider
from styx.backend.generic.linebuffer import LineBuffer, blank_after, blank_before, comment, concat, expand, indent
from styx.backend.generic.model import GenericArg, GenericDataClass, GenericFunc, GenericModule, GenericNamedTuple
from styx.backend.generic.scope import Scope
from styx.backend.generic.string_case import pascal_case, screaming_snake_case, snake_case
from styx.backend.generic.utils import enbrace, enquote, ensure_endswith, escape_backslash, linebreak_paragraph
from styx.ir import core as ir


class PythonLanguageProvider(LanguageProvider):
    def cargs_0d_or_1d_to_0d(self, val_and_islist: list[tuple[str, bool]]) -> list[str]:
        return [(f"*{val}" if val_is_list else val) for val, val_is_list in val_and_islist]

    def struct_collect_outputs(self, struct: ir.Param[ir.Param.Struct], struct_symbol: str) -> str:
        if struct.list_:
            opt = ""
            if struct.nullable:
                opt = f" if {struct_symbol} else None"
            # Need to check for attr because some alts might have outputs others not.
            # todo: think about alternative solutions
            return f'[i.outputs(execution) if hasattr(i, "outputs") else None for i in {struct_symbol}]{opt}'

        o = f"{struct_symbol}.outputs(execution)"
        if struct.nullable:
            o = f"{o} if {struct_symbol} else None"
        return o

    def numeric_to_str(self, numeric_expr: str) -> str:
        return f"str({numeric_expr})"

    def null(self) -> str:
        return "None"

    def runner_symbol(self) -> str:
        return "runner"

    def runner_declare(self, runner_symbol: str) -> LineBuffer:
        return [f"{runner_symbol} = {runner_symbol} or get_global_runner()"]

    def execution_symbol(self) -> str:
        return "execution"

    def execution_declare(self, execution_symbol: str, metadata_symbol: str) -> LineBuffer:
        return [f"{execution_symbol} = runner.start_execution({metadata_symbol})"]

    def execution_run(self, execution_symbol: str, cargs_symbol: str) -> LineBuffer:
        return [f"{execution_symbol}.run({cargs_symbol})"]

    def legal_symbol(self, symbol: str) -> bool:
        return symbol.isidentifier()

    def language_scope(self) -> Scope:
        import builtins
        import keyword
        import sys

        scope = Scope(self)

        for s in {
            *keyword.kwlist,
            *sys.stdlib_module_names,
            *dir(builtins),
            *dir(__builtins__),
        }:
            scope.add_or_die(s)

        return scope

    def ensure_symbol(self, name: str) -> str:
        alt_prefix: str = "v_"
        name = re.sub(r"[^a-zA-Z0-9_]", "_", name)
        # Prefix if name starts with a digit or underscore
        if re.match(r"^[0-9_]", name):
            name = f"{alt_prefix}{name}"
        return name

    def ensure_constant_case(self, name: str) -> str:
        return screaming_snake_case(self.ensure_symbol(name))

    def ensure_class_case(self, name: str) -> str:
        return pascal_case(self.ensure_symbol(name))

    def ensure_var_case(self, name: str) -> str:
        return snake_case(self.ensure_symbol(name))

    def generate_arg_declaration(self, arg: GenericArg) -> str:
        annot_type = f": {arg.type}" if arg.type is not None else ""
        if arg.default is None:
            return f"{arg.name}{annot_type}"
        return f"{arg.name}{annot_type} = {arg.default}"

    def generate_func(self, func: GenericFunc) -> LineBuffer:
        buf = []

        # Sort arguments so default arguments come last
        func.args.sort(key=lambda a: a.default is not None)

        # Function signature
        buf.append(f"def {func.name}(")

        # Add arguments
        for arg in func.args:
            buf.extend(indent([f"{self.generate_arg_declaration(arg)},"]))
        buf.append(f") -> {func.return_type}:")

        arg_docstr_buf = []
        for arg in func.args:
            if arg.name == "self":
                continue
            arg_docstr = linebreak_paragraph(
                f"{arg.name}: {escape_backslash(arg.docstring) if arg.docstring else ''}",
                width=80 - (4 * 3) - 1,
                first_line_width=80 - (4 * 2) - 1,
            )
            arg_docstr = ensure_endswith("\\\n".join(arg_docstr), ".").split("\n")
            arg_docstr_buf.append(arg_docstr[0])
            arg_docstr_buf.extend(indent(arg_docstr[1:]))

        # Add docstring (Google style)

        if func.docstring_body:
            docstring_linebroken = linebreak_paragraph(escape_backslash(func.docstring_body), width=80 - 4)
        else:
            docstring_linebroken = [""]

        buf.extend(
            indent([
                '"""',
                *docstring_linebroken,
                "",
                "Args:",
                *indent(arg_docstr_buf),
                *(["Returns:", *indent([f"{escape_backslash(func.return_descr)}"])] if func.return_descr else []),
                '"""',
            ])
        )

        # Add function body
        if func.body:
            buf.extend(indent(func.body))
        else:
            buf.extend(indent(["pass"]))
        return buf

    def generate_data_class(self, data_class: GenericDataClass) -> LineBuffer:
        # Sort fields so default arguments come last
        data_class.fields.sort(key=lambda a: a.default is not None)

        def _arg_docstring(arg: GenericArg) -> LineBuffer:
            if not arg.docstring:
                return []
            return linebreak_paragraph(
                f'"""{escape_backslash(arg.docstring)}"""', width=80 - 4, first_line_width=80 - 4
            )

        args = concat([[self.generate_arg_declaration(f), *_arg_docstring(f)] for f in data_class.fields])
        methods = concat([self.generate_func(method) for method in data_class.methods], [""])

        buf = [
            "@dataclasses.dataclass",
            f"class {data_class.name}:",
            *indent([
                *(
                    [
                        '"""',
                        *linebreak_paragraph(
                            escape_backslash(data_class.docstring), width=80 - 4, first_line_width=80 - 4
                        ),
                        '"""',
                    ]
                    if data_class.docstring
                    else []
                ),
                *args,
                *blank_before(methods),
            ]),
        ]
        return buf

    def generate_named_tuple(self, data_class: GenericNamedTuple) -> LineBuffer:
        # Sort fields so default arguments come last
        data_class.fields.sort(key=lambda a: a.default is not None)

        def _arg_docstring(arg: GenericArg) -> LineBuffer:
            if not arg.docstring:
                return []
            return linebreak_paragraph(
                f'"""{escape_backslash(arg.docstring)}"""', width=80 - 4, first_line_width=80 - 4
            )

        args = concat([[self.generate_arg_declaration(f), *_arg_docstring(f)] for f in data_class.fields])
        methods = concat([self.generate_model(method) for method in data_class.methods], [""])

        buf = [
            f"class {data_class.name}(typing.NamedTuple):",
        ]
        if data_class.docstring:
            buf.extend(
                indent([
                    '"""',
                    f"{escape_backslash(data_class.docstring)}",
                    '"""',
                    *args,
                    *blank_before(methods),
                ])
            )
        return buf

    def generate_module(self, module: GenericModule) -> LineBuffer:
        exports = (
            [
                "__all__ = [",
                *indent(list(map(lambda x: f"{enquote(x)},", sorted(module.exports)))),
                "]",
            ]
            if module.exports
            else []
        )

        return blank_after([
            *(['"""', *linebreak_paragraph(escape_backslash(module.docstr)), '"""'] if module.docstr else []),
            *comment([
                "This file was auto generated by Styx.",
                "Do not edit this file directly.",
            ]),
            *blank_before(module.imports),
            *blank_before(module.header),
            *[line for func in module.funcs_and_classes for line in blank_before(self.generate_model(func), 2)],
            *blank_before(module.footer),
            *blank_before(exports, 2),
        ])

    def as_literal(self, obj: _TYPE_PYLITERAL) -> str:
        quote = '"'
        if isinstance(obj, bool):
            return "True" if obj else "False"
        if isinstance(obj, (int, float)):
            return str(obj)
        if obj is None:
            return "None"
        if isinstance(obj, str):
            return enquote(obj, quote)
        if isinstance(obj, pathlib.Path):
            return enquote(str(obj), quote)
        if isinstance(obj, list):
            return enbrace(", ".join([self.as_literal(o) for o in obj]), "[")
        if isinstance(obj, (tuple, set)):
            return enbrace(", ".join([self.as_literal(o) for o in obj]), "(")
        if isinstance(obj, dict):
            return enbrace(", ".join([f"{self.as_literal(k)}: {self.as_literal(v)}" for k, v in obj.items()]), "{")
        raise ValueError(f"Unsupported type: {type(obj)}")

    def as_literal_union_type(self, obj: list[_TYPE_PYLITERAL]) -> str:
        return f"typing.Literal[{', '.join(map(self.as_literal, obj))}]"

    def wrapper_module_imports(self) -> LineBuffer:
        return [
            "import typing",
            "import pathlib",
            "from styxdefs import *",
            "import dataclasses",
        ]

    def metadata_symbol(
        self,
        interface_base_name: str,
    ) -> str:
        return self.ensure_constant_case(f"{interface_base_name}_METADATA")

    def generate_metadata(
        self,
        metadata_symbol: str,
        entries: dict,
    ) -> LineBuffer:
        return [
            f"{metadata_symbol} = Metadata(",
            *indent([f"{k}={self.as_literal(v)}," for k, v in entries.items()]),
            ")",
        ]

    def type_symbol_as_list(self, symbol: str) -> str:
        return f"list[{symbol}]"

    def type_symbol_as_optional(self, symbol: str) -> str:
        return f"{symbol} | None"

    def type_symbols_as_union(self, symbol: list[str]) -> str:
        return f"typing.Union[{', '.join(symbol)}]"

    def param_type(self, param: ir.Param, lookup_struct_type: dict[ir.IdType, str]) -> str:
        def _base() -> str:
            if isinstance(param.body, ir.Param.String):
                if param.choices:
                    return self.as_literal_union_type(param.choices)  # type: ignore
                return "str"
            if isinstance(param.body, ir.Param.Int):
                if param.choices:
                    return self.as_literal_union_type(param.choices)  # type: ignore
                return "int"
            if isinstance(param.body, ir.Param.Float):
                return "float"
            if isinstance(param.body, ir.Param.File):
                return "InputPathType"
            if isinstance(param.body, ir.Param.Bool):
                return "bool"
            if isinstance(param.body, ir.Param.Struct):
                return lookup_struct_type[param.base.id_]
            if isinstance(param.body, ir.Param.StructUnion):
                return self.type_symbols_as_union([lookup_struct_type[i.base.id_] for i in param.body.alts])
            assert False

        type_ = _base()
        if param.list_:
            type_ = self.type_symbol_as_list(type_)
        if param.nullable:
            type_ = self.type_symbol_as_optional(type_)

        return type_

    def output_path_type(self) -> str:
        return "OutputPathType"

    def runner_type(
        self,
    ) -> str:
        return "Runner"

    def execution_type(
        self,
    ) -> str:
        return "Execution"

    def type_string_list(self) -> str:
        return "list[str]"

    def param_var_to_str(self, param: ir.Param, symbol: str) -> tuple[str, bool]:
        def _val() -> tuple[str, bool]:
            if not param.list_:
                if isinstance(param.body, ir.Param.String):
                    return symbol, False
                if isinstance(param.body, (ir.Param.Int, ir.Param.Float)):
                    return f"str({symbol})", False
                if isinstance(param.body, ir.Param.Bool):
                    as_list = (len(param.body.value_true) > 1) or (len(param.body.value_false) > 1)
                    if as_list:
                        value_true: str | list[str] | None = param.body.value_true
                        value_false: str | list[str] | None = param.body.value_false
                    else:
                        value_true = param.body.value_true[0] if len(param.body.value_true) > 0 else None
                        value_false = param.body.value_false[0] if len(param.body.value_false) > 0 else None
                    if len(param.body.value_true) > 0:
                        if len(param.body.value_false) > 0:
                            return (
                                f"({self.as_literal(value_true)} if {symbol} else {self.as_literal(value_true)})",
                                as_list,
                            )
                        return self.as_literal(value_true), as_list
                    assert len(param.body.value_false) > 0
                    return self.as_literal(value_false), as_list
                if isinstance(param.body, ir.Param.File):
                    extra_args = ""
                    if param.body.resolve_parent:
                        extra_args += ", resolve_parent=True"
                    if param.body.mutable:
                        extra_args += ", mutable=True"
                    return f"execution.input_file({symbol}{extra_args})", False
                if isinstance(param.body, (ir.Param.Struct, ir.Param.StructUnion)):
                    return f"{symbol}.run(execution)", True
                assert False

            if param.list_.join is None:
                if isinstance(param.body, ir.Param.String):
                    return symbol, True
                if isinstance(param.body, (ir.Param.Int, ir.Param.Float)):
                    return f"map(str, {symbol})", True
                if isinstance(param.body, ir.Param.Bool):
                    assert False, "TODO: Not implemented yet"
                if isinstance(param.body, ir.Param.File):
                    extra_args = ""
                    if param.body.resolve_parent:
                        extra_args += ", resolve_parent=True"
                    if param.body.mutable:
                        extra_args += ", mutable=True"
                    return f"[execution.input_file(f{extra_args}) for f in {symbol}]", True
                if isinstance(param.body, (ir.Param.Struct, ir.Param.StructUnion)):
                    return f"[a for c in [s.run(execution) for s in {symbol}] for a in c]", True
                assert False

            # arg.data.list_separator is not None
            sep_join = f"{enquote(param.list_.join)}.join"
            if isinstance(param.body, ir.Param.String):
                return f"{sep_join}({symbol})", False
            if isinstance(param.body, (ir.Param.Int, ir.Param.Float)):
                return f"{sep_join}(map(str, {symbol}))", False
            if isinstance(param.body, ir.Param.Bool):
                assert False, "TODO: Not implemented yet"
            if isinstance(param.body, ir.Param.File):
                extra_args = ""
                if param.body.resolve_parent:
                    extra_args += ", resolve_parent=True"
                if param.body.mutable:
                    extra_args += ", mutable=True"
                return f"{sep_join}([execution.input_file(f{extra_args}) for f in {symbol}])", False
            if isinstance(param.body, (ir.Param.Struct, ir.Param.StructUnion)):
                return f"{sep_join}([a for c in [s.run(execution) for s in {symbol}] for a in c])", False
            assert False

        return _val()

    def param_default_value(self, param: ir.Param) -> str | None:
        if param.default_value is ir.Param.SetToNone:
            return "None"
        if param.default_value is None:
            return None
        return self.as_literal(param.default_value)  # type: ignore

    def param_var_is_set_by_user(self, param: ir.Param, symbol: str, enbrace_statement: bool = False) -> str | None:
        if param.nullable:
            if enbrace_statement:
                return f"({symbol} is not None)"
            return f"{symbol} is not None"

        if isinstance(param.body, ir.Param.Bool):
            if len(param.body.value_true) > 0 and len(param.body.value_false) == 0:
                return symbol
            if len(param.body.value_false) > 0 and len(param.body.value_true) == 0:
                if enbrace_statement:
                    return f"(not {symbol})"
                return f"not {symbol}"
        return None

    def remove_suffixes(self, str_expr: str, suffixes: list[str]) -> str:
        substitute = str_expr
        for suffix in suffixes:
            substitute += f".removesuffix({self.as_literal(suffix)})"
        return substitute

    def path_expr_get_filename(self, path_expr: str) -> str:
        return f"pathlib.Path({path_expr}).name"

    def self_access(self, attribute: str) -> str:
        return "self"

    def member_access(self, attribute: str) -> str:
        return f"self.{attribute}"

    def conditions_join_and(self, condition_exprs: list[str]) -> str:
        return " and ".join(condition_exprs)

    def conditions_join_or(self, condition_exprs: list[str]) -> str:
        return " or ".join(condition_exprs)

    def join_string_list_expr(self, expr: str, join: str = "") -> str:
        join = join.replace('"', '\\"')
        return f'"{join}".join({expr})'

    def concat_strings(self, exprs: list[str]) -> str:
        return " + ".join(exprs)

    def ternary(self, condition: str, truthy: str, falsy: str, enbrace_: bool = False) -> str:
        if " " in condition:
            condition = enbrace(condition, "(")
        ret = f"{truthy} if {condition} else {falsy}"
        if enbrace_:
            return enbrace(ret, "(")
        return ret

    def return_statement(self, value: str) -> str:
        return f"return {value}"

    def cargs_symbol(self) -> str:
        return "cargs"

    def cargs_declare(self, cargs_symbol: str) -> LineBuffer:
        return [f"{cargs_symbol} = []"]

    def cargs_add_0d(self, cargs_symbol: str, val: str | list[str]) -> LineBuffer:
        if isinstance(val, list):
            return [
                "cargs.extend([",
                *indent(expand(",\n".join(val))),
                "])",
            ]
        return [f"{cargs_symbol}.append({val})"]

    def cargs_add_1d(self, cargs_symbol: str, val: str | list[str]) -> LineBuffer:
        if isinstance(val, list):
            return [
                "cargs.extend([",
                *indent(expand(",\n".join(f"*{v}" for v in val))),
                "])",
            ]
        return [f"{cargs_symbol}.extend({val})"]

    def empty_str(self) -> str:
        return '""'

    def empty_str_list(self) -> str:
        return "[]"

    def if_else_block(self, condition: str, truthy: LineBuffer, falsy: LineBuffer | None = None) -> LineBuffer:
        buf = [
            f"if {condition}:",
            *indent(truthy),
        ]
        if falsy:
            buf.extend([
                "else:",
                *indent(falsy),
            ])
        return buf

    def generate_ret_object_creation(
        self,
        buf: LineBuffer,
        execution_symbol: str,
        output_type: str,
        members: dict[str, str],
    ) -> LineBuffer:
        buf.append(f"ret = {output_type}(")

        # Set root output path
        buf.extend(indent([f'root={execution_symbol}.output_file("."),']))

        for member_symbol, member_expr in members.items():
            buf.extend(indent([f"{member_symbol}={member_expr},"]))

        buf.extend([")"])

        return buf

    def resolve_output_file(self, execution_symbol: str, file_expr: str) -> str:
        return f"{execution_symbol}.output_file({file_expr})"
