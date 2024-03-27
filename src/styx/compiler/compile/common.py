from dataclasses import dataclass

from styx.pycodegen.scope import Scope


@dataclass
class SharedScopes:
    module: Scope
    function: Scope
    output_tuple: Scope


@dataclass
class SharedSymbols:
    function: str
    output_class: str
    metadata: str
    runner: str
    execution: str
    cargs: str
    ret: str
