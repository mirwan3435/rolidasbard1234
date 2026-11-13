"""Tulis satu event ke logs/events.jsonl.

Sistem trading memanggil helper ini. Dashboard hanya membaca file tersebut.
Helper ini tidak mengimpor risk_engine dan tidak mengirim order.

Contoh:

    from emit_event import emit_event
    emit_event(
        "RISK",
        "decision",
        "Trade ditolak, lot minimum kegedean",
        symbol="XAUUSDm",
        data={"approved": False, "reasons": ["Lot minimum 0.01 butuh risiko ..."]},
    )
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOG_DIR = Path(os.environ.get("DASHBOARD_LOG_DIR", ROOT / "logs"))
EVENT_FILE = LOG_DIR / "events.jsonl"

AGENTS = {"DATA", "SCOPE", "WHALES", "DEBATE", "RISK", "EXEC", "CORE", "SYSTEM"}
TYPES = {"status", "input", "output", "decision", "error", "heartbeat", "config_change"}
LEVELS = {"debug", "info", "warn", "error"}


def emit_event(agent, type_, summary, symbol="", level="info", data=None, run_id=""):
    if agent not in AGENTS:
        raise ValueError(f"agent tidak dikenal: {agent}")
    if type_ not in TYPES:
        raise ValueError(f"type tidak dikenal: {type_}")
    if level not in LEVELS:
        raise ValueError(f"level tidak dikenal: {level}")
    event = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
        "agent": agent,
        "type": type_,
        "symbol": symbol or "",
        "level": level,
        "summary": str(summary)[:500],
        "data": data if isinstance(data, dict) else {},
        "run_id": run_id or "",
    }
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    line = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
    with EVENT_FILE.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    return event
