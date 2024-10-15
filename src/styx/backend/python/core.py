import dataclasses
from typing import Any, Generator, Iterable

from styx.backend.python.documentation import docs_to_docstring
from styx.backend.python.interface import compile_interface
from styx.backend.python.pycodegen.core import PyModule
from styx.backend.python.pycodegen.scope import Scope
from styx.backend.python.pycodegen.utils import python_snakify
from styx.ir.core import Interface, Package


@dataclasses.dataclass
class _PackageData:
    package: Package
    package_symbol: str
    scope: Scope
    module: PyModule


def to_python(interfaces: Iterable[Interface]) -> Generator[tuple[str, list[str]], Any, None]:
    """For a stream of IR interfaces return a stream of Python modules and their module paths.

    Args:
        interfaces: Stream of IR interfaces.

    Returns:
        Stream of tuples (Python module, module path).
    """
    packages: dict[str, _PackageData] = {}
    global_scope = Scope(parent=Scope.python())

    for interface in interfaces:
        if interface.package.name not in packages:
            packages[interface.package.name] = _PackageData(
                package=interface.package,
                package_symbol=global_scope.add_or_dodge(python_snakify(interface.package.name)),
                scope=Scope(parent=global_scope),
                module=PyModule(
                    docstr=docs_to_docstring(interface.package.docs),
                ),
            )
        package_data = packages[interface.package.name]

        # interface_module_symbol = global_scope.add_or_dodge(python_snakify(interface.command.param.name))
        interface_module_symbol = python_snakify(interface.command.base.name)

        interface_module = PyModule()
        compile_interface(interface=interface, package_scope=package_data.scope, interface_module=interface_module)
        package_data.module.imports.append(f"from .{interface_module_symbol} import *")
        yield interface_module.text(), [package_data.package_symbol, interface_module_symbol]

    for package_data in packages.values():
        package_data.module.imports.sort()
        yield package_data.module.text(), [package_data.package_symbol, "__init__"]


def styxdefs_compat() -> str:
    """Return what version of styxdefs generated wrappers will be compatible with."""
    return "^0.3.0"
