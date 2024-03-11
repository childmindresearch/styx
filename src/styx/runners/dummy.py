from styx.runners.styxdefs import Execution, Metadata, Runner


class DummyRunner(Runner[str, str], Execution[str, str]):
    def __init__(self) -> None:
        self.last_cargs: list[str] | None = None
        self.last_metadata: Metadata | None = None

    def start_execution(self, metadata: Metadata) -> Execution[str, str]:
        self.last_metadata = metadata
        return self

    def input_file(self, host_file: str) -> str:
        return host_file

    def output_file(self, local_file: str, optional: bool = False) -> str:
        return local_file

    def run(self, cargs: list[str]) -> None:
        self.last_cargs = cargs
