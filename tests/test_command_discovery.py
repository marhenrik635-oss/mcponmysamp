from mcp_gta_samp.command_discovery import discover_commands


def test_discovers_commands_from_pawn_source(tmp_path):
    source = tmp_path / "mode.pwn"
    source.write_text(
        'if (!strcmp(cmdtext, "/help", true)) {}\n'
        'if (!strcmp(cmdtext, "/status", true)) {}\n',
        encoding="utf-8",
    )

    assert discover_commands(source) == ["/help", "/status"]


def test_discovery_deduplicates_and_sorts(tmp_path):
    source = tmp_path / "mode.pwn"
    source.write_text(
        'if (!strcmp(cmdtext, "/z", true)) {}\n'
        'if (!strcmp(cmdtext, "/help", true)) {}\n'
        'if (!strcmp(cmdtext, "/z", true)) {}\n',
        encoding="utf-8",
    )

    assert discover_commands(source) == ["/help", "/z"]


def test_discovery_rejects_missing_source(tmp_path):
    try:
        discover_commands(tmp_path / "missing.pwn")
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("expected FileNotFoundError")
