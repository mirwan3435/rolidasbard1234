import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timezone

TIMEFRAMES = {
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
}


def connect():
    if not mt5.initialize():
        raise RuntimeError(f"Gagal konek MT5: {mt5.last_error()}")


def server_offset_hours(symbol="EURUSD"):
    """Selisih jam server broker terhadap UTC, dalam jam."""
    mt5.symbol_select(symbol, True)
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise RuntimeError(f"Tick kosong untuk {symbol}")
    now_utc = datetime.now(timezone.utc).timestamp()
    return round((tick.time - now_utc) / 3600)


def fetch_rates(symbol, tf="M15", bars=1000):
    mt5.symbol_select(symbol, True)
    rates = mt5.copy_rates_from_pos(symbol, TIMEFRAMES[tf], 0, bars)
    if rates is None or len(rates) == 0:
        raise RuntimeError(f"Data kosong {symbol} {tf}: {mt5.last_error()}")
    df = pd.DataFrame(rates)
    offset = server_offset_hours(symbol)
    df["time_utc"] = pd.to_datetime(df["time"], unit="s") - pd.Timedelta(hours=offset)
    df["time_wita"] = df["time_utc"] + pd.Timedelta(hours=8)
    return df[["time_utc", "time_wita", "open", "high", "low", "close", "tick_volume", "spread"]]
