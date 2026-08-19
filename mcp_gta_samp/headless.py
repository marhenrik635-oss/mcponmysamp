from __future__ import annotations

import queue
import subprocess
import threading
import time
from typing import Sequence


class HeadlessClient:
    def __init__(self, executable: str, args: Sequence[str] = ()):
        self.executable = executable
        self.args = list(args)
        self._process: subprocess.Popen[str] | None = None
        self._lines: list[str] = []
        self._queue: queue.Queue[str] = queue.Queue()
        self._pending: list[str] = []
        self._reader: threading.Thread | None = None
        self._ready = threading.Event()

    @property
    def running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def start(self) -> None:
        if self.running:
            return
        self._lines.clear()
        self._pending.clear()
        self._ready.clear()
        self._process = subprocess.Popen(
            [self.executable, *self.args],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )
        assert self._process.stdout is not None
        self._reader = threading.Thread(target=self._read_output, args=(self._process.stdout,), daemon=True)
        self._reader.start()

    def _read_output(self, stream: object) -> None:
        for raw_line in stream:  # type: ignore[union-attr]
            line = raw_line.rstrip("\r\n")
            self._lines.append(line)
            self._queue.put(line)
            if "state transition state=Spawned" in line or "spawned" in line.lower():
                self._ready.set()

    def send_chat(self, command: str, timeout: float = 5.0) -> str:
        if not self.running or not self._process or not self._process.stdin:
            raise RuntimeError("headless client is not running")
        command = command.strip()
        if not command.startswith("/"):
            raise ValueError("only slash commands are allowed")
        before = len(self._lines)
        self._process.stdin.write(command + "\n")
        self._process.stdin.flush()
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            for line in self._lines[before:]:
                # RakClient stdout is a tracing stream. Only a server event is an
                # authoritative command response; startup/state lines are noise.
                if " server: " in line:
                    return line
            time.sleep(0.05)
        raise TimeoutError(f"no server response to {command}")

    def wait_until_spawned(self, timeout: float = 15.0) -> bool:
        return self._ready.wait(timeout)

    def send_chat_after_spawn(self, command: str, timeout: float = 15.0) -> str:
        if not self.wait_until_spawned(timeout):
            raise TimeoutError("headless client did not reach Spawned")
        return self.send_chat(command, timeout=timeout)

    def history(self) -> list[str]:
        return list(self._lines)

    def drain_pending(self) -> list[str]:
        pending, self._pending = self._pending, []
        return pending

    def history_contains(self, text: str) -> bool:
        return any(text in line for line in self._lines)

    def stop(self) -> None:
        if not self._process:
            return
        if self.running and self._process.stdin:
            try:
                self._process.stdin.close()
            except OSError:
                pass
        try:
            self._process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self._process.kill()
            self._process.wait()
        self._process = None
        self._reader = None

    def __enter__(self) -> "HeadlessClient":
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.stop()


# ponytail: one reader thread keeps event order; add structured RakClient event parsing after protocol output is stable.
