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
        "commission_verified": False,
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
        "commission_verified": False,
    },
    # Modal uji 10 USD di akun cent. Bukan jaminan hasil. Batas keras di hard_limits.py.
    "micro_10usd": {
        "virtual_capital_usd": 10.0,
        "account_type": "cent",
        "risk_per_trade_pct": 2.0,
        "skip_if_min_lot_risk_pct": 3.0,
        "max_portfolio_heat_pct": 5.0,
        "daily_loss_limit_pct": 5.0,
        "kill_switch_drawdown_pct": 15.0,
        "loss_streak_cooldown": {"3": 120, "5": "end_of_day"},
        "min_margin_level_pct": 500,
        "max_concurrent_positions": 2,
        "max_open_per_symbol": 1,
        "max_spread_atr_ratio": 0.15,
        "news_blackout_min": 20,
        "commission_per_lot_usd": 0.03,
        "commission_verified": False,
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
                if isinstance(value, bool):
                    base[key] = value
            elif isinstance(current, str) and isinstance(value, str):
                base[key] = value
            elif isinstance(current, dict) and isinstance(value, dict):
                base[key] = value
            elif isinstance(current, int) and isinstance(value, (int, float)) and not isinstance(value, bool):
                base[key] = int(value)
            elif isinstance(current, float) and isinstance(value, (int, float)) and not isinstance(value, bool):
                base[key] = float(value)


_overlay_from_json()
