"""Validasi Signal. Field tambahan dan SL di sisi yang salah ditolak."""
from datetime import datetime

REQUIRED = [
    "id", "ts", "symbol", "broker_symbol", "direction", "strategy", "mode", "tf_entry", "tf_bias",
    "order_type", "entry", "sl", "tp", "rr", "atr", "spread_at_signal", "tags", "score_components",
    "score", "valid_until", "invalidation",
]
ALLOWED = set(REQUIRED) | {"expectancy_ref", "source"}


def _parse(stamp):
    text = str(stamp).replace("Z", "+00:00")
    return datetime.fromisoformat(text)


def validate_signal(raw):
    if not isinstance(raw, dict):
        return {"ok": False, "reason": "Signal bukan objek"}
    extra = set(raw) - ALLOWED
    if extra:
        return {"ok": False, "reason": "Field tambahan ditolak"}
    missing = [key for key in REQUIRED if key not in raw]
    if missing:
        return {"ok": False, "reason": "Field wajib hilang"}
    if raw["direction"] not in {"buy", "sell"}:
        return {"ok": False, "reason": "Arah tidak dikenal"}
    if raw["mode"] not in {"scalp", "intraday", "swing"}:
        return {"ok": False, "reason": "Mode tidak dikenal"}
    if raw["order_type"] not in {"market", "limit", "stop"}:
        return {"ok": False, "reason": "Tipe tidak dikenal"}
    try:
        entry = float(raw["entry"])
        sl = float(raw["sl"])
        tp = float(raw["tp"])
        rr = float(raw["rr"])
        atr = float(raw["atr"])
        score = int(raw["score"])
        ts = _parse(raw["ts"])
        until = _parse(raw["valid_until"])
    except (TypeError, ValueError):
        return {"ok": False, "reason": "Angka atau waktu tidak valid"}
    if atr <= 0 or rr < 0 or not 0 <= score <= 100:
        return {"ok": False, "reason": "Rentang angka ditolak"}
    risk = (entry - sl) if raw["direction"] == "buy" else (sl - entry)
    reward = (tp - entry) if raw["direction"] == "buy" else (entry - tp)
    if risk <= 0 or reward <= 0:
        return {"ok": False, "reason": "SL atau TP di sisi yang salah"}
    if abs((reward / risk) - rr) > 0.05:
        return {"ok": False, "reason": "RR tidak sesuai entry SL TP"}
    if until <= ts:
        return {"ok": False, "reason": "Sinyal sudah kedaluwarsa"}
    if len(str(raw["invalidation"])) > 240:
        return {"ok": False, "reason": "Invalidation terlalu panjang"}
    return {"ok": True, "reason": ""}
