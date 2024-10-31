from styx.backend.generic.core import compile_language
from styx.backend.python.languageprovider import PythonLanguageProvider
from styx.frontend.boutiques import from_boutiques


def boutiques2python(boutiques: dict, package: str = "no_package") -> str:
    ir = from_boutiques(boutiques, package)
    py = compile_language(PythonLanguageProvider(), [ir]).__next__()[0]
    return py
