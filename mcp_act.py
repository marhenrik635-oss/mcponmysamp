"""MCP action: scan players + walk bot ke player."""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, ".")

SHARED = Path(tempfile.mkdtemp(prefix="mcp-shared-"))
os.environ["RAKCLIENT_SHARED_DIR"] = str(SHARED)

from mcp_gta_samp.remote import RemoteControl  # noqa: E402

rc = RemoteControl(SHARED)
print("players:", rc.scan_players())
print("vehicles:", rc.scan_vehicles())
print("pos bot:", rc.position())
