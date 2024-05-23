"""Generate __init__.py that re-exports __all__ from all submodules."""

from styx.pycodegen.core import PyModule


def generate_reexport_module(relative_imports: list[str]) -> str:
    """Generate __init__.py that re-exports __all__ from all submodules."""
    module: PyModule = PyModule()
    module.imports = list(map(lambda item: f"from .{item} import *", sorted(relative_imports)))
    return module.text()
