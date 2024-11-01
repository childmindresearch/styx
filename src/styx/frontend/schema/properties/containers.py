from typing import Literal, Optional, Self

import pydantic

from .. import StringProperty


class ContainerImage(pydantic.BaseModel):
    """Model for container image configuration."""

    type_: Literal["docker", "singularity", "rootfs"] = pydantic.Field(alias="type")
    image: Optional[StringProperty] = pydantic.Field(
        description="Name of an image where the tool is installed and configured. Example: bids/mriqc.",
        default=None,
    )
    url: Optional[StringProperty] = pydantic.Field(
        description="URL where the image is available.", default=None
    )
    working_directory: Optional[StringProperty] = pydantic.Field(
        alias="working-directory",
        description="Location from which this task must be launched within the container.",
        default=None,
    )
    container_hash: Optional[StringProperty] = pydantic.Field(
        alias="container-hash",
        description="Hash for the given container.",
        default=None,
    )
    entrypoint: bool = pydantic.Field(
        description="Flag indicating whether or not the container uses an entrypoint.",
        default=False,
    )
    index: Optional[StringProperty] = pydantic.Field(
        description="Optional index where the image is available, if not the standard location. Example: docker.io",
        default=None,
    )
    container_opts: Optional[list[str]] = pydantic.Field(
        alias="container-opts",
        description="Container-level arguments for the application. Example: --privileged",
        default=None,
    )

    @pydantic.model_validator(mode="after")
    def validate_container_properties(self) -> Self:
        error_messages = {
            "rootfs": "'url' parameter must be provided for container type 'rootfs'",
            "docker": "'image' parameter must be provided for container type 'docker'",
            "singularity": "'image' parameter must be provided for container type 'singularity'",
        }

        if (self.type_ == "rootfs" and self.url is None) or (
            self.type_ in ["docker", "singularity"] and self.image is None
        ):
            raise ValueError(error_messages[self.type_])

        return self
