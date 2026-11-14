"""Daftar keputusan dari event. Tidak membuat order."""
from dashboard_api.services import events


def _row(event):
    data = event.get("data") if isinstance(event.get("data"), dict) else {}
    signal = data.get("signal") if isinstance(data.get("signal"), dict) else {}
    risk = data.get("risk") if isinstance(data.get("risk"), dict) else {}
    grok = data.get("grok") if isinstance(data.get("grok"), dict) else None
    outcome = data.get("outcome")
    if outcome not in {"placed", "rejected", "skipped"}:
        outcome = "placed" if data.get("approved") else "rejected"
    return {
        "id": event.get("run_id") or f"{event.get('ts')}-{event.get('symbol')}",
        "ts": event.get("ts"),
        "symbol": event.get("symbol") or signal.get("symbol") or "",
        "strategy": signal.get("strategy") or data.get("strategy") or "",
        "direction": signal.get("direction") or data.get("direction") or "",
        "score": signal.get("score") if signal.get("score") is not None else data.get("score"),
        "outcome": outcome,
        "reason": data.get("reason") or ("; ".join(data.get("reasons") or []) if isinstance(data.get("reasons"), list) else event.get("summary")),
        "signal": signal,
        "scores": data.get("scores") or signal.get("score_components") or {},
        "grok": grok,
        "risk": {
            "passed": risk.get("passed") or [],
            "failed": risk.get("failed") or (data.get("reasons") if not data.get("approved") else []),
            "lot": risk.get("lot", data.get("lot")),
            "risk_pct": risk.get("risk_pct"),
        },
        "source": data.get("source") or "real",
    }


def query(symbol="", strategy="", outcome="", since="", until="", limit=50):
    rows = []
    for event in events.query_events(limit=500):
        if event.get("type") not in {"decision", "veto"} and event.get("agent") != "RISK":
            continue
        if event.get("agent") not in {"RISK", "CORE", "EXEC", "PORTFOLIO"} and event.get("type") != "decision":
            continue
        row = _row(event)
        if symbol and row["symbol"] != symbol:
            continue
        if strategy and row["strategy"] != strategy:
            continue
        if outcome and row["outcome"] != outcome:
            continue
        ts = row["ts"] or ""
        if since and ts < since:
            continue
        if until and ts > until:
            continue
        rows.append(row)
        if len(rows) >= limit:
            break
    return rows


def get_one(decision_id: str):
    for row in query(limit=500):
        if row["id"] == decision_id:
            return row
    raise KeyError(decision_id)
