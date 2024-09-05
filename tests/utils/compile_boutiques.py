from styx.backend.python import to_python
from styx.frontend.boutiques import from_boutiques


def boutiques2python(boutiques: dict, package: str = "no_package") -> str:
    ir = from_boutiques(boutiques, package)
    py = to_python([ir]).__next__()[0]
    return py
