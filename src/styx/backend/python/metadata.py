from styx.backend.python.pycodegen.core import PyModule, indent
from styx.backend.python.pycodegen.scope import Scope
from styx.backend.python.pycodegen.utils import as_py_literal, python_screaming_snakify
from styx.ir.core import Interface


def generate_static_metadata(
    module: PyModule,
    scope: Scope,
    interface: Interface,
) -> str:
    """Generate the static metadata."""
    metadata_symbol = scope.add_or_dodge(f"{python_screaming_snakify(interface.command.base.name)}_METADATA")

    entries: dict = {
        "id": interface.uid,
        "name": interface.command.base.name,
        "package": interface.package.name,
    }

    if interface.command.base.docs.literature:
        entries["citations"] = interface.command.base.docs.literature

    if interface.package.docker:
        entries["container_image_tag"] = interface.package.docker

    module.header.extend([
        f"{metadata_symbol} = Metadata(",
        *indent([f"{k}={as_py_literal(v)}," for k, v in entries.items()]),
        ")",
    ])

    return metadata_symbol
