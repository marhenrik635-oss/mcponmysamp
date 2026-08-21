# MCP on My SAMP

AI-native testing bridge untuk server open.mp / SA-MP lokal.

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white) ![MCP](https://img.shields.io/badge/MCP-stdio-7C3AED?style=for-the-badge) ![License](https://img.shields.io/badge/license-MIT-F59E0B?style=for-the-badge) [![M8ven Score](https://m8ven.ai/badge/mcp/marhenrik635-oss-mcponmysamp-f5v8cy)](https://m8ven.ai/mcp/marhenrik635-oss-mcponmysamp-f5v8cy)

> Gunakan hanya untuk server lokal atau server yang kamu miliki / izinkan. Bukan tool public-server automation.

## Fitur

- Lifecycle open.mp: start, status, stop.
- Lifecycle headless RakClient: start, status, stop.
- Spawn-gated command dispatch.
- Command allowlist dari source Pawn.
- Client history dan response assertion.
- Evidence-based command round-trip.

Tidak menyediakan flood, spam, lag injection, arbitrary RCON, atau automation server publik.

## Alur kerja

```text
AI agent
  │ MCP stdio
  ▼
MCP on My SAMP ──► open.mp server
        │              ▲
        └── RakClient ─┘ UDP lokal
```

Bukti valid:

```text
command dikirim
→ server callback menerima command
→ gamemode mengirim response
→ client menerima response
→ MCP assertion berhasil
```

## Instalasi Windows

Jalankan dari root repository yang baru di-clone:

```bat
git clone https://github.com/marhenrik635-oss/mcponmysamp.git
cd mcponmysamp
py -3 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install ".[dev]"
pytest -q
```

Linux / macOS:

```bash
git clone https://github.com/marhenrik635-oss/mcponmysamp.git
cd mcponmysamp
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install ".[dev]"
pytest -q
```

## Dependency game

Binary open.mp, RakClient, dan Pawn compiler **tidak disimpan di Git repository** agar clone tetap kecil dan tidak mendistribusikan binary pihak ketiga.

Siapkan dependency tersebut sendiri. Struktur lokal bebas; contoh:

```text
D:/Games/open.mp/omp-server.exe
D:/Games/RakClient/rakclient.exe
D:/Games/RakClient/scripts/
```

## Konfigurasi

Salin template:

```bat
copy config.example.json local-server.json
```

Linux / macOS:

```bash
cp config.example.json local-server.json
```

Edit `local-server.json`:

```json
{
  "executable": "D:/Games/open.mp/omp-server.exe",
  "working_dir": "D:/Games/open.mp",
  "args": ["--config-path", "config.json"],
  "ready_text": "Legacy Network started on port",
  "startup_timeout": 30
}
```

`local-server.json` sengaja di-ignore Git. Gunakan path sesuai komputer sendiri.

## Menjalankan MCP

Server saja:

```bat
mcp-gta-samp --config local-server.json
```

Dengan headless RakClient:

```bat
mcp-gta-samp ^
  --config local-server.json ^
  --client-executable D:/Games/RakClient/rakclient.exe ^
  --client-arg --server ^
  --client-arg 127.0.0.1:7777 ^
  --client-arg --nick ^
  --client-arg MCPBot ^
  --client-arg --scripts-dir ^
  --client-arg D:/Games/RakClient/scripts ^
  --gamemode-source examples/mcp_test.pwn
```

Untuk PowerShell, gunakan satu baris. MCP menggunakan transport `stdio`; terminal yang diam berarti proses sedang menunggu request dari MCP client.

## MCP tools

| Tool | Fungsi |
|---|---|
| `server_start` | Start server dan tunggu readiness. |
| `server_status` | Cek server dan PID. |
| `server_stop` | Stop server. |
| `server_list_commands` | Daftar command dari source Pawn. |
| `server_assert_command` | Validasi command terhadap allowlist. |
| `client_start` | Start headless RakClient. |
| `client_status` | Cek status client. |
| `client_stop` | Stop client. |
| `client_send_chat` | Kirim command slash allowlisted setelah `Spawned`. |
| `client_get_history` | Ambil output client. |
| `client_assert_output` | Pastikan response diterima client. |
| `bot_walk_to` | Jalan ke titik (walk/jog/sprint/direct). |
| `bot_stop` | Berhenti jalan. |
| `bot_teleport` | Teleport body. |
| `bot_face_heading` | Hadap arah (derajat). |
| `bot_face_point` | Hadap titik. |
| `bot_jump` | Pulse lompat. |
| `bot_key_hold` | Hold key mask (8=sprint, 4=fire, 32=jump, 128=crouch). |
| `bot_key_release` | Lepas semua key. |
| `bot_enter_vehicle` | Masuk kendaraan (ID, seat). |
| `bot_exit_vehicle` | Keluar kendaraan. |
| `bot_animation` | Paksa animasi (ID, flags). |
| `bot_set_velocity` | Set velocity vector. |
| `bot_send_chat` | Kirim chat (tanpa slash). |
| `bot_respawn` | Force respawn. |
| `bot_reconnect` | Putus & reconnect ke server. |
| `bot_dialog` | Jawab dialog server. |
| `bot_get_position` | Posisi body. |
| `bot_get_rotation` | Heading body. |
| `bot_get_vehicle` | ID kendaraan saat ini. |
| `bot_get_health` | HP + armour. |
| `bot_get_weapon` | ID senjata saat ini. |
| `bot_get_money` | Uang. |
| `bot_get_nick` | Nickname. |
| `bot_get_interior` | Interior ID. |
| `bot_get_camera` | Posisi kamera. |
| `bot_get_keys` | Key mask yang dihold. |
| `bot_get_server` | Alamat server. |
| `bot_is_walking` | Apakah sedang berjalan? |
| `bot_ping` | Cek apakah bridge script hidup. |
| `bot_scan_players` | Player di sekitar (ID, posisi). |
| `bot_scan_vehicles` | Kendaraan di sekitar (ID, posisi, model). |
| `bot_wait_for_chat` | Tunggu chat mengandung marker. |

## Workflow AI agent

```text
1. server_status
2. server_start jika belum berjalan
3. client_start
4. tunggu Spawned
5. server_list_commands
6. server_assert_command("/help")
7. client_send_chat("/help")
8. client_assert_output("MCP Test Commands:")
9. client_get_history bila perlu diagnosis
10. client_stop
11. server_stop
```

Jangan menganggap boot, join, atau `Spawned` sebagai bukti command berhasil. Jika gagal, klasifikasikan boundary: boot, koneksi, spawn, queue, outbound packet, callback server, response server, parser client, atau assertion MCP.

## Fixture gamemode

Source minimal ada di:

```text
examples/mcp_test.pwn
```

Command:

```text
/help
/status
```

Fixture ini perlu dimasukkan ke folder `gamemodes` pada instalasi open.mp lalu di-compile menggunakan Pawn compiler. Dari folder instalasi open.mp:

```bat
qawno\pawncc.exe -i.\qawno\include -o.\gamemodes\mcp_test examples\mcp_test.pwn
```

Pastikan `config.json` open.mp memuat gamemode:

```json
"main_scripts": ["mcp_test 1"]
```

## Contoh MCP client

MCP client menjalankan executable sebagai subprocess melalui stdio. Sesuaikan semua path:

```json
{
  "mcpServers": {
    "mcponmysamp": {
      "command": "D:/path/mcponmysamp/.venv/Scripts/mcp-gta-samp.exe",
      "args": [
        "--config", "D:/path/mcponmysamp/local-server.json",
        "--client-executable", "D:/Games/RakClient/rakclient.exe",
        "--client-arg", "--server",
        "--client-arg", "127.0.0.1:7777",
        "--client-arg", "--nick",
        "--client-arg", "MCPBot",
        "--client-arg", "--scripts-dir",
        "--client-arg", "D:/Games/RakClient/scripts",
        "--gamemode-source", "D:/path/mcponmysamp/examples/mcp_test.pwn"
      ]
    }
  }
}
```

## Testing dan build

```bat
.venv\Scripts\activate
pytest -q
python -m pip wheel . --no-deps -w dist
```

Target minimal: seluruh test Python lulus. Live test membutuhkan dependency game lokal dan tidak dijalankan di CI.

## Struktur repository

```text
mcp_gta_samp/       package MCP Python
tests/              unit dan contract tests
examples/           fixture Pawn kecil
config.example.json template konfigurasi
README.md           dokumentasi
LICENSE             MIT License
```

## Keamanan dan batasan

Gunakan hanya pada server lokal atau server yang kamu miliki / izinkan. Jangan commit credential, proxy, log privat, konfigurasi sensitif, atau binary game besar. Headless RakClient membuktikan protocol, state, command, dan response; bukan screenshot atau gameplay visual.

## Lisensi

MIT License. Lihat [LICENSE](LICENSE).

[Repository](https://github.com/marhenrik635-oss/mcponmysamp) · [Issues](https://github.com/marhenrik635-oss/mcponmysamp/issues)

<p align="center"><strong>Testable. Local. Verifiable.</strong></p>
