from pathlib import Path

from mcp_gta_samp.mcp_server import create_mcp_server
from mcp_gta_samp.openmp import OpenMpConfig, OpenMpServer


def test_mcp_exposes_discovered_commands(tmp_path):
    executable = tmp_path / "server.exe"
    executable.write_text("placeholder", encoding="utf-8")
    source = tmp_path / "mode.pwn"
    source.write_text('if (!strcmp(cmdtext, "/help", true)) {}', encoding="utf-8")
    app = create_mcp_server(OpenMpServer(OpenMpConfig(executable=executable)), gamemode_source=source)

    tool_names = {tool.name for tool in app._tool_manager.list_tools()}
    assert "server_list_commands" in tool_names
    assert "server_list_commands" in app._tool_manager._tools
    assert app._tool_manager._tools["server_list_commands"].fn() == {"commands": ["/help"]}


def test_mcp_rejects_command_outside_discovered_allowlist(tmp_path):
    executable = tmp_path / "server.exe"
    executable.write_text("placeholder", encoding="utf-8")
    source = tmp_path / "mode.pwn"
    source.write_text('if (!strcmp(cmdtext, "/help", true)) {}', encoding="utf-8")
    app = create_mcp_server(OpenMpServer(OpenMpConfig(executable=executable)), gamemode_source=source)

    tool = app._tool_manager._tools["server_assert_command"]
    assert tool.fn("/help") == {"command": "/help", "allowed": True}
    try:
        tool.fn("/kick")
    except ValueError as exc:
        assert "not discovered" in str(exc)
    else:
        raise AssertionError("expected ValueError")
