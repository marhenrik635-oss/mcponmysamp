import json

import pytest

from mcp_gta_samp.config import load_config, ConfigError


def test_load_config_reads_valid_json(tmp_path):
    executable = tmp_path / "omp-server.exe"
    executable.write_text("placeholder", encoding="utf-8")
    cfg = tmp_path / "config.json"
    cfg.write_text(
        json.dumps(
            {
                "executable": str(executable),
                "working_dir": str(tmp_path),
                "ready_text": "Listening on port",
                "startup_timeout": 15,
            }
        ),
        encoding="utf-8",
    )

    config = load_config(cfg)

    assert config.executable == executable
    assert config.working_dir == tmp_path
    assert config.ready_text == "Listening on port"
    assert config.startup_timeout == 15


def test_load_config_rejects_missing_file(tmp_path):
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "nope.json")


def test_load_config_rejects_missing_executable_key(tmp_path):
    cfg = tmp_path / "config.json"
    cfg.write_text("{}", encoding="utf-8")
    with pytest.raises(ConfigError, match="executable"):
        load_config(cfg)


def test_load_config_rejects_invalid_json(tmp_path):
    cfg = tmp_path / "config.json"
    cfg.write_text("{not json", encoding="utf-8")
    with pytest.raises(ConfigError, match="invalid JSON"):
        load_config(cfg)
