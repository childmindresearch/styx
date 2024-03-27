from styx.compiler.settings import CompilerSettings, DefsMode
from styx.pycodegen.core import PyModule


def compile_definitions() -> str:
    """Compile the definitions to Python code."""
    import styx.runners.styxdefs

    defs_file = styx.runners.styxdefs.__file__
    with open(defs_file, "r") as f:
        return f.read()


def generate_definitions(module: PyModule, settings: CompilerSettings) -> None:
    """Generate the definition code in the header."""
    if settings.defs_mode == DefsMode.INLINE:
        module.header.append(compile_definitions())
    elif settings.defs_mode == DefsMode.IMPORT:
        defs_module_path = "styx.runners.styxdefs" if settings.defs_module_path is None else settings.defs_module_path
        module.header.append(f"from {defs_module_path} import *")
