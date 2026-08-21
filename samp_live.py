"""Interaktif: server + bot + auto-reply chat player."""
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, ".")

SHARED = Path(tempfile.mkdtemp(prefix="mcp-shared-"))
os.environ["RAKCLIENT_SHARED_DIR"] = str(SHARED)

from mcp_gta_samp.config import load_config  # noqa: E402
from mcp_gta_samp.headless import HeadlessClient  # noqa: E402
from mcp_gta_samp.openmp import OpenMpServer  # noqa: E402

cfg = load_config("local-server.json")
server = OpenMpServer(cfg)
print("server start:", server.start())

RAK = r"D:\Folderku\mcp-gta-samp\vendor\RakClient\target\x86_64-pc-windows-gnu\release\rakclient.exe"
client = HeadlessClient(
    RAK,
    [
        "--server", "127.0.0.1:7777",
        "--nick", "MCPBot",
        "--scripts-dir", r"D:\Folderku\mcp-gta-samp\scripts",
    ],
)
client.start()
print("spawned:", client.wait_until_spawned(20))
print("SHARED_DIR:", SHARED)

# Auto-reply: kalau player chat masuk, bot bales
seen = set()
import re

def send(text: str):
    # via stdin rakclient — langsung
    client._process.stdin.write(text + "\n")
    client._process.stdin.flush()

while True:
    for line in client.history():
        if line in seen:
            continue
        seen.add(line)
        if " chat: " in line and "player_id=" in line:
            # player chat: "chat: <text> player_id=PlayerId(1)"
            m = re.search(r"chat: (.*?) player_id=", line)
            if m:
                msg = m.group(1).strip()
                pid = re.search(r"player_id=PlayerId\((\d+)\)", line)
                print(f"[PLAYER {pid.group(1) if pid else '?'}] {msg}", flush=True)
                # auto-reply
                reply = f"[MCPBot] hai Djati, aku dengar: {msg}"
                send(reply)
                print(f"[MCPBot ->] {reply}", flush=True)
        elif "server:" in line:
            print(f"[SERVER] {line.split('INFO ')[-1].strip()}", flush=True)
    time.sleep(0.5)
