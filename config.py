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
