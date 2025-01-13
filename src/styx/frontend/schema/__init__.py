from typing import Annotated

from pydantic import StringConstraints

StringProperty = Annotated[str, StringConstraints(min_length=1)]

__all__ = ["StringProperty"]
