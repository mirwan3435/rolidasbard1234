"""Konfigurasi risiko.

Nilai di bawah adalah bawaan (perilaku sama seperti sebelumnya bila
data/config.json tidak ada atau rusak). Dashboard menulis perubahan ke
data/config.json — bukan mengedit file ini dengan regex — lalu proses
trading membaca ulang saat sesi berikutnya dimulai.

Batas keras ada di dashboard_api/hard_limits.py, bukan di sini.
"""
import json
from pathlib import Path

VIRTUAL_CAPITAL = 95.0
ACTIVE_PROFILE = "standard"

PROFILES = {
    # Jalur utama: risiko per trade % dari modal, lot dihitung dari jarak stop
    "standard": {
        "risk_per_trade_pct": 2.0,
        "stop_pct_of_price": None,
        "max_open_positions": 2,
        "max_total_risk_pct": 4.0,
        "max_margin_pct": 30.0,
        "daily_loss_limit_pct": 5.0,
        "max_drawdown_pct": 15.0,
        "max_spread_to_stop_ratio": 0.15,
        "commission_per_lot_usd": 7.0,  # PLACEHOLDER: ganti sesuai komisi akun lu (round-turn per lot)
    },
    # Profil eksperimen dari blueprint awal: stop -8% dari harga, batas 10%
    "experiment_a": {
        "risk_per_trade_pct": 10.0,
        "stop_pct_of_price": 8.0,
        "max_open_positions": 2,
        "max_total_risk_pct": 10.0,
        "max_margin_pct": 30.0,
        "daily_loss_limit_pct": 5.0,
        "max_drawdown_pct": 15.0,
        "max_spread_to_stop_ratio": 0.15,
        "commission_per_lot_usd": 7.0,
    },
}


def _overlay_from_json():
    path = Path(__file__).resolve().parent / "data" / "config.json"
    if not path.is_file():
        return
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return
    if not isinstance(raw, dict):
        return
    global VIRTUAL_CAPITAL, ACTIVE_PROFILE
    capital = raw.get("virtual_capital")
    if isinstance(capital, (int, float)) and not isinstance(capital, bool) and capital > 0:
        VIRTUAL_CAPITAL = float(capital)
    if raw.get("active_profile") in PROFILES:
        ACTIVE_PROFILE = raw["active_profile"]
    incoming = raw.get("profiles")
    if not isinstance(incoming, dict):
        return
    for name, patch in incoming.items():
        if name not in PROFILES or not isinstance(patch, dict):
            continue
        base = PROFILES[name]
        for key, value in patch.items():
            if key not in base:
                continue
            current = base[key]
            if current is None:
                if value is None:
                    base[key] = None
                elif isinstance(value, (int, float)) and not isinstance(value, bool):
                    base[key] = float(value)
            elif isinstance(current, bool):
                continue
            elif isinstance(current, int) and isinstance(value, (int, float)) and not isinstance(value, bool):
                base[key] = int(value)
            elif isinstance(current, float) and isinstance(value, (int, float)) and not isinstance(value, bool):
                base[key] = float(value)


_overlay_from_json()
