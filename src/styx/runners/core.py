from styx.runners.styxdefs import Execution, Runner


class DummyRunner(Runner[str, str], Execution[str, str]):
    def __init__(self) -> None:
        self.last_cargs: list[str] | None = None

    def start_execution(self, tool_name: str) -> Execution[str, str]:
        return self

    def input_file(self, host_file: str) -> str:
        return host_file

    def run(self, cargs: list[str]) -> None:
        self.last_cargs = cargs

    def output_file(self, local_file: str) -> str:
        return local_file

    def finalize(self) -> None:
        pass
