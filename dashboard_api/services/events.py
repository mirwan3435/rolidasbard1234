"""Antrean event di memori + tail file JSONL. Baris rusak dihitung, tidak menjatuhkan proses."""
import json
import threading
import time
from collections import deque
from datetime import datetime, timezone, timedelta

from dashboard_api.paths import ARCHIVE, AUDIT, EVENTS, LOGS, ensure_dirs

bus_recent = deque(maxlen=3000)
_sigs = deque(maxlen=3000)
corrupt_count = 0
_lock = threading.Lock()
_subscribers: list = []
_stop = threading.Event()
_loop = None


def _signature(event: dict):
    return (
        event.get("ts"),
        event.get("agent"),
        event.get("type"),
        event.get("symbol"),
        event.get("summary"),
        event.get("run_id"),
    )


def _first_time(event: dict) -> bool:
    sig = _signature(event)
    with _lock:
        if sig in _sigs:
            return False
        _sigs.append(sig)
        return True


def set_loop(loop):
    global _loop
    _loop = loop


def subscribe(maxsize=200):
    import asyncio
    queue = asyncio.Queue(maxsize=maxsize)
    with _lock:
        _subscribers.append(queue)
    return queue


def unsubscribe(queue):
    with _lock:
        if queue in _subscribers:
            _subscribers.remove(queue)


def _stamp():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def publish(event: dict):
    with _lock:
        bus_recent.append(event)
        subs = list(_subscribers)
    loop = _loop
    if loop is None:
        return
    for queue in subs:
        loop.call_soon_threadsafe(_offer, queue, event)


def _offer(queue, event):
    if queue.full():
        try:
            queue.get_nowait()
        except Exception:
            return
    try:
        queue.put_nowait(event)
    except Exception:
        return


def ingest_line(line: str):
    global corrupt_count
    raw = line.strip()
    if not raw:
        return None
    try:
        event = json.loads(raw)
    except json.JSONDecodeError:
        with _lock:
            corrupt_count += 1
        return None
    if not isinstance(event, dict) or "agent" not in event or "type" not in event:
        with _lock:
            corrupt_count += 1
        return None
    if _first_time(event):
        publish(event)
    return event


def append_event(event: dict):
    ensure_dirs()
    line = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
    with EVENTS.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    if _first_time(event):
        publish(event)
    return event


def append_audit(kind: str, summary: str, extra=None):
    ensure_dirs()
    row = {"ts": _stamp(), "kind": kind, "summary": summary}
    if extra:
        row.update(extra)
    with AUDIT.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    if kind == "config_change":
        append_event({
            "ts": row["ts"],
            "agent": "SYSTEM",
            "type": "config_change",
            "symbol": "",
            "level": "info",
            "summary": summary[:500],
            "data": {k: v for k, v in row.items() if k not in {"ts"}},
            "run_id": "",
        })
    return row


def read_audit(limit=200):
    if not AUDIT.exists():
        return []
    rows = []
    for line in AUDIT.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows[-limit:]


def query_events(agent="", symbol="", level="", text="", limit=100, since="", until=""):
    with _lock:
        rows = list(bus_recent)
    out = []
    needle = (text or "").lower()
    for event in reversed(rows):
        if agent and event.get("agent") != agent:
            continue
        if symbol and event.get("symbol") != symbol:
            continue
        if level and event.get("level") != level:
            continue
        ts = event.get("ts") or ""
        if since and ts < since:
            continue
        if until and ts > until:
            continue
        if needle:
            blob = json.dumps(event, ensure_ascii=False).lower()
            if needle not in blob:
                continue
        out.append(event)
        if len(out) >= limit:
            break
    return out


def corrupt_total():
    with _lock:
        return corrupt_count


def _rotate_once(retention_days: int):
    if not EVENTS.exists():
        return
    stamp = datetime.now().strftime("%Y%m%d")
    marker = LOGS / ".events_day"
    current = marker.read_text(encoding="utf-8").strip() if marker.exists() else stamp
    if current == stamp:
        return
    if EVENTS.stat().st_size > 0:
        dest = ARCHIVE / f"events_{current}.jsonl"
        try:
            if dest.exists():
                dest.write_text(dest.read_text(encoding="utf-8") + EVENTS.read_text(encoding="utf-8"), encoding="utf-8")
                EVENTS.write_text("", encoding="utf-8")
            else:
                EVENTS.replace(dest)
                EVENTS.write_text("", encoding="utf-8")
        except OSError:
            return
    marker.write_text(stamp, encoding="utf-8")
    cutoff = datetime.now() - timedelta(days=max(1, retention_days))
    for old in ARCHIVE.glob("events_*.jsonl"):
        try:
            day = datetime.strptime(old.stem.replace("events_", ""), "%Y%m%d")
        except ValueError:
            continue
        if day < cutoff:
            try:
                old.unlink()
            except OSError:
                pass


def tail_loop():
    ensure_dirs()
    position = 0
    while not _stop.is_set():
        try:
            if not EVENTS.exists():
                time.sleep(0.4)
                continue
            size = EVENTS.stat().st_size
            if size < position:
                position = 0
            with EVENTS.open("r", encoding="utf-8") as handle:
                handle.seek(position)
                while not _stop.is_set():
                    line = handle.readline()
                    if not line:
                        break
                    position = handle.tell()
                    ingest_line(line)
        except OSError:
            time.sleep(0.5)
        _stop.wait(0.35)


def rotator_loop():
    while not _stop.is_set():
        try:
            from dashboard_api.services import state
            days = int(state.read_settings().get("log_retention_days", 14))
        except Exception:
            days = 14
        try:
            _rotate_once(days)
        except Exception:
            pass
        _stop.wait(30)


def start_background():
    _stop.clear()
    threading.Thread(target=tail_loop, name="event-tail", daemon=True).start()
    threading.Thread(target=rotator_loop, name="log-rotate", daemon=True).start()


def stop_background():
    _stop.set()
