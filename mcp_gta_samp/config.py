from __future__ import annotations

import json
from pathlib import Path

from .openmp import OpenMpConfig


class ConfigError(Exception):
    pass


def load_config(path: Path | str) -> OpenMpConfig:
    config_path = Path(path)
    if not config_path.is_file():
        raise ConfigError(f"config file not found: {config_path}")
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"invalid JSON in {config_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError("config must be a JSON object")
    if "executable" not in data:
        raise ConfigError("config must contain 'executable'")
    return OpenMpConfig(
        executable=Path(data["executable"]),
        working_dir=Path(data["working_dir"]) if data.get("working_dir") else None,
        args=list(data.get("args", [])),
        ready_text=data.get("ready_text", "Listening on port"),
        startup_timeout=float(data.get("startup_timeout", 30.0)),
    ).validate()


# ponytail: JSON only; add TOML/YAML only if a real user asks for it.
