"""JOURNAL: catat keputusan ke SQLite. Tidak menyimpan API key."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def _connect(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.execute(
        "CREATE TABLE IF NOT EXISTS decisions (id TEXT PRIMARY KEY, ts TEXT, symbol TEXT, payload TEXT)"
    )
    return con


def write_decision(path: Path, decision_id: str, symbol: str, payload: dict):
    con = _connect(path)
    try:
        con.execute(
            "INSERT OR REPLACE INTO decisions (id, ts, symbol, payload) VALUES (?, ?, ?, ?)",
            (decision_id, datetime.now(timezone.utc).isoformat(), symbol, json.dumps(payload, ensure_ascii=False)),
        )
        con.commit()
    finally:
        con.close()
    return {"ok": True, "source": "real"}
