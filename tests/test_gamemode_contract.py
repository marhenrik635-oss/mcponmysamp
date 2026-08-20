from pathlib import Path


GAMEMODE = Path(__file__).parents[1] / "examples/mcp_test.pwn"


def test_mcp_test_gamemode_exposes_help_command():
    source = GAMEMODE.read_text(encoding="utf-8")
    assert '"/help"' in source
    assert '"MCP Test Commands:"' in source
    assert '"/status"' in source


def test_mcp_test_gamemode_routes_chat_commands():
    source = GAMEMODE.read_text(encoding="utf-8")
    assert "handle_mcp_command" in source
    assert "public OnPlayerText" in source
    assert "public OnPlayerCommandText" in source
