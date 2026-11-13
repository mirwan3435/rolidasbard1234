"""Batas keras config. Diedit hanya lewat kode, tidak ada endpoint untuk mengubahnya.

daily_loss_limit_pct dan max_drawdown_pct tidak boleh dinaikkan melewati bawaan saat ini.
risk_per_trade_pct profil standard dibatasi 5.
"""

DEFAULTS = {
    "virtual_capital": 95.0,
    "active_profile": "standard",
    "commission_confirmed": False,
    "profiles": {
        "standard": {
            "risk_per_trade_pct": 2.0,
            "stop_pct_of_price": None,
            "max_open_positions": 2,
            "max_total_risk_pct": 4.0,
            "max_margin_pct": 30.0,
            "daily_loss_limit_pct": 5.0,
            "max_drawdown_pct": 15.0,
            "max_spread_to_stop_ratio": 0.15,
            "commission_per_lot_usd": 7.0,
        },
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
    },
}

# Nilai maksimum yang boleh disimpan. Menurunkan batas boleh.
CEILING = {
    "standard": {
        "risk_per_trade_pct": 5.0,
        "max_open_positions": 3,
        "max_total_risk_pct": 6.0,
        "max_margin_pct": 40.0,
        "daily_loss_limit_pct": 5.0,
        "max_drawdown_pct": 15.0,
        "max_spread_to_stop_ratio": 0.25,
        "commission_per_lot_usd": 50.0,
    },
    "experiment_a": {
        "risk_per_trade_pct": 15.0,
        "stop_pct_of_price": 12.0,
        "max_open_positions": 3,
        "max_total_risk_pct": 15.0,
        "max_margin_pct": 40.0,
        "daily_loss_limit_pct": 5.0,
        "max_drawdown_pct": 15.0,
        "max_spread_to_stop_ratio": 0.25,
        "commission_per_lot_usd": 50.0,
    },
}

FLOOR = {
    "risk_per_trade_pct": 0.1,
    "max_open_positions": 1,
    "max_total_risk_pct": 0.2,
    "max_margin_pct": 1.0,
    "daily_loss_limit_pct": 0.5,
    "max_drawdown_pct": 1.0,
    "max_spread_to_stop_ratio": 0.01,
    "commission_per_lot_usd": 0.0,
    "stop_pct_of_price": 0.5,
}

VIRTUAL_CAPITAL_MIN = 10.0
VIRTUAL_CAPITAL_MAX = 1_000_000.0

PROFILE_NAMES = ("standard", "experiment_a")
INT_FIELDS = {"max_open_positions"}
NULLABLE = {"stop_pct_of_price"}
