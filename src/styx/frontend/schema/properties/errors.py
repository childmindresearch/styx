import pydantic


class ErrorCode(pydantic.BaseModel):
    """Model for error codes."""

    code: int = pydantic.Field(description="Value of the exit code")
    description: str = pydantic.Field(description="Description of the error code.")
