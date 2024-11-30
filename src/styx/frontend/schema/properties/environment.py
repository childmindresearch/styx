from typing import Annotated, Optional

import pydantic


class EnvironmentVariable(pydantic.BaseModel):
    """Model for environment variables."""

    name: Annotated[
        str,
        pydantic.StringConstraints(pattern=r"^[a-zA-Z][0-9_a-zA-Z]*$", min_length=1),
    ] = pydantic.Field(
        description='The environment variable name (identifier) containing only alphanumeric characters and underscores. Example: "PROGRAM_PATH".',
    )
    value: str = pydantic.Field(description="The value of the environment variable.")
    description: Optional[str] = pydantic.Field(
        description="Description of the environment variable.", default=None
    )
