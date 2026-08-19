import sys

from mcp_gta_samp.headless import HeadlessClient


def test_client_keeps_all_output_lines_and_searches_history(tmp_path):
    script = tmp_path / "client.py"
    script.write_text(
        "import sys\n"
        "print('BOOT', flush=True)\n"
        "for line in sys.stdin:\n"
        "    print('INFO server: MCP Test Commands:', flush=True)\n"
        "    print('INFO server: /help - show this command list', flush=True)\n",
        encoding="utf-8",
    )
    client = HeadlessClient(sys.executable, [str(script)])
    client.start()
    try:
        client.send_chat("/help", timeout=2)
        assert client.history_contains("MCP Test Commands:")
        assert client.history_contains("/help - show this command list")
        assert client.history()[-1] == "INFO server: /help - show this command list"
    finally:
        client.stop()


def test_mcp_history_tool_returns_buffered_lines(tmp_path):
    script = tmp_path / "client.py"
    script.write_text(
        "import sys\n"
        "for line in sys.stdin:\n"
        "    print('INFO server: MCP_STATUS_OK', flush=True)\n",
        encoding="utf-8",
    )
    client = HeadlessClient(sys.executable, [str(script)])
    client.start()
    try:
        client.send_chat("/status", timeout=2)
        assert client.history()[-1] == "INFO server: MCP_STATUS_OK"
    finally:
        client.stop()
