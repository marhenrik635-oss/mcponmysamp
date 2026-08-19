import sys
import time

import pytest

from mcp_gta_samp.server import ServerConfig, ServerProcess


@pytest.fixture
def fake_server(tmp_path):
    script = tmp_path / "fake_server.py"
    script.write_text(
        "import sys, time\n"
        "print('OPEN_MP_READY', flush=True)\n"
        "for line in sys.stdin:\n"
        "    if line.strip() == 'shutdown': break\n"
        "time.sleep(0.01)\n",
        encoding="utf-8",
    )
    return script


def test_server_starts_waits_for_ready_and_stops(fake_server):
    server = ServerProcess(
        ServerConfig(
            executable=sys.executable,
            args=[str(fake_server)],
            ready_text="OPEN_MP_READY",
            startup_timeout=2,
        )
    )

    server.start()
    assert server.is_running()
    assert server.wait_until_ready() is True

    server.stop()
    assert server.is_running() is False


def test_server_start_is_idempotent(fake_server):
    server = ServerProcess(
        ServerConfig(
            executable=sys.executable,
            args=[str(fake_server)],
            ready_text="OPEN_MP_READY",
            startup_timeout=2,
        )
    )

    server.start()
    first_pid = server.pid
    server.start()

    assert server.pid == first_pid
    server.stop()


def test_server_reports_timeout_when_ready_marker_is_missing(tmp_path):
    script = tmp_path / "never_ready.py"
    script.write_text("import time; time.sleep(2)\n", encoding="utf-8")
    server = ServerProcess(
        ServerConfig(
            executable=sys.executable,
            args=[str(script)],
            ready_text="MISSING",
            startup_timeout=0.05,
        )
    )

    server.start()
    with pytest.raises(TimeoutError, match="server did not become ready"):
        server.wait_until_ready()
    server.stop()
