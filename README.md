# MCP on My SAMP

<p align="center">
  <strong>AI-native testing bridge untuk open.mp / SA-MP</strong><br>
  Jalankan server lokal, kendalikan client headless, lalu buktikan response game melalui MCP.
</p>

<p align="center">
  <a href="https://github.com/marhenrik635-oss/mcponmysamp/actions"><img src="https://img.shields.io/github/actions/workflow/status/marhenrik635-oss/mcponmysamp/ci.yml?style=for-the-badge&label=CI" alt="CI"></a>
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/MCP-stdio-7C3AED?style=for-the-badge" alt="MCP stdio">
  <img src="https://img.shields.io/badge/open.mp%20%2F%20SA--MP-local%20testing-00A86B?style=for-the-badge" alt="Local testing only">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-F59E0B?style=for-the-badge" alt="MIT License"></a>
</p>

> **Fokus:** testing server lokal atau server yang kamu miliki / izinkan. Bukan tool untuk mengotomatisasi public server.

---

## Mulai dari nol — Windows

> Jalankan semua command dari **Command Prompt** atau **PowerShell**.

### 1. Download project

`git clone` hanya menyalin source code dari GitHub ke komputer. Tidak langsung menjalankan server.

```bat
git clone https://github.com/marhenrik635-oss/mcponmysamp.git
cd mcponmysamp
```

### 2. Buat lingkungan Python

```bat
py -3 -m venv .venv
.venv\Scripts\activate
```

Jika berhasil, biasanya nama `(.venv)` muncul di awal baris terminal.

### 3. Install dependency

```bat
python -m pip install --upgrade pip
python -m pip install ".[dev]"
```

### 4. Buat konfigurasi lokal

```bat
copy config.example.json local-server.json
```

`local-server.json` sengaja tidak masuk Git karena path server setiap komputer berbeda.

### 5. Jalankan test Python

```bat
pytest -q
```

Jika test selesai tanpa error, lanjut ke live test.

---

## Struktur folder

```text
mcponmysamp/
├─ mcp_gta_samp/                  source MCP server
├─ tests/                         unit dan contract tests
├─ vendor/openmp/Server/          binary + konfigurasi open.mp
│  └─ gamemodes/mcp_test.pwn      gamemode untuk pengujian
├─ vendor/rakclient-bin/          headless RakClient
│  └─ scripts/                    script client
├─ config.example.json            template konfigurasi
└─ local-server.json              konfigurasi lokal, buat sendiri
```

Repository sudah menyertakan binary testing di `vendor/`. Kalau kamu mengganti lokasi server, cukup ubah `local-server.json`.

---

## Konfigurasi server

Buka `local-server.json`. Default-nya:

```json
{
  "executable": "vendor/openmp/Server/omp-server.exe",
  "working_dir": "vendor/openmp/Server",
  "args": ["--config-path", "config.json"],
  "ready_text": "Legacy Network started on port",
  "startup_timeout": 30
}
```

Path relatif dihitung dari **root project**, yaitu folder `mcponmysamp`.

Jika open.mp berada di tempat lain, gunakan path sesuai komputer:

```json
{
  "executable": "D:/Games/open.mp/omp-server.exe",
  "working_dir": "D:/Games/open.mp",
  "args": ["--config-path", "config.json"],
  "ready_text": "Legacy Network started on port",
  "startup_timeout": 30
}
```

---

## Menjalankan MCP

### Server MCP + open.mp saja

```bat
mcp-gta-samp --config local-server.json
```

### Server MCP + open.mp + headless RakClient

Gunakan command multiline berikut di **Command Prompt**:

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

Untuk **PowerShell**, gunakan satu baris agar tidak salah escaping:

```powershell
mcp-gta-samp --config local-server.json --client-executable vendor/rakclient-bin/rakclient.exe --client-arg --server --client-arg 127.0.0.1:7777 --client-arg --nick --client-arg MCPBot --client-arg --scripts-dir --client-arg vendor/rakclient-bin/scripts --gamemode-source vendor/openmp/Server/gamemodes/mcp_test.pwn
```

MCP menggunakan transport **stdio**. Terminal akan terlihat diam karena proses menunggu MCP client mengirim request. Itu normal.

---

## Workflow pengujian

Panggil MCP tools dalam urutan ini:

```text
1. server_status
2. server_start
3. client_start
4. tunggu client mencapai Spawned
5. server_list_commands
6. server_assert_command("/help")
7. client_send_chat("/help")
8. client_assert_output("MCP Test Commands:")
9. client_get_history jika perlu diagnosis
10. client_stop
11. server_stop
```

`Spawned` hanya membuktikan client berhasil masuk game. Bukti command yang valid harus melewati seluruh round-trip:

```text
command dikirim
  → server menerima callback
  → gamemode mengirim response
  → client menerima response
  → MCP assertion berhasil
```

---

## MCP tools

| Tool | Fungsi |
|---|---|
| `server_start` | Menyalakan open.mp dan menunggu readiness. |
| `server_status` | Mengecek status server dan PID. |
| `server_stop` | Menghentikan server. |
| `client_start` | Menyalakan headless RakClient. |
| `client_status` | Mengecek status client. |
| `client_stop` | Menghentikan client. |
| `client_send_chat` | Mengirim command slash yang diizinkan setelah `Spawned`. |
| `client_get_history` | Membaca output client yang dibuffer. |
| `client_assert_output` | Memastikan response tertentu diterima client. |
| `server_list_commands` | Menemukan command dari source Pawn. |
| `server_assert_command` | Memvalidasi command terhadap allowlist. |

`server_list_commands` dan `server_assert_command` aktif jika `--gamemode-source` diberikan.

---

## Live test bawaan

Gamemode test:

```text
vendor/openmp/Server/gamemodes/mcp_test.pwn
```

Command yang tersedia:

```text
/help
/status
```

Contoh assertion:

```text
client_send_chat("/help")
client_assert_output("MCP Test Commands:")
client_assert_output("/status - show a test response")
```

Headless RakClient membuktikan protocol, state, command, dan response. Ia **tidak menghasilkan screenshot**. Testing visual membutuhkan GTA client dengan renderer terpisah.

---

## Jika gamemode Pawn diubah

Compile ulang dari folder server menggunakan Pawn compiler:

```bat
qawno\pawncc.exe -i.\qawno\include -o.\gamemodes\mcp_test .\gamemodes\mcp_test.pwn
```

Jalankan command tersebut dari:

```text
vendor/openmp/Server
```

---

## Troubleshooting cepat

### `mcp-gta-samp is not recognized`

Virtual environment belum aktif, atau package belum ter-install:

```bat
.venv\Scripts\activate
python -m pip install ".[dev]"
```

Alternatif tanpa command global:

```bat
python -m mcp_gta_samp.cli --config local-server.json
```

### `FileNotFoundError` / executable tidak ditemukan

Cek tiga hal:

- command dijalankan dari root `mcponmysamp`;
- `executable` di `local-server.json` benar;
- file `.exe` memang ada.

### Client tidak mencapai `Spawned`

Cek:

- open.mp sudah `server_start` dan ready;
- port UDP `7777` tidak dipakai proses lain;
- alamat client `127.0.0.1:7777` benar;
- `rakclient.exe` dan folder `scripts` ada.

### Test berhenti di tengah

Ambil history client, hentikan proses, lalu pastikan port `7777` kembali kosong. Jangan menganggap server berhasil hanya karena prosesnya masih hidup.

---

## Pengembangan

```bat
.venv\Scripts\activate
pytest -q
python -m pip wheel . --no-deps -w dist
```

Project tidak membutuhkan database, credential, proxy pool, atau koneksi public server.

---

## Batasan keamanan

Gunakan hanya pada server lokal atau server yang kamu miliki / izinkan. Project ini tidak menyediakan:

- flood atau spam;
- lag injection;
- arbitrary RCON;
- automation public server;
- API game-control terbuka ke internet.

Jangan commit credential, proxy, log privat, atau konfigurasi server sensitif.

---

## Lisensi

MIT License. Lihat [LICENSE](LICENSE).

<p align="center">
  <strong>Testable. Local. Verifiable.</strong><br>
  Dibuat untuk testing open.mp / SA-MP yang dapat dibuktikan.
</p>

[Repository](https://github.com/marhenrik635-oss/mcponmysamp) · [Issues](https://github.com/marhenrik635-oss/mcponmysamp/issues)
