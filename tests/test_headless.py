import sys
import time

from mcp_gta_samp.headless import HeadlessClient


def test_headless_client_waits_for_spawn_marker(tmp_path):
    script = tmp_path / "client.py"
    script.write_text(
        "import time\n"
        "print('state transition state=Spawned', flush=True)\n"
        "time.sleep(60)\n",
        encoding="utf-8",
    )
    client = HeadlessClient(sys.executable, [str(script)])
    client.start()
    try:
        assert client.wait_until_spawned(timeout=2) is True
    finally:
        client.stop()


def test_headless_client_sends_chat_and_reads_process_output(tmp_path):
    script = tmp_path / "client.py"
    script.write_text(
        "import sys\n"
        "for line in sys.stdin:\n"
        "    print('INFO server: CLIENT_ECHO:' + line.strip(), flush=True)\n",
        encoding="utf-8",
    )
    client = HeadlessClient(sys.executable, [str(script)])
    client.start()
    try:
        assert client.send_chat("/help", timeout=2) == "INFO server: CLIENT_ECHO:/help"
    finally:
        client.stop()


def test_headless_client_requires_running_process():
    client = HeadlessClient(sys.executable, [])
    try:
        client.send_chat("/help")
    except RuntimeError as exc:
        assert "not running" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")


def test_headless_client_rejects_non_slash_input(tmp_path):
    client = HeadlessClient(sys.executable, [])
    client.start()
    try:
        try:
            client.send_chat("hello")
        except ValueError as exc:
            assert "slash" in str(exc)
        else:
            raise AssertionError("expected ValueError")
    finally:
        client.stop()
        time.sleep(0.01)
        assert client.running is False
