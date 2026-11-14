"""DATA: baca candle dari CSV atau, kalau terminal ada, dari MT5 read-only."""
import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path


def load_csv(path: Path):
    if not path.is_file():
        return {"bars": [], "source": "sample", "detail": "File history belum ada"}
    rows = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            lowered = {(k or "").strip().lower(): v for k, v in row.items()}
            try:
                rows.append({
                    "time": lowered["time"],
                    "open": float(lowered["open"]),
                    "high": float(lowered["high"]),
                    "low": float(lowered["low"]),
                    "close": float(lowered["close"]),
                    "volume": float(lowered.get("volume") or 0),
                })
            except (KeyError, TypeError, ValueError):
                continue
    return {"bars": rows, "source": "real" if rows else "sample", "detail": f"{len(rows)} bar"}


def load_mt5(symbol: str, timeframe: str, days: int = 5):
    try:
        import MetaTrader5 as mt5
    except Exception:
        return {"bars": [], "source": "sample", "detail": "MetaTrader5 belum terpasang"}
    tf = {"M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15}.get(timeframe)
    if tf is None or not mt5.initialize():
        return {"bars": [], "source": "sample", "detail": "Terminal tidak merespons"}
    try:
        end = datetime.now(timezone.utc)
        rates = mt5.copy_rates_range(symbol, tf, end - timedelta(days=days), end)
    except Exception:
        rates = None
    finally:
        mt5.shutdown()
    if rates is None:
        return {"bars": [], "source": "sample", "detail": "copy_rates_range kosong"}
    bars = [{
        "time": datetime.fromtimestamp(int(bar["time"]), timezone.utc).isoformat(),
        "open": float(bar["open"]),
        "high": float(bar["high"]),
        "low": float(bar["low"]),
        "close": float(bar["close"]),
        "volume": float(bar["tick_volume"]),
    } for bar in rates]
    return {"bars": bars, "source": "real", "detail": f"{len(bars)} bar MT5"}
