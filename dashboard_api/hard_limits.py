"""Batas keras config. Diedit hanya lewat kode, tidak ada endpoint untuk mengubahnya.

daily_loss_limit_pct dan max_drawdown_pct tidak boleh dinaikkan melewati bawaan.
risk_per_trade_pct profil standard dibatasi 5.
Profil micro_10usd tidak boleh dilonggarkan melewati angka di KONSEP_TRADING_BOT.md.
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
            "commission_verified": False,
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
            "commission_verified": False,
        },
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
    },
}

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
    "micro_10usd": {
        "virtual_capital_usd": 10.0,
        "risk_per_trade_pct": 2.0,
        "skip_if_min_lot_risk_pct": 3.0,
        "max_portfolio_heat_pct": 5.0,
        "daily_loss_limit_pct": 5.0,
        "kill_switch_drawdown_pct": 15.0,
        "min_margin_level_pct": 2000,
        "max_concurrent_positions": 2,
        "max_open_per_symbol": 1,
        "max_spread_atr_ratio": 0.15,
        "news_blackout_min": 120,
        "commission_per_lot_usd": 5.0,
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
    "virtual_capital_usd": 10.0,
    "skip_if_min_lot_risk_pct": 0.5,
    "max_portfolio_heat_pct": 0.5,
    "kill_switch_drawdown_pct": 1.0,
    "min_margin_level_pct": 100,
    "max_concurrent_positions": 1,
    "max_open_per_symbol": 1,
    "max_spread_atr_ratio": 0.01,
    "news_blackout_min": 0,
}

VIRTUAL_CAPITAL_MIN = 10.0
VIRTUAL_CAPITAL_MAX = 1_000_000.0

PROFILE_NAMES = ("standard", "experiment_a", "micro_10usd")
INT_FIELDS = {"max_open_positions", "max_concurrent_positions", "max_open_per_symbol", "news_blackout_min"}
NULLABLE = {"stop_pct_of_price"}
BOOL_FIELDS = {"commission_verified"}
STRING_FIELDS = {"account_type": ("cent", "standard")}
DICT_FIELDS = {"loss_streak_cooldown"}

CLASSIC_FIELDS = [
    "risk_per_trade_pct",
    "stop_pct_of_price",
    "max_open_positions",
    "max_total_risk_pct",
    "max_margin_pct",
    "daily_loss_limit_pct",
    "max_drawdown_pct",
    "max_spread_to_stop_ratio",
    "commission_per_lot_usd",
    "commission_verified",
]

MICRO_FIELDS = [
    "virtual_capital_usd",
    "account_type",
    "risk_per_trade_pct",
    "skip_if_min_lot_risk_pct",
    "max_portfolio_heat_pct",
    "daily_loss_limit_pct",
    "kill_switch_drawdown_pct",
    "loss_streak_cooldown",
    "min_margin_level_pct",
    "max_concurrent_positions",
    "max_open_per_symbol",
    "max_spread_atr_ratio",
    "news_blackout_min",
    "commission_per_lot_usd",
    "commission_verified",
]

FIELDS_BY_PROFILE = {
    "standard": CLASSIC_FIELDS,
    "experiment_a": CLASSIC_FIELDS,
    "micro_10usd": MICRO_FIELDS,
}

# Budget Grok. Menurunkan boleh, menaikkan melewati ceiling tidak.
GROK_TOKEN_BUDGET_MIN = 1_000
GROK_TOKEN_BUDGET_MAX = 2_000_000
GROK_USD_BUDGET_MAX = 100.0
