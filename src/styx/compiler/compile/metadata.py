from styx.compiler.compile.common import SharedSymbols
from styx.model.core import Descriptor
from styx.pycodegen.core import PyModule, indent
from styx.pycodegen.utils import as_py_literal


def generate_static_metadata(
    module: PyModule,
    descriptor: Descriptor,
    symbols: SharedSymbols,
) -> None:
    """Generate the static metadata."""
    module.header.extend([
        f"{symbols.metadata} = Metadata(",
        *indent([f"{k}={as_py_literal(v)}," for k, v in descriptor.metadata.items()]),
        ")",
    ])
