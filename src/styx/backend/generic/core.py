import dataclasses
from typing import Any, Generator, Iterable

from styx.backend.generic.documentation import docs_to_docstring
from styx.backend.generic.gen.interface import compile_interface
from styx.backend.generic.languageprovider import LanguageProvider
from styx.backend.generic.linebuffer import collapse
from styx.backend.generic.model import GenericModule
from styx.backend.generic.scope import Scope
from styx.ir.core import Interface, Package


@dataclasses.dataclass
class _PackageData:
    package: Package
    package_symbol: str
    scope: Scope
    module: GenericModule


def compile_language(
    lang: LanguageProvider, interfaces: Iterable[Interface]
) -> Generator[tuple[str, list[str]], Any, None]:
    """For a stream of IR interfaces return a stream of Python modules and their module paths.

    Args:
        lang: Language provider.
        interfaces: Stream of IR interfaces.

    Returns:
        Stream of tuples (Python module, module path).
    """
    packages: dict[str, _PackageData] = {}
    global_scope = lang.language_scope()

    for interface in interfaces:
        if interface.package.name not in packages:
            packages[interface.package.name] = _PackageData(
                package=interface.package,
                package_symbol=global_scope.add_or_dodge(lang.ensure_var_case(interface.package.name)),
                scope=Scope(parent=global_scope),
                module=GenericModule(
                    docstr=docs_to_docstring(interface.package.docs),
                ),
            )
        package_data = packages[interface.package.name]

        # interface_module_symbol = global_scope.add_or_dodge(python_snakify(interface.command.param.name))
        interface_module_symbol = lang.ensure_var_case(interface.command.base.name)

        interface_module: GenericModule = GenericModule()
        compile_interface(
            lang=lang, interface=interface, package_scope=package_data.scope, interface_module=interface_module
        )
        package_data.module.imports.append(f"from .{interface_module_symbol} import *")
        yield collapse(lang.generate_module(interface_module)), [package_data.package_symbol, interface_module_symbol]

    for package_data in packages.values():
        package_data.module.imports.sort()
        yield collapse(lang.generate_module(package_data.module)), [package_data.package_symbol, "__init__"]
