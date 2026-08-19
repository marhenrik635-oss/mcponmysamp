import sys

from mcp_gta_samp.headless import HeadlessClient
from mcp_gta_samp.mcp_server import create_mcp_server
from mcp_gta_samp.openmp import OpenMpConfig, OpenMpServer


def test_mcp_exposes_client_tools_when_client_is_injected(tmp_path):
    server_exe = tmp_path / "server.exe"
    server_exe.write_text("placeholder", encoding="utf-8")
    client = HeadlessClient(sys.executable, ["-c", "import time; time.sleep(60)"])
    app = create_mcp_server(OpenMpServer(OpenMpConfig(executable=server_exe)), client=client)

    assert {tool.name for tool in app._tool_manager.list_tools()} == {
        "server_start", "server_stop", "server_status",
        "client_start", "client_stop", "client_status", "client_send_chat",
        "client_get_history", "client_assert_output",
    }
    client.stop()


def test_client_send_chat_tool_returns_response(tmp_path):
    server_exe = tmp_path / "server.exe"
    server_exe.write_text("placeholder", encoding="utf-8")
    script = "import sys; print('state transition state=Spawned', flush=True); [print('INFO server: REPLY:' + x.strip(), flush=True) for x in sys.stdin]"
    client = HeadlessClient(sys.executable, ["-c", script])
    app = create_mcp_server(OpenMpServer(OpenMpConfig(executable=server_exe)), client=client)
    tools = app._tool_manager._tools

    assert tools["client_start"].fn() == {"running": True}
    assert tools["client_send_chat"].fn("/help") == {"command": "/help", "output": "INFO server: REPLY:/help"}
    assert tools["client_stop"].fn() == {"running": False}
