import pathlib
import typing
from abc import ABC
from typing import Mapping, Sequence, TypeAlias

import styx.ir.core as ir
from styx.backend.generic.linebuffer import LineBuffer
from styx.backend.generic.model import GenericArg, GenericDataClass, GenericFunc, GenericModule, GenericNamedTuple

if typing.TYPE_CHECKING:
    from styx.backend.generic.scope import Scope
else:
    Scope = None

_TYPE_PYPRIMITIVE: TypeAlias = str | float | int | bool | pathlib.Path | None
_TYPE_PYLITERAL: TypeAlias = _TYPE_PYPRIMITIVE | Sequence["_TYPE_PYLITERAL"] | Mapping[str, "_TYPE_PYLITERAL"]


class LanguageProvider(ABC):
    def legal_symbol(self, symbol: str) -> bool:
        """Is a given string a legal symbol in this language."""
        return NotImplemented

    def language_scope(self) -> Scope:
        """Build a scope with all the global keywords, reserved symbols, etc.

        (Basically everything we never want to shadow).
        """
        return NotImplemented

    def ensure_symbol(self, name: str) -> str:
        """Convert an arbitrary name to a similar-looking legal symbol."""
        return NotImplemented

    def ensure_constant_case(self, name: str) -> str:
        """Convert an arbitrary name to a similar-looking legal symbol.

        which is in the usual case style of a constant.
        """
        return NotImplemented

    def ensure_class_case(self, name: str) -> str:
        """Convert an arbitrary name to a similar-looking legal symbol.

        which is in the usual case style of a class name.
        """
        return NotImplemented

    def ensure_var_case(self, name: str) -> str:
        """Convert an arbitrary name to a similar-looking legal symbol.

        which is in the usual case style of a variable.
        """
        return NotImplemented

    def generate_arg_declaration(self, arg: GenericArg) -> str:
        """Argument declaration."""
        return NotImplemented

    def generate_func(self, func: GenericFunc) -> LineBuffer:
        """Generate function."""
        return NotImplemented

    def generate_data_class(self, data_class: GenericDataClass) -> LineBuffer:
        """Generate data class (fields and methods)."""
        return NotImplemented

    def generate_named_tuple(self, data_class: GenericNamedTuple) -> LineBuffer:
        """Generate named tuple (only fields, immutable)."""
        return NotImplemented

    def generate_module(self, module: GenericModule) -> LineBuffer:
        """Generate module."""
        return NotImplemented

    def generate_model(self, m: GenericFunc | GenericDataClass | GenericNamedTuple) -> LineBuffer:
        if isinstance(m, GenericFunc):
            return self.generate_func(m)
        if isinstance(m, GenericDataClass):
            return self.generate_data_class(m)
        if isinstance(m, GenericNamedTuple):
            return self.generate_named_tuple(m)
        assert False

    def as_literal(self, obj: _TYPE_PYLITERAL) -> str:
        """Convert an object to a language literal expression."""
        return NotImplemented

    def as_literal_union_type(self, obj: list[_TYPE_PYLITERAL]) -> str:
        """Convert an object to a language literal union type."""
        return NotImplemented

    def wrapper_module_imports(self) -> LineBuffer:
        """List of imports each wrapper module should have."""
        return NotImplemented

    def metadata_symbol(
        self,
        interface_base_name: str,
    ) -> str:
        """Symbol the metadata constant should get."""
        return NotImplemented

    def generate_metadata(
        self,
        metadata_symbol: str,
        entries: dict,
    ) -> LineBuffer:
        """Generate the metadata definition."""
        return NotImplemented

    def type_symbol_as_list(self, symbol: str) -> str:
        """Convert a type symbol to a type of list of that type."""
        return NotImplemented

    def type_symbol_as_optional(self, symbol: str) -> str:
        """Convert a type symbol to an optional of that type."""
        return NotImplemented

    def type_symbols_as_union(self, symbol: list[str]) -> str:
        """Convert a collection of type symbol to a union type of them."""
        return NotImplemented

    def param_type(self, param: ir.Param, lookup_struct_type: dict[ir.IdType, str]) -> str:
        """Return the Python type expression for a param.

        Args:
            param: The param.
            lookup_struct_type: lookup dictionary for struct types (pre-compute).

        Returns:
            Language type expression.
        """
        return NotImplemented

    def output_path_type(
        self,
    ) -> str:
        """Type of output path."""
        return NotImplemented

    def runner_type(
        self,
    ) -> str:
        """Type of Runner."""
        return NotImplemented

    def execution_type(
        self,
    ) -> str:
        """Type of Execution."""
        return NotImplemented

    def type_string_list(self) -> str:
        """Type of string list. (e.g. for cargs)."""
        return NotImplemented

    def param_var_to_str(
        self,
        param: ir.Param,
        symbol: str,
    ) -> tuple[str, bool]:
        """Language var to str.

        Return a language expression that converts the variable to a string or string array
        and a boolean that indicates if the expression value is an array.
        """
        return NotImplemented

    def param_default_value(self, param: ir.Param) -> str | None:
        """Default value language literal if param has default value else None."""
        return NotImplemented

    def param_var_is_set_by_user(
        self,
        param: ir.Param,
        symbol: str,
        enbrace_statement: bool = False,
    ) -> str | None:
        """Return a language expression that checks if the variable is set by the user.

        Returns `None` if the param must always be specified.
        """
        return NotImplemented

    def remove_suffixes(
        self,
        str_expr: str,
        suffixes: list[str],
    ) -> str:
        """String expression which removes all given suffixes from a string expression."""
        return NotImplemented

    def path_expr_get_filename(
        self,
        path_expr: str,
    ) -> str:
        """Extract filename from path expression."""
        return NotImplemented

    def numeric_to_str(
        self,
        numeric_expr: str,
    ) -> str:
        """Numeric (float or int) expression to str expression."""
        return NotImplemented

    def self_access(self, attribute: str) -> str:
        """Access self/this/..."""
        return NotImplemented

    def member_access(
        self,
        attribute: str,
    ) -> str:
        """Access class member. (self. / this. / ...)."""
        return NotImplemented

    def conditions_join_and(
        self,
        condition_exprs: list[str],
    ) -> str:
        """Join conditions via logical AND."""
        return NotImplemented

    def conditions_join_or(
        self,
        condition_exprs: list[str],
    ) -> str:
        """Join conditions via logical OR."""
        return NotImplemented

    def join_string_list_expr(self, expr: str, join: str = "") -> str:
        """Join/collapse a string list_expression."""
        return NotImplemented

    def concat_strings(self, exprs: list[str]) -> str:
        """Concatenate string expressions."""
        return NotImplemented

    def ternary(self, condition: str, truthy: str, falsy: str, enbrace_: bool = False) -> str:
        """Ternary expression."""
        return NotImplemented

    def return_statement(self, value: str) -> str:
        """(Possibly early) return statement."""
        return NotImplemented

    def cargs_symbol(self) -> str:
        """Construct command line args list."""
        return NotImplemented

    def cargs_declare(self, cargs_symbol: str) -> LineBuffer:
        """Construct command line args list."""
        return NotImplemented

    def cargs_add_0d(self, cargs_symbol: str, val: str | list[str]) -> LineBuffer:
        """Add one entry that is a string expression or multiple string expressions."""
        return NotImplemented

    def cargs_add_1d(self, cargs_symbol: str, val: str | list[str]) -> LineBuffer:
        """Add one entry that is a string-list expression or multiple string-list expressions."""
        return NotImplemented

    def cargs_0d_or_1d_to_0d(self, val_and_islist: list[tuple[str, bool]]) -> list[str]:
        """Convert a list of 0d or 1d carg expressions to a list of 0d."""
        return NotImplemented

    def empty_str(self) -> str:
        """Empty string expression."""
        return NotImplemented

    def empty_str_list(self) -> str:
        """Empty string list expression."""
        return NotImplemented

    def runner_symbol(self) -> str:
        """Construct command line args list."""
        return NotImplemented

    def runner_declare(self, runner_symbol: str) -> LineBuffer:
        """Construct command line args list."""
        return NotImplemented

    def execution_symbol(self) -> str:
        """Construct command line args list."""
        return NotImplemented

    def execution_declare(self, execution_symbol: str, metadata_symbol: str) -> LineBuffer:
        """Construct command line args list."""
        return NotImplemented

    def execution_run(self, execution_symbol: str, cargs_symbol: str) -> LineBuffer:
        """Start execution."""
        return NotImplemented

    def null(self) -> str:
        """Null value."""
        return NotImplemented

    def if_else_block(self, condition: str, truthy: LineBuffer, falsy: LineBuffer | None = None) -> LineBuffer:
        """If/else block."""
        return NotImplemented

    def generate_ret_object_creation(
        self,
        buf: LineBuffer,
        execution_symbol: str,
        output_type: str,
        members: dict[str, str],
    ) -> LineBuffer:
        """Generate return tuple object."""
        return NotImplemented

    def resolve_output_file(self, execution_symbol: str, file_expr: str) -> str:
        """Resolve output file."""
        return NotImplemented

    def struct_collect_outputs(self, struct: ir.Param[ir.Param.Struct], struct_symbol: str) -> str:
        """Collect outputs for a sub-struct."""
        return NotImplemented

    @classmethod
    def styxdefs_compat(cls) -> str:
        """Return what version of styxdefs generated wrappers will be compatible with."""
        return "^0.3.0"
