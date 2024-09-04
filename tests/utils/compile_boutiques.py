from styx.backend.python.core import to_python
from styx.frontend.boutiques.core import from_boutiques


def boutiques2python(boutiques: dict, package: str = "no_package") -> str:
    return to_python([from_boutiques(boutiques, package)]).__next__()[0]
