# Dashboard 5 Agent + Grok Core

Dashboard browser untuk memantau sistem trading di folder ini. Prosesnya terpisah: kalau dashboard mati, trading tidak ikut mati. Dashboard **tidak mengirim order** dan **tidak punya tombol reset kill-switch**.

## Yang sudah ada di repo (hasil inspeksi)

- `config.py`: `VIRTUAL_CAPITAL = 95`, profil `standard` dan `experiment_a`. Nilai yang boleh diubah dashboard disimpan di `data/config.json` dan dibaca `config.py` saat proses trading berikutnya mulai. Kalau file itu hilang atau rusak, bawaan di `config.py` yang dipakai.
- `risk_engine/validation.py`: `evaluate_trade`, `SymbolSpec`, `TradeRequest`, `RiskDecision`.
- `risk_engine/exposure.py`: `check_exposure`.
- `risk_engine/drawdown.py`: `DrawdownMonitor`.
- `risk_engine/kill_switch.py`: file `logs\KILL_SWITCH.lock`. Sengaja tanpa fungsi reset.
- Folder `agents/` dan `core/` sudah ada sebagai stub kosong (`scope.py`, `whales.py`, dll). Dashboard **tidak mengimpor** file itu. Event dan status memakai `emit_event()` + file JSON. Cari komentar `# TODO: sambungkan ke modul asli`.

## Instal (PowerShell)

```powershell
cd C:\Users\LENOVO\Documents\PYTHON_AI_LAB
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
cd dashboard_ui
npm install
cd ..
```

## Jalankan

Mode mock (tanpa MT5 dan tanpa API key):

```powershell
cd C:\Users\LENOVO\Documents\PYTHON_AI_LAB
.\scripts\run_dashboard.ps1
```

Buka http://127.0.0.1:5173 . Header harus bertuliskan mode **MOCK**. Event palsu muncul di halaman Log.

Mode live (hanya membaca file yang ditulis sistem trading):

```powershell
$env:DASHBOARD_MODE = "live"
.\scripts\run_dashboard.ps1
```

## Tes

```powershell
.\venv\Scripts\Activate.ps1
python test_risk.py
python -m pytest dashboard_api/tests -q
cd dashboard_ui
npm run build
```

`test_risk.py` harus tetap **12/12**.

## Menulis event dari sistem trading

Jangan impor FastAPI. Dari kode trading:

```python
from emit_event import emit_event

emit_event(
    "RISK",
    "decision",
    "Trade ditolak",
    symbol="XAUUSDm",
    level="warn",
    data={"approved": False, "reasons": ["Lot minimum kegedean"]},
)
```

File tujuan: `logs/events.jsonl`. Snapshot akun opsional: `data/account.json` (equity, peak, session_start, positions). Jurnal paper opsional: `data/paper.json`.

## Kill-switch

Kalau banner merah menyala, baca alasan di halaman RISK. Untuk menyalakan lagi sistem trading, hapus manual `logs\KILL_SWITCH.lock`. Dashboard tidak menghapus file itu.

## API key

Disimpan di `.env` (sudah di `.gitignore`) secara atomik. UI hanya menampilkan "Terisi" dan 4 karakter terakhir. Jangan tempel key ke chat, log, atau screenshot.

## Config

Perubahan lewat halaman Config menulis `data/config.json`, membuat backup di `data/backups/`, dan mencatat audit. Berlaku setelah proses trading dijalankan ulang, bukan di tengah sesi yang sudah memuat `config.py`.

Batas yang tidak bisa dilanggar UI ada di `dashboard_api/hard_limits.py` (misalnya risiko per trade profil standard maks 5%, rugi sesi dan drawdown tidak boleh dinaikkan melewati 5% dan 15%).

## Troubleshooting

- **Backend tidak terhubung:** pastikan tidak ada proses lain di port 8765, lalu jalankan ulang skrip. Server hanya bind `127.0.0.1`.
- **Halaman kosong / token ditolak:** buka lewat http://127.0.0.1:5173 atau http://localhost:5173, bukan lewat IP lain.
- **Event tidak muncul di mode live:** sistem trading belum memanggil `emit_event`. Mode mock tidak membaca MT5.
- **Komisi kuning:** `commission_per_lot_usd` masih 7.0. Isi nilai asli di Config lalu centang "Saya sudah cek komisi asli akun".
- **Tes prompt nonaktif:** isi `XAI_API_KEY` dan nama model dari dokumentasi xAI. Dashboard tidak menebak nama model.

## Keamanan (BAGIAN 6)

1. Bind `127.0.0.1` saja, CORS hanya origin Vite lokal.
2. Header `Host` selain localhost ditolak.
3. PUT/POST butuh `X-Dashboard-Token` dari `/api/bootstrap` (origin harus sah).
4. `/api/keys` tidak mengembalikan nilai key. Tes `test_key_never_leaks`.
5. Nama agent dan simbol dari whitelist. Input divalidasi Pydantic. Error validasi tidak mengirim field `input`.
6. `.env`, `logs/`, dan `data/backups/` ada di `.gitignore`.
7. Prompt dan output AI ditampilkan sebagai teks React, tanpa `dangerouslySetInnerHTML`.
8. Tidak ada `eval` / eksekusi kode dari prompt.
9. Hard limit diuji di `dashboard_api/tests/test_dashboard.py`. Tidak ada endpoint order atau reset kill-switch.
