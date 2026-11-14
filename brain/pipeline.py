"""Satu putaran baca-saja. Hasilnya niat paper, bukan order broker."""
import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from brain.signal import validate_signal
from services.context import build as build_context
from services.portfolio import allow
from services.profiler import status_for
from services.watchdog import check as watchdog_check
from strategies import common


DETECTORS = [
    common.detect_smc,
    common.detect_ict,
    common.detect_breakout,
    common.detect_crt,
    common.detect_snd,
    common.detect_sbr_rbs,
    common.detect_session_sweep,
    common.detect_wyckoff,
    common.detect_mean_reversion,
]


def _signal_from(hit, symbol, broker_symbol, bars):
    last = bars[-1]
    entry = float(last["close"])
    sl_dist = float(hit["sl_distance"])
    tp_dist = float(hit["tp_distance"])
    if hit["direction"] == "buy":
        sl = entry - sl_dist
        tp = entry + tp_dist
    else:
        sl = entry + sl_dist
        tp = entry - tp_dist
    now = datetime.now(timezone.utc)
    score = 70
    return {
        "id": uuid.uuid4().hex,
        "ts": now.isoformat(),
        "symbol": symbol,
        "broker_symbol": broker_symbol,
        "direction": hit["direction"],
        "strategy": hit["strategy"],
        "mode": "scalp",
        "tf_entry": "M5",
        "tf_bias": "H1",
        "order_type": "market",
        "entry": entry,
        "sl": sl,
        "tp": tp,
        "rr": round(tp_dist / sl_dist, 4) if sl_dist else 0,
        "atr": float(hit["atr"]),
        "spread_at_signal": 0,
        "tags": hit.get("tags") or [],
        "score_components": {"trigger": 20, "rr": 10},
        "score": score,
        "expectancy_ref": None,
        "valid_until": (now + timedelta(minutes=15)).isoformat(),
        "invalidation": "Tutup kembali ke dalam zona",
        "source": "sample",
    }


def preview(symbol: str, broker_symbol: str, bars, open_symbols=(), heat_pct=0.0, heat_limit=5.0, out_dir: Path | None = None):
    """Jalankan alur sampai niat. EXEC tidak menyentuh terminal."""
    ctx = build_context(bars, Path("data/calendar.csv"))
    watchdog = watchdog_check(0 if bars else None, True, bool(bars))
    hits = [fn(bars, {}) for fn in DETECTORS]
    hits = [hit for hit in hits if hit]
    if not hits:
        return {"outcome": "skipped", "reason": "Tidak ada detektor yang menyala", "source": "sample", "context": ctx}
    signal = _signal_from(hits[0], symbol, broker_symbol, bars)
    checked = validate_signal(signal)
    if not checked["ok"]:
        return {"outcome": "rejected", "reason": checked["reason"], "source": "sample"}
    if signal["score"] < 80:
        signal["source"] = "sample"
        outcome = {"outcome": "skipped", "reason": "Skor di bawah 80. Hipotesis, belum high probability.", "signal": signal}
    else:
        ok, reason = allow(symbol, open_symbols, heat_pct, heat_limit)
        outcome = {"outcome": "paper_intent" if ok else "rejected", "reason": reason, "signal": signal}
    outcome["profiler"] = status_for(0, 0)
    outcome["watchdog"] = watchdog
    outcome["context"] = ctx
    outcome["verdict"] = {"verdict": "reject", "reason": "Grok tidak dipanggil pada pratinjau ini"}
    outcome["source"] = "sample"
    if out_dir is not None and outcome["outcome"] == "paper_intent":
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{signal['id']}.json").write_text(json.dumps(outcome, ensure_ascii=False, indent=2), encoding="utf-8")
    return outcome
