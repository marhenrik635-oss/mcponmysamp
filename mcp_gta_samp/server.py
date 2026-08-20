from __future__ import annotations

from dataclasses import dataclass, field
import subprocess
import threading
from typing import Sequence


@dataclass(frozen=True)
class ServerConfig:
    executable: str
    args: Sequence[str] = field(default_factory=tuple)
    ready_text: str = ""
    startup_timeout: float = 30.0
    cwd: str | None = None


class ServerProcess:
    def __init__(self, config: ServerConfig):
        self.config = config
        self._process: subprocess.Popen[str] | None = None
        self._output = ""
        self._ready = threading.Event()
        self._reader: threading.Thread | None = None

    @property
    def pid(self) -> int | None:
        return self._process.pid if self._process else None

    def start(self) -> None:
        if self.is_running():
            return
        self._output = ""
        self._ready.clear()
        self._process = subprocess.Popen(
            [self.config.executable, *self.config.args],
            cwd=self.config.cwd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert self._process.stdout is not None
        self._reader = threading.Thread(
            target=self._read_output, args=(self._process.stdout,), daemon=True
        )
        self._reader.start()

    def _read_output(self, stream: object) -> None:
        for raw_line in stream:  # type: ignore[union-attr]
            line = raw_line.rstrip("\r\n")
            self._output += line + "\n"
            if self.config.ready_text in self._output:
                self._ready.set()

    def wait_until_ready(self) -> bool:
        if not self._process or not self._process.stdout:
            raise RuntimeError("server is not started")
        if self._ready.wait(self.config.startup_timeout):
            return True
        raise TimeoutError("server did not become ready")

    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def stop(self) -> None:
        if not self._process:
            return
        if self.is_running() and self._process.stdin:
            try:
                self._process.stdin.write("shutdown\n")
                self._process.stdin.flush()
            except OSError:
                pass
        try:
            self._process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self._process.kill()
            self._process.wait()
        finally:
            for stream in (self._process.stdin, self._process.stdout):
                if stream:
                    try:
                        stream.close()
                    except OSError:
                        pass
            self._process = None
            self._reader = None

    def __enter__(self) -> "ServerProcess":
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.stop()


# ponytail: stdout is consumed only during readiness; add asynchronous log streaming when log queries need it.
