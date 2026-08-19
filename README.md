# MCP on My SAMP

MCP server untuk menguji server **open.mp / SA-MP lokal** melalui headless RakClient.

> Fokus proyek: integration testing yang bisa dijalankan AI agent secara deterministik.
> Gunakan hanya untuk server lokal atau server yang memang kamu miliki/izinkan.

## Fitur

- Menyalakan, memeriksa, dan mematikan server open.mp.
- Menyalakan, memeriksa, dan mematikan headless RakClient.
- Menunggu client benar-benar mencapai state `Spawned`.
- Mengirim command slash yang diizinkan.
- Menyimpan history output client.
- Memastikan response server benar-benar diterima client.
- Menemukan command dari source Pawn gamemode.
- Menolak command yang tidak ada di allowlist.

Tidak ada fitur flood, spam, lag injection, arbitrary RCON, atau automation ke public server.

## Arsitektur singkat

```text
AI agent
  ↓ MCP stdio
mcp-gta-samp
  ├─ ServerProcess → open.mp server
  └─ HeadlessClient → RakClient → UDP localhost → open.mp
                                      ↓
                              response server
                                      ↓
                              client history
```

Round-trip yang diuji:

```text
client_start
→ client mencapai Spawned
→ client_send_chat("/help")
→ open.mp menerima command
→ gamemode mengirim response
→ RakClient menerima server message
→ client_assert_output
```

Output startup tidak dianggap sebagai response command. Adapter menunggu event server yang valid.

## Persyaratan

- Windows, Linux, atau macOS untuk package Python.
- Python 3.10 atau lebih baru.
- open.mp server.
- RakClient headless untuk live test.
- Git, jika install dari source.

Binary open.mp dan RakClient **tidak wajib** untuk unit test Python. Binary hanya diperlukan untuk live smoke test.

## Instalasi dari source

### Windows

```bat
cd D:\Folderku\mcp-gta-samp
py -3 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install ".[dev]"
```

### Linux / macOS

```bash
cd /path/ke/mcponmysamp
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install ".[dev]"
```

Jalankan test:

```bash
pytest -q
```

## Instalasi package wheel

Maintainer dapat membuat wheel:

```bash
python -m pip wheel . --no-deps -w dist
```

Install wheel:

```bash
python -m pip install dist/mcp_gta_samp-0.1.0-py3-none-any.whl
```

## Konfigurasi server

Salin template:

```bat
copy config.example.json local-server.json
```

Linux / macOS:

```bash
cp config.example.json local-server.json
```

Isi default:

```json
{
  "executable": "vendor/openmp/Server/omp-server.exe",
  "working_dir": "vendor/openmp/Server",
  "args": ["--config-path", "config.json"],
  "ready_text": "Legacy Network started on port",
  "startup_timeout": 30
}
```

Keterangan:

- `executable`: path ke `omp-server.exe` atau binary open.mp.
- `working_dir`: folder server agar path gamemode relatif terbaca.
- `args`: argumen proses open.mp.
- `ready_text`: teks yang menandakan server siap.
- `startup_timeout`: batas tunggu startup dalam detik.

`local-server.json` di-ignore Git karena path tiap komputer berbeda.

## Menjalankan MCP server

Server-only:

```bat
mcp-gta-samp --config local-server.json
```

Dengan headless RakClient:

```bat
mcp-gta-samp ^
  --config local-server.json ^
  --client-executable vendor/rakclient-bin/rakclient.exe ^
  --client-arg --server ^
  --client-arg 127.0.0.1:7777 ^
  --client-arg --nick ^
  --client-arg MCPBot ^
  --client-arg --scripts-dir ^
  --client-arg vendor/rakclient-bin/scripts ^
  --gamemode-source vendor/openmp/Server/gamemodes/mcp_test.pwn
```

Linux / macOS gunakan `\` sebagai line continuation.

`--client-arg` dapat diulang. Transport MCP menggunakan **stdio**. Jangan menulis log debug ke stdout MCP.

## Daftar MCP tools

Jika hanya server yang dikonfigurasi:

- `server_start` — start server dan tunggu readiness.
- `server_status` — cek process status dan PID.
- `server_stop` — stop server.

Jika client dikonfigurasi:

- `client_start` — start RakClient.
- `client_status` — cek client berjalan atau tidak.
- `client_stop` — stop RakClient.
- `client_send_chat(command)` — kirim command slash yang allowlisted setelah `Spawned`.
- `client_get_history` — ambil seluruh output client.
- `client_assert_output(text)` — gagal jika text belum diterima client.

Jika `--gamemode-source` dikonfigurasi:

- `server_list_commands` — daftar command yang ditemukan dari source Pawn.
- `server_assert_command(command)` — validasi command terhadap allowlist.

## Instruksi untuk AI agent

Berikan konteks berikut kepada agent yang memakai MCP ini:

```text
Kamu sedang menguji server open.mp/SA-MP lokal atau server yang dimiliki user.
Gunakan MCP on My SAMP hanya untuk test deterministik.
Jangan mengakses public server.

Workflow wajib:
1. Panggil server_status.
2. Panggil server_start jika server belum berjalan.
3. Panggil client_start.
4. Tunggu sampai client mencapai Spawned.
5. Panggil server_list_commands jika tersedia.
6. Validasi command dengan server_assert_command.
7. Panggil client_send_chat dengan command yang valid.
8. Gunakan client_assert_output untuk memastikan response server diterima.
9. Ambil client_get_history bila diagnosis diperlukan.
10. Panggil client_stop dan server_stop setelah test.

Jangan menganggap server boot, join, atau Spawned sebagai bukti command round-trip.
Bukti valid harus mencakup command dikirim, callback server, response server, dan response diterima client.
Jika test gagal, laporkan boundary yang gagal: boot, koneksi, spawn, command queue,
outbound packet, callback server, response server, parser client, atau MCP assertion.
```

## Contoh skenario test

Dengan gamemode contoh:

```text
1. server_start
2. client_start
3. server_list_commands → ["/help", "/status"]
4. server_assert_command("/help")
5. client_send_chat("/help")
6. client_assert_output("MCP Test Commands:")
7. client_assert_output("/status - show a test response")
8. client_stop
9. server_stop
```

Gamemode test berada di:

```text
vendor/openmp/Server/gamemodes/mcp_test.pwn
```

Input slash diproses oleh handler test yang sesuai dengan event chat yang dikirim headless client. Binary `.amx` harus dibuat ulang jika source Pawn diubah:

```bat
cd vendor\openmp\Server
qawno\pawncc.exe -i.\qawno\include -o.\gamemodes\mcp_test .\gamemodes\mcp_test.pwn
```

Jika terminal menampilkan warning symbol tidak dipakai, itu warning compiler; tetap periksa hasil `.amx` dan jalankan live smoke test.

## Testing

Unit dan contract test:

```bash
pytest -q
```

Build package:

```bash
python -m pip wheel . --no-deps -w dist
```

Fresh install smoke test:

```bash
python -m venv /tmp/mcp-fresh
source /tmp/mcp-fresh/bin/activate
python -m pip install dist/mcp_gta_samp-0.1.0-py3-none-any.whl
python -c "import mcp_gta_samp; print(mcp_gta_samp.__file__)"
```

Live test memerlukan:

- port UDP `7777` tersedia;
- server dijalankan dari `vendor/openmp/Server`;
- RakClient binary tersedia;
- proses lama dibersihkan sebelum test.

Setelah live test, pastikan tidak ada `omp-server` atau `rakclient` tersisa dan port `7777` kembali kosong.

## Struktur repository

```text
mcp_gta_samp/                 package Python dan MCP facade
tests/                        unit, contract, dan bridge tests
vendor/openmp/                runtime open.mp dan gamemode test
vendor/RakClient/             source RakClient
vendor/rakclient-bin/         binary dan script RakClient
config.example.json           template config portable
README.md                     dokumentasi ini
LICENSE                       MIT License
```

Log, artifact runtime, config lokal, cache, proxy pool, dan target native tidak boleh di-commit.

## Batasan saat ini

- Client headless membuktikan protocol/state/command, bukan screenshot atau gameplay visual.
- Screenshot memerlukan rendered GTA client terpisah.
- Config binary game tetap bergantung pada OS dan lokasi instalasi.
- MCP server ini ditujukan untuk local/owned-server testing, bukan deployment publik yang membuka kontrol game ke internet.

## Lisensi

MIT License. Lihat [LICENSE](LICENSE).

Copyright (c) 2026 Djati.

## Repository

https://github.com/marhenrik635-oss/mcponmysamp

Deskripsi GitHub:

```text
MCP bridge for testing local open.mp / SA-MP servers through a headless RakClient.
```

Topics yang disarankan:

```text
mcp, sa-mp, samp, openmp, raknet, game-testing, ai-agents, python
```

## Status

Prototype release untuk local integration testing. Python test suite dan live localhost round-trip telah diverifikasi; binary game diperlukan untuk pengujian live.

