"""Matematika candle bersama. Tidak mengintip bar di luar jendela yang diberikan."""
import inspect


SCHEMA = {
    "type": "object",
    "properties": {
        "atr_period": {"type": "integer", "minimum": 5, "maximum": 50, "default": 14},
        "atr_sl_mult": {"type": "number", "minimum": 0.5, "maximum": 3, "default": 1.2},
        "atr_tp_mult": {"type": "number", "minimum": 1, "maximum": 5, "default": 2.4},
    },
}


def atr(candles, period):
    if len(candles) < period + 1:
        return None
    total = 0.0
    start = len(candles) - period
    for i in range(start, len(candles)):
        prev = candles[i - 1]["close"]
        high = candles[i]["high"]
        low = candles[i]["low"]
        total += max(high - low, abs(high - prev), abs(low - prev))
    value = total / period
    return value if value > 0 else None


def _swing_high(candles, left=2):
    end = len(candles) - left - 1
    for i in range(end, left - 1, -1):
        high = candles[i]["high"]
        if all(high > candles[i - k]["high"] and high > candles[i + k]["high"] for k in range(1, left + 1)):
            return i, high
    return None


def _swing_low(candles, left=2):
    end = len(candles) - left - 1
    for i in range(end, left - 1, -1):
        low = candles[i]["low"]
        if all(low < candles[i - k]["low"] and low < candles[i + k]["low"] for k in range(1, left + 1)):
            return i, low
    return None


def _pack(strategy, direction, candles, ctx, sl_distance, tp_distance, tags):
    period = int((ctx or {}).get("atr_period") or 14)
    value = atr(candles, period)
    if not value or sl_distance <= 0 or tp_distance <= 0:
        return None
    return {
        "strategy": strategy,
        "kind": "detector",
        "direction": direction,
        "atr": value,
        "sl_distance": sl_distance,
        "tp_distance": tp_distance,
        "tags": tags,
        "signal_index": len(candles) - 1,
        "source": "sample",
    }


def detect_smc(candles, ctx):
    """BOS: close melewati swing terakhir. SL di swing lawan, TP kelipatan ATR."""
    if len(candles) < 12:
        return None
    value = atr(candles, int((ctx or {}).get("atr_period") or 14))
    if not value:
        return None
    high = _swing_high(candles)
    low = _swing_low(candles)
    close = candles[-1]["close"]
    sl_mult = float((ctx or {}).get("atr_sl_mult") or 1.2)
    tp_mult = float((ctx or {}).get("atr_tp_mult") or 2.4)
    if high and close > high[1]:
        return _pack("smc", "buy", candles, ctx, value * sl_mult, value * tp_mult, ["bos"])
    if low and close < low[1]:
        return _pack("smc", "sell", candles, ctx, value * sl_mult, value * tp_mult, ["bos"])
    return None


def detect_ict(candles, ctx):
    """Sweep high/low 8 bar lalu close kembali ke dalam."""
    if len(candles) < 12:
        return None
    value = atr(candles, int((ctx or {}).get("atr_period") or 14))
    if not value:
        return None
    prior = candles[-9:-1]
    last = candles[-1]
    hi = max(bar["high"] for bar in prior)
    lo = min(bar["low"] for bar in prior)
    sl_mult = float((ctx or {}).get("atr_sl_mult") or 1.2)
    tp_mult = float((ctx or {}).get("atr_tp_mult") or 2.4)
    if last["high"] > hi and last["close"] < hi:
        return _pack("ict", "sell", candles, ctx, value * sl_mult, value * tp_mult, ["liquidity_sweep"])
    if last["low"] < lo and last["close"] > lo:
        return _pack("ict", "buy", candles, ctx, value * sl_mult, value * tp_mult, ["liquidity_sweep"])
    return None


def detect_breakout(candles, ctx):
    """Body menutup di luar range 10 bar sebelumnya."""
    if len(candles) < 14:
        return None
    value = atr(candles, int((ctx or {}).get("atr_period") or 14))
    if not value:
        return None
    window = candles[-11:-1]
    last = candles[-1]
    hi = max(bar["high"] for bar in window)
    lo = min(bar["low"] for bar in window)
    sl_mult = float((ctx or {}).get("atr_sl_mult") or 1.2)
    tp_mult = float((ctx or {}).get("atr_tp_mult") or 2.4)
    if last["close"] > hi and last["close"] > last["open"]:
        return _pack("breakout", "buy", candles, ctx, max(last["close"] - lo, value * sl_mult), value * tp_mult, ["breakout"])
    if last["close"] < lo and last["close"] < last["open"]:
        return _pack("breakout", "sell", candles, ctx, max(hi - last["close"], value * sl_mult), value * tp_mult, ["breakout"])
    return None


def detect_crt(candles, ctx):
    """Candle acuan di-sweep, close kembali ke dalam range acuan."""
    if len(candles) < 8:
        return None
    value = atr(candles, int((ctx or {}).get("atr_period") or 14))
    if not value:
        return None
    reference = candles[-6]
    last = candles[-1]
    sl_mult = float((ctx or {}).get("atr_sl_mult") or 1.2)
    tp_mult = float((ctx or {}).get("atr_tp_mult") or 2.4)
    if last["low"] < reference["low"] and last["close"] > reference["low"] and last["close"] < reference["high"]:
        return _pack("crt", "buy", candles, ctx, value * sl_mult, value * tp_mult, ["crt"])
    if last["high"] > reference["high"] and last["close"] < reference["high"] and last["close"] > reference["low"]:
        return _pack("crt", "sell", candles, ctx, value * sl_mult, value * tp_mult, ["crt"])
    return None


def detect_snd(candles, ctx):
    """Zona demand/supply sederhana: tiga candle impuls lalu sentuh kembali."""
    if len(candles) < 8:
        return None
    value = atr(candles, int((ctx or {}).get("atr_period") or 14))
    if not value:
        return None
    base = candles[-4]
    last = candles[-1]
    sl_mult = float((ctx or {}).get("atr_sl_mult") or 1.2)
    tp_mult = float((ctx or {}).get("atr_tp_mult") or 2.4)
    if base["close"] > base["open"] and last["low"] <= base["high"] and last["close"] > base["open"]:
        return _pack("snd", "buy", candles, ctx, value * sl_mult, value * tp_mult, ["snd"])
    if base["close"] < base["open"] and last["high"] >= base["low"] and last["close"] < base["open"]:
        return _pack("snd", "sell", candles, ctx, value * sl_mult, value * tp_mult, ["snd"])
    return None


def detect_sbr_rbs(candles, ctx):
    """Level yang tertembus lalu ditolak pada tes ulang."""
    if len(candles) < 16:
        return None
    value = atr(candles, int((ctx or {}).get("atr_period") or 14))
    if not value:
        return None
    level = candles[-12]["close"]
    broke_down = any(bar["close"] < level for bar in candles[-8:-2])
    broke_up = any(bar["close"] > level for bar in candles[-8:-2])
    last = candles[-1]
    sl_mult = float((ctx or {}).get("atr_sl_mult") or 1.2)
    tp_mult = float((ctx or {}).get("atr_tp_mult") or 2.4)
    if broke_down and last["high"] >= level and last["close"] < level:
        return _pack("sbr_rbs", "sell", candles, ctx, value * sl_mult, value * tp_mult, ["sbr_rbs"])
    if broke_up and last["low"] <= level and last["close"] > level:
        return _pack("sbr_rbs", "buy", candles, ctx, value * sl_mult, value * tp_mult, ["sbr_rbs"])
    return None


def detect_orderflow_proxy(candles, ctx):
    """Konfirmasi saja. Tidak menghasilkan entry, SL, atau TP."""
    return None


def detect_session_sweep(candles, ctx):
    """Range awal jendela disapu di bar terakhir."""
    if len(candles) < 20:
        return None
    value = atr(candles, int((ctx or {}).get("atr_period") or 14))
    if not value:
        return None
    opening = candles[:8]
    hi = max(bar["high"] for bar in opening)
    lo = min(bar["low"] for bar in opening)
    last = candles[-1]
    sl_mult = float((ctx or {}).get("atr_sl_mult") or 1.2)
    tp_mult = float((ctx or {}).get("atr_tp_mult") or 2.4)
    if last["high"] > hi and last["close"] < hi:
        return _pack("session_sweep", "sell", candles, ctx, value * sl_mult, value * tp_mult, ["session_sweep"])
    if last["low"] < lo and last["close"] > lo:
        return _pack("session_sweep", "buy", candles, ctx, value * sl_mult, value * tp_mult, ["session_sweep"])
    return None


def detect_wyckoff(candles, ctx):
    """Spring atau upthrust terhadap range tengah jendela."""
    if len(candles) < 16:
        return None
    value = atr(candles, int((ctx or {}).get("atr_period") or 14))
    if not value:
        return None
    box = candles[-12:-1]
    hi = max(bar["high"] for bar in box)
    lo = min(bar["low"] for bar in box)
    last = candles[-1]
    sl_mult = float((ctx or {}).get("atr_sl_mult") or 1.2)
    tp_mult = float((ctx or {}).get("atr_tp_mult") or 2.4)
    if last["low"] < lo and last["close"] > lo:
        return _pack("wyckoff", "buy", candles, ctx, value * sl_mult, value * tp_mult, ["wyckoff"])
    if last["high"] > hi and last["close"] < hi:
        return _pack("wyckoff", "sell", candles, ctx, value * sl_mult, value * tp_mult, ["wyckoff"])
    return None


def detect_mean_reversion(candles, ctx):
    """Hanya jika range sempit dibanding ATR, lalu close menolak ekstrem."""
    if len(candles) < 16:
        return None
    value = atr(candles, int((ctx or {}).get("atr_period") or 14))
    if not value:
        return None
    window = candles[-15:-1]
    hi = max(bar["high"] for bar in window)
    lo = min(bar["low"] for bar in window)
    if (hi - lo) > value * 4:
        return None
    last = candles[-1]
    sl_mult = float((ctx or {}).get("atr_sl_mult") or 1.2)
    tp_mult = float((ctx or {}).get("atr_tp_mult") or 2.0)
    if last["low"] <= lo + (hi - lo) * 0.15 and last["close"] > last["open"]:
        return _pack("mean_reversion", "buy", candles, ctx, value * sl_mult, value * tp_mult, ["mean_reversion"])
    if last["high"] >= hi - (hi - lo) * 0.15 and last["close"] < last["open"]:
        return _pack("mean_reversion", "sell", candles, ctx, value * sl_mult, value * tp_mult, ["mean_reversion"])
    return None


FUNCS = {
    "bos": detect_smc,
    "choch": detect_smc,
    "order_block": detect_smc,
    "fvg": detect_smc,
    "smc": detect_smc,
    "liquidity_sweep": detect_ict,
    "power_of_3": detect_ict,
    "ict": detect_ict,
    "breakout": detect_breakout,
    "crt": detect_crt,
    "snd": detect_snd,
    "sbr_rbs": detect_sbr_rbs,
    "orderflow_proxy": detect_orderflow_proxy,
    "session_sweep": detect_session_sweep,
    "wyckoff": detect_wyckoff,
    "mean_reversion": detect_mean_reversion,
    "range": detect_mean_reversion,
}


def snippet_for(card_id: str):
    func = FUNCS.get(card_id)
    if func is None:
        return ""
    return inspect.getsource(func)
