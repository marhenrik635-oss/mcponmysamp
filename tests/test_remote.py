"""Tests for the shared-store remote control bridge (mcp_gta_samp/remote.py).

The real RakClient isn't needed: the Luau script's sharedGet/sharedSet/sharedDelete map
to the same file store the Python side writes, so a fake "script side" here exercises
the full wire protocol (queue -> poll -> execute -> respond -> consume).
"""

import threading
import time

from mcp_gta_samp.remote import RemoteControl, RemoteControlError


def _fake_script_side(rc: RemoteControl, stop: threading.Event) -> None:
    """Mimic remote_control.luau: poll the queue key, answer on the resp key."""
    while not stop.is_set():
        q = rc._queue_path()
        if q.exists():
            raw = q.read_text(encoding="utf-8")
            q.unlink(missing_ok=True)
            fields = raw.split("|")
            cmd_id, kind = fields[0], fields[1]
            args = fields[2:]
            result = rc._handle_for_test(kind, args)
            rc._write_atomic(rc._resp_path(), f"{cmd_id}|{result}")
        time.sleep(0.01)


def _start_fake(rc: RemoteControl) -> threading.Event:
    stop = threading.Event()
    t = threading.Thread(target=_fake_script_side, args=(rc, stop), daemon=True)
    t.start()
    return stop


def test_command_round_trip(tmp_path):
    rc = RemoteControl(tmp_path)
    rc._handle_for_test = lambda kind, args: "ok|" + ",".join(args)
    _start_fake(rc)
    assert rc.command("echo", ["a", "b"]) == ["a,b"]


def test_walk_to_and_position(tmp_path):
    rc = RemoteControl(tmp_path)
    rc._handle_for_test = lambda kind, args: (
        "ok"
        if kind in ("walk_to", "teleport", "jump", "face_heading", "face_point")
        else {"get_position": "ok|1.5|2.5|3.5", "is_walking": "ok|1"}.get(kind, "err|unknown:" + kind)
    )
    _start_fake(rc)
    rc.walk_to(1, 2, 3, "sprint")
    assert rc.position() == (1.5, 2.5, 3.5)
    assert rc.is_walking() is True


def test_scan_players_and_vehicles(tmp_path):
    rc = RemoteControl(tmp_path)
    rc._handle_for_test = lambda kind, args: {
        "scan_players": "ok|1,100.5,200.5,10.0;2,300.0,400.0,20.0",
        "scan_vehicles": "ok|5,50.0,60.0,1.0,411;6,70.0,80.0,2.0",
    }.get(kind, "err|unknown:" + kind)
    _start_fake(rc)
    players = rc.scan_players()
    assert players == [
        {"id": 1, "x": 100.5, "y": 200.5, "z": 10.0},
        {"id": 2, "x": 300.0, "y": 400.0, "z": 20.0},
    ]
    assert rc.scan_vehicles() == [
        {"id": 5, "x": 50.0, "y": 60.0, "z": 1.0, "model": 411},
        {"id": 6, "x": 70.0, "y": 80.0, "z": 2.0},
    ]


def test_keys_and_vehicle(tmp_path):
    rc = RemoteControl(tmp_path)
    rc._handle_for_test = lambda kind, args: {
        "key_hold": "ok",
        "key_release": "ok",
        "enter_vehicle": "ok",
        "exit_vehicle": "ok",
        "get_vehicle": "ok|17",
        "animation": "ok",
        "set_velocity": "ok",
        "get_money": "ok|5000",
        "get_nick": "ok|MCPBot",
        "get_interior": "ok|0",
        "get_server_addr": "ok|127.0.0.1:7777",
    }.get(kind, "err|unknown:" + kind)
    _start_fake(rc)
    rc.key_hold(8)
    rc.key_release()
    rc.enter_vehicle(17, 0)
    rc.exit_vehicle()
    assert rc.vehicle_id() == 17
    rc.animation(1189, 0x8004)
    rc.set_velocity(1, 0, 0)
    assert rc.money() == 5000
    assert rc.nick() == "MCPBot"
    assert rc.interior() == 0
    assert rc.server_addr() == "127.0.0.1:7777"


def test_wait_for_chat(tmp_path):
    rc = RemoteControl(tmp_path)

    class FakeClient:
        def __init__(self):
            self.lines = []

        def history(self):
            return self.lines

    c = FakeClient()
    import threading
    import time

    def later():
        time.sleep(0.3)
        c.lines.append("INFO rakclient: server: MCP_HELLO color=00FFFFFF")

    threading.Thread(target=later, daemon=True).start()
    assert rc.wait_for_chat(c, "MCP_HELLO", timeout=3) == [
        "INFO rakclient: server: MCP_HELLO color=00FFFFFF"
    ]


def test_send_message_no_slash(tmp_path):
    """HeadlessClient.send_message accepts plain text, not just slash commands."""
    from mcp_gta_samp.headless import HeadlessClient
    import sys

    script = tmp_path / "echo.py"
    script.write_text(
        "import sys\nfor line in sys.stdin:\n    print('INFO server: ECHO:' + line.strip(), flush=True)\n",
        encoding="utf-8",
    )
    client = HeadlessClient(sys.executable, [str(script)])
    client.start()
    try:
        resp = client.send_message("hello world", timeout=2)
        assert resp == "hello world"  # returns immediately, no echo wait
        time.sleep(0.2)
        assert any("ECHO:hello world" in line for line in client.history())
        # slash still works
        resp2 = client.send_message("/help", timeout=2)
        assert resp2 == "/help"
    finally:
        client.stop()


def test_health_round_trip(tmp_path):
    """Health via stdout marker — script hook does not fire on this binary."""
    rc = RemoteControl(tmp_path)

    class FakeClient:
        def __init__(self):
            self.lines = []

        def send_chat(self, cmd, timeout=2.0):
            self.lines.append(f"INFO rakclient: server: MCP_HEALTH:{cmd.split()[1]}:100:50 color=00FFFFFF")

        def history(self):
            return self.lines

    rc._handle_for_test = lambda kind, args: "err|unknown:" + kind
    _start_fake(rc)
    client = FakeClient()
    hp, arm = rc.health(client, timeout=5)
    assert (hp, arm) == (100.0, 50.0)


def test_health_pending_retry(tmp_path):
    """Health line arrives after a delay."""
    rc = RemoteControl(tmp_path)

    class FakeClient:
        def __init__(self):
            self.lines = []

        def send_chat(self, cmd, timeout=2.0):
            import threading
            import time
            token = cmd.split()[1]

            def later():
                time.sleep(0.3)
                self.lines.append(f"INFO rakclient: server: MCP_HEALTH:{token}:100:50 color=00FFFFFF")
            threading.Thread(target=later, daemon=True).start()

        def history(self):
            return self.lines

    rc._handle_for_test = lambda kind, args: "err|unknown:" + kind
    _start_fake(rc)
    hp, arm = rc.health(FakeClient(), timeout=5)
    assert (hp, arm) == (100.0, 50.0)


def test_error_maps_to_remote_control_error(tmp_path):
    rc = RemoteControl(tmp_path)
    rc._handle_for_test = lambda kind, args: "err|not implemented"
    _start_fake(rc)
    try:
        rc.command("jump")
    except RemoteControlError as exc:
        assert "not implemented" in str(exc)
    else:
        raise AssertionError("expected RemoteControlError")


def test_timeout_when_no_script(tmp_path):
    rc = RemoteControl(tmp_path)
    try:
        rc.command("alive", timeout=0.2)
    except RemoteControlError as exc:
        assert "no response" in str(exc)
    else:
        raise AssertionError("expected RemoteControlError")


def test_stale_response_is_ignored(tmp_path):
    """A response for a previous command id must not satisfy the current one."""
    rc = RemoteControl(tmp_path)
    rc._write_atomic(rc._resp_path(), "999|ok|stale")
    try:
        rc.command("alive", timeout=0.2)
    except RemoteControlError:
        pass
    else:
        raise AssertionError("expected timeout; stale response must not match")
