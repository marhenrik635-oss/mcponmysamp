from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

from .server import ServerConfig, ServerProcess


@dataclass(frozen=True)
class OpenMpConfig:
    executable: Path | str
    working_dir: Path | str | None = None
    args: Sequence[str] = field(default_factory=tuple)
    ready_text: str = "Listening on port"
    startup_timeout: float = 30.0

    def validate(self) -> "OpenMpConfig":
        if not self.executable:
            raise ValueError("open.mp executable must not be blank")
        if not self.ready_text.strip():
            raise ValueError("ready_text must not be blank")
        executable = Path(self.executable)
        if not executable.is_file():
            raise FileNotFoundError(f"open.mp executable not found: {executable}")
        if not self.ready_text.strip():
            raise ValueError("ready_text must not be blank")
        if self.startup_timeout <= 0:
            raise ValueError("startup_timeout must be positive")
        return self

    def to_process_config(self) -> ServerConfig:
        self.validate()
        return ServerConfig(
            executable=str(self.executable),
            args=list(self.args),
            ready_text=self.ready_text,
            startup_timeout=self.startup_timeout,
            cwd=str(self.working_dir) if self.working_dir else None,
        )


class OpenMpServer:
    def __init__(self, config: OpenMpConfig):
        self.config = config
        self._process = ServerProcess(config.to_process_config())

    def start(self) -> dict[str, bool]:
        self._process.start()
        return {"running": True, "ready": self._process.wait_until_ready()}

    def stop(self) -> dict[str, bool]:
        self._process.stop()
        return {"running": False}

    def status(self) -> dict[str, int | bool | None]:
        return {"running": self._process.is_running(), "pid": self._process.pid}


# ponytail: validate launch-critical fields; add server.cfg schema checks when config editing lands.
