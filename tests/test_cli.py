from mcp_gta_samp.cli import build_parser, main


def test_cli_requires_config_flag():
    parser = build_parser()
    args = parser.parse_args(["--config", "server.json"])
    assert str(args.config) == "server.json"


def test_cli_returns_error_for_missing_config(tmp_path, capsys):
    exit_code = main(["--config", str(tmp_path / "missing.json")])
    captured = capsys.readouterr()
    assert exit_code == 2
    assert "error:" in captured.err
