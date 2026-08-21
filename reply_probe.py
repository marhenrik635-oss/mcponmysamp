"""Balas chat dari player via stdin RakClient."""
import sys
sys.path.insert(0, ".")
from mcp_gta_samp.headless import HeadlessClient

# Reuse: tulis langsung ke stdin rakclient yang lagi jalan? Gak bisa dari sini.
# Kirim chat baru via client baru? Salah.
# Cara bener: pakai samp_live.py yang punya client handle — kirim via shared file? No.
# RakClient baca stdin; stdin dipegang samp_live.py. Jadi harus lewat samp_live.
print("Gunakan samp_live.py untuk reply — tulis stdin ke process.")
