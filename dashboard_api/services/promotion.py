"""Tangga promosi. Tidak ada tindakan untuk menyalakan live."""
from dashboard_api.services.config_store import read_config
from dashboard_api.services.state import paper_stats


def ladder():
    config = read_config()
    profile_name = config["active_profile"]
    profile = config["profiles"][profile_name]
    stats = paper_stats()
    verified = bool(profile.get("commission_verified"))
    trades = int(stats["trade_count"])
    expectancy = float(stats["avg_r"])
    dd = float(stats["max_drawdown_pct"])
    dd_limit = float(profile.get("max_drawdown_pct") or profile.get("kill_switch_drawdown_pct") or 15)
    checks = {
        "commission_verified": verified,
        "min_trades": trades >= 30,
        "expectancy_positive": expectancy > 0,
        "drawdown_inside": dd <= dd_limit,
    }
    backtest_pass = checks["commission_verified"] and checks["expectancy_positive"]
    paper_pass = backtest_pass and checks["min_trades"] and checks["drawdown_inside"]
    return {
        "active_profile": profile_name,
        "virtual_capital": config["virtual_capital"] if profile_name != "micro_10usd" else profile.get("virtual_capital_usd"),
        "stages": [
            {"id": "backtest", "label": "BACKTEST", "passed": backtest_pass, "locked": False},
            {"id": "paper", "label": "PAPER", "passed": paper_pass, "locked": False},
            {"id": "demo", "label": "DEMO", "passed": False, "locked": False, "note": "Butuh beberapa minggu demo tanpa pelanggaran. Belum ada data demo."},
            {"id": "micro_live", "label": "MICRO LIVE", "passed": False, "locked": True, "note": "Informasi saja. Dashboard tidak bisa menyalakan live."},
        ],
        "checks": checks,
        "stats": {"trades": trades, "avg_r": expectancy, "max_drawdown_pct": dd},
        "source": "real" if trades else "sample",
    }
