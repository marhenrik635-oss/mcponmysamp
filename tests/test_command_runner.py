import pytest

from mcp_gta_samp.core import CommandResult, CommandRunner


def test_runner_records_command_and_returns_transport_result():
    calls = []

    def transport(command: str) -> str:
        calls.append(command)
        return "[chat] Server: Welcome"

    runner = CommandRunner(transport)

    result = runner.send_chat("/help")

    assert result == CommandResult(command="/help", output="[chat] Server: Welcome")
    assert calls == ["/help"]


def test_runner_rejects_empty_chat_command():
    runner = CommandRunner(lambda _: "unused")

    with pytest.raises(ValueError, match="command must not be empty"):
        runner.send_chat("  ")


def test_runner_asserts_text_in_output():
    runner = CommandRunner(lambda _: "[chat] Server: Welcome")
    runner.send_chat("/help")

    assert runner.assert_last_output_contains("Welcome") is True

    with pytest.raises(AssertionError, match="Missing text"):
        runner.assert_last_output_contains("Not present")
