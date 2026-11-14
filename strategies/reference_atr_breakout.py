"""REFERENSI, bukan detektor produksi.

Breakout ATR supaya pipeline Lab bisa diuji sebelum plugin SMC/ICT ada.
kind = reference. Hasilnya bukan edge yang sudah dibuktikan.
"""
id = "reference_atr_breakout"
kind = "reference"
param_schema = {
    "type": "object",
    "properties": {
        "atr_period": {"type": "integer", "minimum": 5, "maximum": 50, "default": 14},
        "atr_sl_mult": {"type": "number", "minimum": 0.5, "maximum": 3, "default": 1.2},
        "atr_tp_mult": {"type": "number", "minimum": 1, "maximum": 5, "default": 2.4},
    },
}


def _atr(candles, period, index):
    if index < period:
        return None
    total = 0.0
    for i in range(index - period + 1, index + 1):
        prev = candles[i - 1]["close"] if i else candles[i]["close"]
        high = candles[i]["high"]
        low = candles[i]["low"]
        total += max(high - low, abs(high - prev), abs(low - prev))
    return total / period


def detect(candles, ctx):
    """Hanya melihat candle yang diberikan. Tidak mengintip bar berikutnya."""
    ctx = ctx or {}
    period = int(ctx.get("atr_period") or 14)
    if len(candles) < period + 2:
        return None
    index = len(candles) - 1
    atr = _atr(candles, period, index)
    if not atr or atr <= 0:
        return None
    window = candles[index - period:index]
    highest = max(bar["high"] for bar in window)
    lowest = min(bar["low"] for bar in window)
    close = candles[index]["close"]
    if close > highest:
        direction = "buy"
    elif close < lowest:
        direction = "sell"
    else:
        return None
    return {
        "strategy": id,
        "kind": kind,
        "direction": direction,
        "atr": atr,
        "sl_distance": atr * float(ctx.get("atr_sl_mult") or 1.2),
        "tp_distance": atr * float(ctx.get("atr_tp_mult") or 2.4),
        "signal_index": index,
        "source": "sample",
    }
