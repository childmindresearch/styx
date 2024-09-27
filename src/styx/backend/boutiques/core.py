import re
from collections.abc import Callable

import styx.ir.core as ir


def shlex_join(split_command):
    """Return a shell-escaped string from *split_command*."""
    return " ".join(shlex_quote(arg) for arg in split_command)


_shlex_find_unsafe = re.compile(r"[^\w@%+=:,./-\[\]]", re.ASCII).search


def shlex_quote(s):
    """Return a shell-escaped version of the string *s*."""
    if not s:
        return "''"
    if _shlex_find_unsafe(s) is None:
        return s

    # use single quotes, and put single quotes into double quotes
    # the string $'b is then quoted as '$'"'"'b'
    return "'" + s.replace("'", "'\"'\"'") + "'"


def _as_value_key(s: str) -> str:
    return f"[{re.sub(r"\W", "_", s).upper()}]"


def _carg_format(carg: ir.Carg, resolve: Callable[[ir.Param], str]) -> str:
    re = ""
    for token in carg.tokens:
        if isinstance(token, str):
            re += token
            continue
        re += resolve(token)
    return re


def _never(*_args, **_kwargs) -> None:
    assert False


def _carg_is_const(carg: ir.Carg) -> bool:
    for token in carg.tokens:
        if isinstance(token, ir.Param):
            return False
    return True


def _struct_to_boutiques(
    struct: ir.Param[ir.Param.Struct], bt: dict, lookup: dict[int, ir.Param], is_root=True
) -> dict:
    if is_root:
        bt["name"] = struct.base.name
    else:
        bt["id"] = struct.base.name
        if struct.base.docs.title:
            bt["name"] = struct.base.docs.title
    if struct.base.docs.description:
        bt["description"] = struct.base.docs.description
    if struct.base.docs.authors:
        bt["author"] = " AND ".join(struct.base.docs.authors)
    if struct.base.docs.urls:
        bt["url"] = struct.base.docs.urls[0]

    bt["command-line"] = None  # Ensure entry is before inputs/outputs (ordered dict)
    bt["inputs"] = inputs = []

    def _resolve_param_with_flag(flag: str | None):
        def _resolve_param(param: ir.Param):
            value_key = _as_value_key(param.base.name)
            input_: dict = {
                "id": param.base.name,
                "value-key": value_key,
            }
            if param.base.docs.title:
                input_["name"] = param.base.docs.title
            if param.base.docs.description:
                input_["description"] = param.base.docs.description

            if param.list_ is not None:
                input_["list"] = True
            if param.nullable:
                input_["optional"] = True
            if param.choices:
                input_["choices"] = param.choices
            if param.default_value is not None and param.default_value is not ir.Param.SetToNone:
                input_["default-value"] = param.default_value

            if isinstance(param.body, (ir.Param.Int, ir.Param.Float)):
                input_["type"] = "Number"
                if isinstance(param.body, ir.Param.Int):
                    input_["integer"] = True
                if param.body.min_value:
                    input_["minimum"] = param.body.min_value
                if param.body.max_value:
                    input_["maximum"] = param.body.max_value
            elif isinstance(param.body, ir.Param.String):
                input_["type"] = "String"
            elif isinstance(param.body, ir.Param.File):
                input_["type"] = "File"
            elif isinstance(param.body, ir.Param.Bool):
                assert len(param.body.value_true) == 1
                assert len(param.body.value_false) == 0
                input_["type"] = "Flag"
                input_["command-line-flag"] = param.body.value_true[0]
                input_["optional"] = True
                if "default-value" in input_:
                    del input_["default-value"]
            elif isinstance(param.body, ir.Param.Struct):
                input_["type"] = bt_sub = {}
                _struct_to_boutiques(param, bt_sub, lookup, False)
            elif isinstance(param.body, ir.Param.StructUnion):
                input_["type"] = bt_alts = []
                for alt in param.body.alts:
                    bt_sub = {}
                    bt_alts.append(bt_sub)
                    _struct_to_boutiques(alt, bt_sub, lookup, False)

            if flag is not None:
                input_["command-line-flag"] = flag

            inputs.append(input_)
            return value_key

        return _resolve_param

    cargs_formatted = []
    for group in struct.body.groups:
        if len(group.cargs) == 2:
            if _carg_is_const(group.cargs[0]) and not _carg_is_const(group.cargs[1]):
                flag_formatted = _carg_format(group.cargs[0], _never)
                cargs_formatted.append(_carg_format(group.cargs[1], _resolve_param_with_flag(flag_formatted)))
                continue

        for carg in group.cargs:
            cargs_formatted.append(_carg_format(carg, _resolve_param_with_flag(None)))

    if cargs_formatted:
        bt["command-line"] = shlex_join(cargs_formatted)

    bt_outputs = []

    for output in struct.base.outputs:
        bt_output = {
            "id": output.name,
        }
        if output.docs.title:
            bt_output["name"] = output.docs.title
        if output.docs.description:
            bt_output["description"] = output.docs.description

        output_path_formatted = ""
        stripped_extensions = []
        for token in output.tokens:
            if isinstance(token, str):
                output_path_formatted += token
                continue
            if token.file_remove_suffixes:
                stripped_extensions.extend(token.file_remove_suffixes)
            param = lookup[token.ref_id]
            output_path_formatted += _as_value_key(param.base.name)

        bt_output["path-template"] = output_path_formatted
        if stripped_extensions:
            bt_output["path-template-stripped-extensions"] = stripped_extensions

        bt_outputs.append(bt_output)

    if bt_outputs:
        bt["output-files"] = bt_outputs

    return bt


def to_boutiques(interface: ir.Interface) -> dict:
    bt: dict = {
        "schema-version": "0.5",
        "tool-version": interface.package.version,
    }

    if interface.package.docker:
        bt["container-image"] = {
            "image": interface.package.docker,
            "type": "docker",
        }

    lookup = {param.base.id_: param for param in interface.command.iter_params_recursively(False)}
    for k, v in lookup.items():
        print(k, v)

    _struct_to_boutiques(interface.command, bt, lookup)

    return bt
