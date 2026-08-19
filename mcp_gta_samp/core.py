from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class CommandResult:
    command: str
    output: str


class CommandRunner:
    def __init__(self, transport: Callable[[str], str]):
        self._transport = transport
        self._last_result: CommandResult | None = None

    def send_chat(self, command: str) -> CommandResult:
        command = command.strip()
        if not command:
            raise ValueError("command must not be empty")
        result = CommandResult(command, self._transport(command))
        self._last_result = result
        return result

    def assert_last_output_contains(self, text: str) -> bool:
        if self._last_result is None:
            raise AssertionError("No command has been sent")
        if text not in self._last_result.output:
            raise AssertionError(f"Missing text: {text}")
        return True


# ponytail: transport is intentionally injected; add real RakClient integration only after the contract is stable.
