"""Shared-store bridge between MCP tools and the RakClient remote_control.luau script.

The Luau script polls a file key (default <temp>/rakclient-shared/rcq) for commands.
Each command is a pipe-delimited line: <id>|<kind>|<args...>. The script answers on
`rcr` with <id>|ok|... or <id>|err|<message>, then this side deletes both keys.

The same `RAKCLIENT_SHARED_DIR` env var must be visible to both processes.
"""

from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path


class RemoteControlError(RuntimeError):
    pass


class RemoteControl:
    QUEUE_KEY = "rcq"
    RESP_KEY = "rcr"

    def __init__(self, shared_dir: str | os.PathLike[str] | None = None) -> None:
        self.dir = Path(
            shared_dir or os.environ.get("RAKCLIENT_SHARED_DIR")
            or Path(tempfile.gettempdir()) / "rakclient-shared"
        )
        self._seq = 0
        self._dir_created = False
        # Test hook: set by tests to simulate the script side of the bridge.
        self._handle_for_test = None

    def _ensure_dir(self) -> None:
        if not self._dir_created:
            self.dir.mkdir(parents=True, exist_ok=True)
            self._dir_created = True

    def _queue_path(self) -> Path:
        return self.dir / self.QUEUE_KEY

    def _resp_path(self) -> Path:
        return self.dir / self.RESP_KEY

    def _write_atomic(self, path: Path, value: str) -> None:
        self._ensure_dir()
        tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}")
        tmp.write_text(value, encoding="utf-8")
        tmp.replace(path)

    def _read_resp(self, cmd_id: str, timeout: float) -> str:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self._resp_path().exists():
                value = self._resp_path().read_text(encoding="utf-8")
                if value.split("|", 1)[0] == cmd_id:
                    return value
            time.sleep(0.02)
        raise RemoteControlError(f"no response for command {cmd_id} (is the remote_control script loaded?)")

    def command(
        self,
        kind: str,
        args: list[str | float | int] | None = None,
        timeout: float = 10.0,
        return_id: bool = False,
    ) -> list[str]:
        """Send one command and wait for the matching response. Returns result parts after `ok|`."""
        self._seq += 1
        cmd_id = f"{os.getpid()}-{self._seq}"
        parts = [cmd_id, kind, *(str(a) for a in (args or []))]
        self._write_atomic(self._queue_path(), "|".join(parts))
        resp = self._read_resp(cmd_id, timeout)
        # Consume the response before returning so a later command never reads a stale one.
        try:
            self._resp_path().unlink()
        except FileNotFoundError:
            pass
        fields = resp.split("|")
        if fields[1] == "err":
            raise RemoteControlError("|".join(fields[2:]))
        if return_id:
            return [cmd_id, *fields[2:]]
        return fields[2:]

    # -- convenience wrappers (the MCP tools call these) ---------------------------

    def walk_to(self, x: float, y: float, z: float, mode: str = "jog") -> None:
        self.command("walk_to", [x, y, z, mode])

    def walk_stop(self) -> None:
        self.command("walk_stop")

    def teleport(self, x: float, y: float, z: float) -> None:
        self.command("teleport", [x, y, z])

    def face_heading(self, heading: float) -> None:
        self.command("face_heading", [heading])

    def face_point(self, x: float, y: float) -> None:
        self.command("face_point", [x, y])

    def jump(self) -> None:
        self.command("jump")

    def position(self) -> tuple[float, float, float]:
        x, y, z = self.command("get_position")
        return float(x), float(y), float(z)

    def rotation(self) -> float:
        (h,) = self.command("get_rotation")
        return float(h)

    def is_walking(self) -> bool:
        (w,) = self.command("is_walking")
        return w == "1"

    def ping(self, timeout: float = 2.0) -> bool:
        try:
            self.command("alive", timeout=timeout)
            return True
        except RemoteControlError:
            return False

    def scan_players(self) -> list[dict[str, float]]:
        """List streamed-in players around the bot: id + position."""
        (payload,) = self.command("scan_players")
        out = []
        for entry in payload.split(";"):
            if not entry:
                continue
            parts = entry.split(",")
            out.append({"id": int(parts[0]), "x": float(parts[1]), "y": float(parts[2]), "z": float(parts[3])})
        return out

    def scan_vehicles(self) -> list[dict[str, float]]:
        """List streamed-in vehicles around the bot: id + position + model (if known)."""
        (payload,) = self.command("scan_vehicles")
        out = []
        for entry in payload.split(";"):
            if not entry:
                continue
            parts = entry.split(",")
            v = {"id": int(parts[0]), "x": float(parts[1]), "y": float(parts[2]), "z": float(parts[3])}
            if len(parts) >= 5:
                v["model"] = int(parts[4])
            out.append(v)
        return out

    def key_hold(self, mask: int) -> None:
        """Hold a key mask (8=sprint, 4=fire, 128=crouch, 32=jump)."""
        self.command("key_hold", [mask])

    def key_release(self) -> None:
        """Release all keys."""
        self.command("key_release")

    def enter_vehicle(self, vehicle_id: int, seat: int = 0) -> None:
        """Enter a vehicle (driver=0, passenger=1). Sends RPC 26 + mirrors locally."""
        self.command("enter_vehicle", [vehicle_id, seat])

    def exit_vehicle(self) -> None:
        """Exit current vehicle. Sends RPC 154."""
        self.command("exit_vehicle")

    def vehicle_id(self) -> int:
        """Current vehicle id (0 = on foot)."""
        fields = self.command("get_vehicle")
        return int(fields[0])

    def animation(self, anim_id: int, flags: int = 0) -> None:
        """Force an on-foot animation."""
        self.command("animation", [anim_id, flags])

    def set_velocity(self, x: float, y: float, z: float) -> None:
        """Set bot velocity vector."""
        self.command("set_velocity", [x, y, z])

    def money(self) -> int:
        fields = self.command("get_money")
        return int(fields[0])

    def nick(self) -> str:
        fields = self.command("get_nick")
        return fields[0]

    def interior(self) -> int:
        fields = self.command("get_interior")
        return int(fields[0])

    def server_addr(self) -> str:
        fields = self.command("get_server_addr")
        return fields[0]

    def send_chat(self, client, text: str, timeout: float = 5.0) -> str:
        """Send a plain chat line via client stdin (no slash requirement)."""
        return client.send_message(text, timeout=timeout)

    def wait_for_chat(self, client, marker: str, timeout: float = 15.0) -> list[str]:
        """Block until a chat line containing `marker` appears in client history.
        Returns matching lines (server messages and player chat)."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            for line in client.history():
                if marker in line:
                    return [line]
            time.sleep(0.1)
        raise RemoteControlError(f"no chat line containing {marker!r} within {timeout}s")

    def health(self, client, timeout: float = 8.0) -> tuple[float, float]:
        """Health + armour via server round-trip.

        The RakClient binary's sampev.onServerMessage event hook does not fire on this
        build, so instead of the script answering, the MCP side reads the value from the
        client's stdout: /health <token> (stdin) -> gamemode replies MCP_HEALTH:<token>:
        <hp>:<armor> -> RakClient logs it as `server: MCP_HEALTH:...` which HeadlessClient
        captures in its history buffer.
        """
        token = str(os.getpid())
        client.send_chat(f"/health {token}", timeout=2.0)
        deadline = time.monotonic() + timeout
        marker = f"MCP_HEALTH:{token}:"
        while time.monotonic() < deadline:
            for line in client.history():
                if marker in line:
                    # "INFO rakclient: server: MCP_HEALTH:<token>:<hp>:<armor> color=..."
                    tail = line.split(marker, 1)[1]
                    hp, _, rest = tail.partition(":")
                    arm = rest.split(" ")[0]
                    try:
                        return float(hp), float(arm)
                    except ValueError:
                        raise RemoteControlError(f"malformed MCP_HEALTH line: {line}")
            time.sleep(0.1)
        raise RemoteControlError(f"no MCP_HEALTH response for token {token}")
