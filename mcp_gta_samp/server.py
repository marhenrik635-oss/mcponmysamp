from __future__ import annotations

from dataclasses import dataclass, field
import subprocess
import time
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

    @property
    def pid(self) -> int | None:
        return self._process.pid if self._process else None

    def start(self) -> None:
        if self.is_running():
            return
        self._output = ""
        self._process = subprocess.Popen(
            [self.config.executable, *self.config.args],
            cwd=self.config.cwd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

    def wait_until_ready(self) -> bool:
        if not self._process or not self._process.stdout:
            raise RuntimeError("server is not started")
        deadline = time.monotonic() + self.config.startup_timeout
        while time.monotonic() < deadline:
            line = self._process.stdout.readline()
            if line:
                self._output += line
                if self.config.ready_text in self._output:
                    return True
            elif self._process.poll() is not None:
                break
            else:
                time.sleep(0.01)
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

    def __enter__(self) -> "ServerProcess":
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.stop()


# ponytail: stdout is consumed only during readiness; add asynchronous log streaming when log queries need it.
