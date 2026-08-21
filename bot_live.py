"""Bot + kontrol: SHARED dir tetap biar bisa dikontrol via MCP."""
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, ".")

SHARED = Path(os.environ.get("RAKCLIENT_SHARED_DIR", r"C:\Users\Administrator\AppData\Local\Temp\mcp-shared-live"))
os.environ["RAKCLIENT_SHARED_DIR"] = str(SHARED)
print("SHARED:", SHARED, flush=True)

from mcp_gta_samp.headless import HeadlessClient  # noqa: E402

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
print("spawned:", client.wait_until_spawned(20), flush=True)
print("BOT_READY", flush=True)

seen = set()
while True:
    for line in client.history():
        if line in seen:
            continue
        seen.add(line)
        if " chat: " in line and "player_id=" in line:
            m = re.search(r"chat: (.*?) player_id=PlayerId\((\d+)\)", line)
            if m:
                msg, pid = m.group(1).strip(), m.group(2)
                print(f"[PLAYER {pid}] {msg}", flush=True)
                reply = f"[MCPBot] Halo! Aku bot AI. Pesanmu: {msg}"
                client._process.stdin.write(reply + "\n")
                client._process.stdin.flush()
                print(f"[MCPBot ->] {reply}", flush=True)
        elif "server:" in line:
            txt = line.split("server:", 1)[1].split("color=")[0].strip()
            print(f"[SERVER] {txt}", flush=True)
    time.sleep(0.5)
