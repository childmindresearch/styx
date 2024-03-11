import pathlib as pl
import re
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from subprocess import PIPE, CalledProcessError, Popen
from typing import Callable

from styx.runners.styxdefs import Execution, Metadata, Runner


def _docker_mount(host_path: str, container_path: str, readonly: bool) -> str:
    host_path = host_path.replace('"', r"\"")
    container_path = container_path.replace('"', r"\"")
    host_path = host_path.replace("\\", "\\\\")
    container_path = container_path.replace("\\", "\\\\")
    return f"type=bind,source={host_path},target={container_path}{',readonly' if readonly else ''}"


class DockerExecution(Execution[pl.Path, pl.Path]):
    def __init__(self, metadata: Metadata, output_dir: pl.Path) -> None:
        self.metadata = metadata
        self.input_files: list[tuple[pl.Path, str]] = []
        self.input_file_next_id = 0
        self.output_files: list[tuple[pl.Path, str]] = []
        self.output_file_next_id = 0
        self.output_dir = output_dir

    def input_file(self, host_file: pl.Path) -> str:
        local_file = f"/styx_input/{self.input_file_next_id}/{host_file.name}"
        self.input_file_next_id += 1
        self.input_files.append((host_file, local_file))
        return local_file

    def output_file(self, local_file: str, optional: bool = False) -> pl.Path:
        return self.output_dir / local_file

    def run(self, cargs: list[str]) -> None:
        mounts: list[str] = []

        for i, (host_file, local_file) in enumerate(self.input_files):
            mounts.append("--mount")
            mounts.append(_docker_mount(host_file.absolute().as_posix(), local_file, readonly=True))

        # Output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        mounts.append("--mount")
        mounts.append(_docker_mount(self.output_dir.absolute().as_posix(), "/styx_output", readonly=False))

        docker_extra_args: list[str] = []
        container = self.metadata.container_image_tag

        if container is None:
            raise ValueError("No container image tag specified in metadata")

        docker_command = [
            "docker",
            "run",
            "--rm",
            "-w",
            "/styx_output",
            *mounts,
            "--entrypoint",
            "/bin/bash",
            *docker_extra_args,
            container,
            "-l",
            "-c",
            " ".join(cargs),
        ]

        print(f"Executing docker command: '{docker_command}'")

        def stdout_handler(line: str) -> None:
            print(line)

        def stderr_handler(line: str) -> None:
            print(line)

        with Popen(docker_command, text=True, stdout=PIPE, stderr=PIPE) as process:
            with ThreadPoolExecutor(2) as pool:  # two threads to handle the streams
                exhaust = partial(pool.submit, partial(deque, maxlen=0))
                exhaust(stdout_handler(line[:-1]) for line in process.stdout)  # type: ignore
                exhaust(stderr_handler(line[:-1]) for line in process.stderr)  # type: ignore
        retcode = process.poll()
        if retcode:
            raise CalledProcessError(retcode, process.args)


def _default_execution_output_dir(metadata: Metadata) -> pl.Path:
    filesafe_name = re.sub(r"\W+", "_", metadata.name)
    return pl.Path(f"output_{filesafe_name}")


class DockerRunner(Runner[pl.Path, pl.Path]):
    def __init__(self, execution_output_dir: Callable[[Metadata], pl.Path] | None = None) -> None:
        """Create a new DockerRunner.

        Args:
            execution_output_dir: A function that returns the output directory for a given Metadata.
                If None, a folder named 'output_<metadata.name>' will be used.
                This function is called once before every execution.
        """
        self.execution_output_dir: Callable[[Metadata], pl.Path] = (
            _default_execution_output_dir if execution_output_dir is None else execution_output_dir
        )

    def start_execution(self, metadata: Metadata) -> Execution[pl.Path, pl.Path]:
        output_dir = self.execution_output_dir(metadata)
        return DockerExecution(metadata, output_dir)
