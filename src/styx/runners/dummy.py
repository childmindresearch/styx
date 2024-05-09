from styx.runners.styxdefs import Execution, InputPathType, Metadata, OutputPathType, Runner


class DummyRunner(Runner, Execution):
    def __init__(self) -> None:
        self.last_cargs: list[str] | None = None
        self.last_metadata: Metadata | None = None

    def start_execution(self, metadata: Metadata) -> Execution:
        self.last_metadata = metadata
        return self

    def input_file(self, host_file: InputPathType) -> str:
        return str(host_file)

    def output_file(self, local_file: str, optional: bool = False) -> OutputPathType:
        return local_file

    def run(self, cargs: list[str]) -> None:
        self.last_cargs = cargs
