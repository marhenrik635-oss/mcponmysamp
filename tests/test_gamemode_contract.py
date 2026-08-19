from pathlib import Path


GAMEMODE = Path(__file__).parents[1] / "vendor/openmp/Server/gamemodes/mcp_test.pwn"


def test_mcp_test_gamemode_exposes_help_command():
    source = GAMEMODE.read_text(encoding="utf-8")
    assert '"/help"' in source
    assert '"MCP Test Commands:"' in source
    assert '"/status"' in source


def test_local_server_uses_mcp_test_gamemode():
    config = (GAMEMODE.parent.parent / "config.json").read_text(encoding="utf-8")
    assert '"mcp_test 1"' in config
