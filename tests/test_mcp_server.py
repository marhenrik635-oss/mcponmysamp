import sys

from mcp_gta_samp.mcp_server import create_mcp_server
from mcp_gta_samp.openmp import OpenMpConfig, OpenMpServer


def test_mcp_server_exposes_safe_lifecycle_tools(tmp_path):
    executable = tmp_path / "server.exe"
    executable.write_text("placeholder", encoding="utf-8")
    app = create_mcp_server(OpenMpServer(OpenMpConfig(executable=executable)))

    tools = app._tool_manager.list_tools()

    assert {tool.name for tool in tools} == {"server_start", "server_stop", "server_status"}


def test_mcp_server_tool_functions_control_server(tmp_path):
    script = tmp_path / "fake_server.py"
    script.write_text("print('READY', flush=True); input()\n", encoding="utf-8")
    server = OpenMpServer(
        OpenMpConfig(
            executable=sys.executable,
            args=[str(script)],
            ready_text="READY",
            startup_timeout=2,
        )
    )
    app = create_mcp_server(server)
    tools = app._tool_manager._tools

    assert tools["server_start"].fn() == {"running": True, "ready": True}
    assert tools["server_status"].fn()["running"] is True
    assert tools["server_stop"].fn() == {"running": False}
