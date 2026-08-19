from pathlib import Path
import re


_COMMAND_RE = re.compile(r'!strcmp\s*\(\s*cmdtext\s*,\s*["\'](/[A-Za-z0-9_]+)["\']', re.IGNORECASE)


def discover_commands(source: Path | str) -> list[str]:
    text = Path(source).read_text(encoding="utf-8")
    return sorted(set(_COMMAND_RE.findall(text)))


# ponytail: supports direct strcmp command handlers; add parser support only when a real gamemode needs it.
