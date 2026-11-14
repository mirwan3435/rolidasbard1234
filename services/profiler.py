"""PROFILER: status pair tetap hypothesis sampai sampel dan expectancy terpenuhi."""
import json
from pathlib import Path


def status_for(trades: int, expectancy_r: float, min_trades: int = 100):
    if trades >= min_trades and expectancy_r > 0:
        return "validated"
    if trades > 0 and expectancy_r < 0:
        return "disabled"
    return "hypothesis"


def from_runs(folder: Path):
    rows = []
    if not folder.is_dir():
        return rows
    for path in folder.glob("*.json"):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        kpis = doc.get("kpis") or {}
        count = int(kpis.get("trade_count") or 0)
        expectancy = float(kpis.get("expectancy_r") or 0)
        rows.append({
            "strategy": doc.get("strategy"),
            "symbol": doc.get("symbol"),
            "trades": count,
            "expectancy_r": expectancy,
            "status": status_for(count, expectancy),
            "source": "real" if doc.get("status") == "done" else "sample",
        })
    return rows
