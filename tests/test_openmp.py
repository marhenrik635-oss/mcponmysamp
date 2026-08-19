import sys

import pytest

from mcp_gta_samp.openmp import OpenMpConfig, OpenMpServer


def test_config_requires_existing_executable(tmp_path):
    with pytest.raises(FileNotFoundError, match="open.mp executable"):
        OpenMpConfig(executable=tmp_path / "missing.exe").validate()


def test_openmp_server_builds_process_config(tmp_path):
    executable = tmp_path / "omp-server.exe"
    executable.write_text("placeholder", encoding="utf-8")
    config = OpenMpConfig(
        executable=executable,
        working_dir=tmp_path,
        args=["--config", "server.cfg"],
        ready_text="Listening on port",
    )

    process_config = config.validate().to_process_config()

    assert process_config.executable == str(executable)
    assert process_config.cwd == str(tmp_path)
    assert process_config.args == ["--config", "server.cfg"]
    assert process_config.ready_text == "Listening on port"


def test_openmp_facade_status_is_safe_before_start(tmp_path):
    executable = tmp_path / "omp-server.exe"
    executable.write_text("placeholder", encoding="utf-8")
    server = OpenMpServer(OpenMpConfig(executable=executable))

    assert server.status() == {"running": False, "pid": None}


def test_openmp_facade_starts_fake_process(tmp_path):
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

    assert server.start() == {"running": True, "ready": True}
    assert server.status()["running"] is True
    assert server.stop() == {"running": False}


@pytest.mark.parametrize("field", ["executable", "ready_text"])
def test_config_rejects_blank_values(tmp_path, field):
    values = {"executable": tmp_path / "server.exe", "ready_text": "READY"}
    values[field] = "" if field == "ready_text" else None
    with pytest.raises(ValueError):
        OpenMpConfig(**values).validate()
