from styx.pycodegen.core import PyModule


def generate_definitions(module: PyModule) -> None:
    """Generate the definition code in the header."""
    module.header.append("from styxdefs import *")
