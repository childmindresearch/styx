import styx.ir.core as ir
from styx.backend.python.pycodegen.scope import Scope
from styx.backend.python.pycodegen.utils import python_pascalize, python_snakify
from styx.backend.python.utils import iter_params_recursively, param_py_type


class LookupParam:
    """Pre-compute and store Python symbols, types, class-names, etc. to reduce spaghetti code everywhere else."""

    def __init__(
        self,
        interface: ir.Interface,
        package_scope: Scope,
        function_symbol: str,
        function_scope: Scope,
    ) -> None:
        def _collect_output_field_symbols(
            param: ir.IStruct | ir.IParam, lookup_output_field_symbol: dict[ir.IdType, str]
        ) -> None:
            scope = Scope(parent=package_scope)
            scope.add_or_die("root")
            for output in param.param.outputs:
                output_field_symbol = scope.add_or_dodge(python_snakify(output.name))
                assert output.id_ not in lookup_output_field_symbol
                lookup_output_field_symbol[output.id_] = output_field_symbol

            for sub_struct in param.struct.iter_params():
                if isinstance(sub_struct, (ir.IStruct, ir.IStructUnion)):
                    output_field_symbol = scope.add_or_dodge(python_snakify(sub_struct.param.name))
                    assert sub_struct.param.id_ not in lookup_output_field_symbol
                    lookup_output_field_symbol[sub_struct.param.id_] = output_field_symbol

        def _collect_py_symbol(param: ir.IStruct | ir.IParam, lookup_py_symbol: dict[ir.IdType, str]) -> None:
            scope = Scope(parent=function_scope)
            for elem in param.struct.iter_params():
                symbol = scope.add_or_dodge(python_snakify(elem.param.name))
                assert elem.param.id_ not in lookup_py_symbol
                lookup_py_symbol[elem.param.id_] = symbol

        self.param: dict[ir.IdType, ir.IParam] = {interface.command.param.id_: interface.command}
        """Find param object by its ID. IParam.id_ -> IParam"""
        self.py_struct_type: dict[ir.IdType, str] = {interface.command.param.id_: function_symbol}
        """Find Python struct type by param id. IParam.id_ -> Python type
        (this is different from py_type because of optionals and lists)"""
        self.py_type: dict[ir.IdType, str] = {interface.command.param.id_: function_symbol}
        """Find Python type by param id. IParam.id_ -> Python type"""
        self.py_symbol: dict[ir.IdType, str] = {}
        """Find function-parameter symbol by param ID. IParam.id_ -> Python symbol"""
        self.py_output_type: dict[ir.IdType, str] = {
            interface.command.param.id_: package_scope.add_or_dodge(
                python_pascalize(f"{interface.command.struct.name}_Outputs")
            )
        }
        """Find outputs class name by struct param ID. IStruct.id_ -> Python class name"""
        self.py_output_field_symbol: dict[ir.IdType, str] = {}
        """Find output field symbol by output ID. Output.id_ -> Python symbol"""

        _collect_py_symbol(
            param=interface.command,
            lookup_py_symbol=self.py_symbol,
        )
        _collect_output_field_symbols(
            param=interface.command,
            lookup_output_field_symbol=self.py_output_field_symbol,
        )

        for elem in iter_params_recursively(interface.command):
            self.param[elem.param.id_] = elem

            if isinstance(elem, ir.IStruct):
                if elem.param.id_ not in self.py_struct_type:  # Struct unions may resolve these first
                    self.py_struct_type[elem.param.id_] = package_scope.add_or_dodge(
                        python_pascalize(f"{interface.command.struct.name}_{elem.struct.name}")
                    )
                    self.py_type[elem.param.id_] = param_py_type(elem, self.py_struct_type)
                self.py_output_type[elem.param.id_] = package_scope.add_or_dodge(
                    python_pascalize(f"{interface.command.struct.name}_{elem.struct.name}_Outputs")
                )
                _collect_py_symbol(
                    param=elem,
                    lookup_py_symbol=self.py_symbol,
                )
                _collect_output_field_symbols(
                    param=elem,
                    lookup_output_field_symbol=self.py_output_field_symbol,
                )
            elif isinstance(elem, ir.IStructUnion):
                for alternative in elem.alts:
                    self.py_struct_type[alternative.param.id_] = package_scope.add_or_dodge(
                        python_pascalize(f"{interface.command.struct.name}_{alternative.struct.name}")
                    )
                    self.py_type[alternative.param.id_] = param_py_type(alternative, self.py_struct_type)
                self.py_type[elem.param.id_] = param_py_type(elem, self.py_struct_type)
            else:
                self.py_type[elem.param.id_] = param_py_type(elem, self.py_struct_type)
