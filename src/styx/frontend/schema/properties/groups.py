from typing import Annotated, Optional

import pydantic

from .. import StringProperty


class Group(pydantic.BaseModel):
    id: Annotated[
        str, pydantic.StringConstraints(pattern=r"^[0-9,_,a-z,A-Z]*$", min_length=1)
    ] = pydantic.Field(
        description='A short, unique, informative identifier containing only alphanumeric characters and underscores. Typically used to generate variable names. Example: "outfile_group".',
    )
    name: StringProperty = pydantic.Field(
        description="A human-readable name for the input group."
    )
    description: Optional[str] = pydantic.Field(
        description="Description of the input group.", default=None
    )
    members: list[
        Annotated[str, pydantic.StringConstraints(pattern=r"^[0-9,_,a-z,A-Z]*$")]
    ] = pydantic.Field(description="IDs of the inputs belonging to this group.")
    mutually_exclusive: bool = pydantic.Field(
        alias="mutually-exclusive",
        description="True if only one input in the group may be active at runtime.",
        default=False,
    )
    one_is_required: bool = pydantic.Field(
        alias="one-is-required",
        description="True if at least one of the inputs in the group must be active at runtime.",
        default=False,
    )
    all_or_one: bool = pydantic.Field(
        alias="all-or-none",
        description="True if members of the group need to be toggled together",
        default=False,
    )
