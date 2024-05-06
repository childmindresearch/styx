from styx.compiler.compile.descriptor import compile_descriptor
from styx.compiler.settings import CompilerSettings
from styx.model.from_boutiques import descriptor_from_boutiques  # type: ignore


def compile_boutiques_dict(boutiques_descriptor: dict, settings: CompilerSettings) -> str:
    descriptor = descriptor_from_boutiques(boutiques_descriptor)
    return compile_descriptor(descriptor, settings)
