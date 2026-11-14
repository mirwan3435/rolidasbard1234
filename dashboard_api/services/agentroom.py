"""State ruangan agen dari heartbeat dan event terakhir."""
from datetime import datetime, timezone

from dashboard_api.services import events
from dashboard_api.services.agent_registry import SPECS


def _age(ts):
    if not ts:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            stamp = datetime.strptime(ts, fmt).replace(tzinfo=timezone.utc)
            return (datetime.now(timezone.utc) - stamp).total_seconds()
        except ValueError:
            continue
    return None


def state():
    recent = events.query_events(limit=400)
    latest = {}
    counts = {}
    handoffs = []
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for event in recent:
        agent = event.get("agent")
        if agent not in SPECS:
            continue
        latest.setdefault(agent, event)
        if str(event.get("ts") or "").startswith(today):
            counts[agent] = counts.get(agent, 0) + 1
        if event.get("type") in {"handoff", "signal"}:
            handoffs.append({"ts": event.get("ts"), "agent": agent, "msg": event.get("summary") or event.get("msg")})
    agents = []
    for name, spec in SPECS.items():
        event = latest.get(name)
        age = _age(event.get("ts")) if event else None
        if event is None or age is None:
            mode = "offline"
        elif event.get("level") == "error" or event.get("type") == "error":
            mode = "error"
        elif age < 30:
            mode = "working"
        elif age < 300:
            mode = "idle"
        else:
            mode = "offline"
        agents.append({
            "id": name,
            "label": spec["label"],
            "tier": spec["tier"],
            "color": spec["color"],
            "llm": spec["llm"],
            "state": mode,
            "task": (event or {}).get("summary") or (event or {}).get("msg") or "",
            "last_event": (event or {}).get("ts"),
            "age_sec": age,
            "events_today": counts.get(name, 0),
            "summary": spec["summary"],
        })
    return {"agents": agents, "handoffs": handoffs[:20], "source": "real" if recent else "sample"}
