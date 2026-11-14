"""Catatan pemakaian token. Harga tidak dikarang."""
import json
from datetime import datetime, timedelta, timezone

from dashboard_api.paths import DATA, ensure_dirs
from dashboard_api.services import events


class BudgetExceeded(RuntimeError):
    pass


def _path():
    return DATA / "costs.jsonl"


def record(agent: str, model: str, tokens_in: int, tokens_out: int):
    ensure_dirs()
    row = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
        "agent": agent,
        "model": model,
        "tokens_in": int(tokens_in),
        "tokens_out": int(tokens_out),
    }
    with _path().open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row) + "\n")
    events.append_event({
        **{"ts": row["ts"], "agent": agent, "type": "cost", "symbol": "", "level": "info"},
        "summary": f"Token {tokens_in + tokens_out}",
        "msg": f"Token {tokens_in + tokens_out}",
        "data": {"model": model, "tokens_in": tokens_in, "tokens_out": tokens_out, "source": "real"},
        "run_id": "",
    })
    return row


def _rows():
    path = _path()
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def summary():
    from dashboard_api.services.state import read_settings
    settings = read_settings()
    now = datetime.now(timezone.utc)
    day = now - timedelta(days=1)
    week = now - timedelta(days=7)
    rows = _rows()
    def stamp(row):
        try:
            return datetime.strptime(row["ts"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
        except (KeyError, ValueError):
            return None
    today = []
    last7 = []
    for row in rows:
        ts = stamp(row)
        if ts is None:
            continue
        if ts >= week:
            last7.append(row)
        if ts >= day:
            today.append(row)
    pin = settings.get("grok_price_in_per_million")
    pout = settings.get("grok_price_out_per_million")

    def tokens(items):
        return sum(int(r.get("tokens_in") or 0) + int(r.get("tokens_out") or 0) for r in items)

    def usd(items):
        if pin is None or pout is None:
            return None
        cost = 0.0
        for row in items:
            cost += int(row.get("tokens_in") or 0) / 1_000_000 * float(pin)
            cost += int(row.get("tokens_out") or 0) / 1_000_000 * float(pout)
        return round(cost, 4)

    by_agent = {}
    for row in today:
        name = row.get("agent") or "?"
        by_agent[name] = by_agent.get(name, 0) + int(row.get("tokens_in") or 0) + int(row.get("tokens_out") or 0)
    used = tokens(today)
    budget = int(settings["grok_daily_token_budget"])
    return {
        "tokens_today": used,
        "calls_today": len(today),
        "tokens_7d": tokens(last7),
        "calls_7d": len(last7),
        "usd_today": usd(today),
        "usd_7d": usd(last7),
        "prices_set": pin is not None and pout is not None,
        "price_note": "" if pin is not None and pout is not None else "Isi harga di pengaturan untuk melihat biaya USD.",
        "token_budget": budget,
        "usd_budget": settings.get("grok_daily_usd_budget"),
        "by_agent": by_agent,
        "recent": rows[-30:],
        "source": "real" if rows else "sample",
    }


def budget_guard():
    snap = summary()
    if snap["tokens_today"] >= snap["token_budget"]:
        raise BudgetExceeded("Budget token harian habis")
    if snap["usd_budget"] is not None and snap["usd_today"] is not None and snap["usd_today"] >= float(snap["usd_budget"]):
        raise BudgetExceeded("Budget USD harian habis")
