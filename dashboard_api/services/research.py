"""Ingest riset. URL privat ditolak. Tanpa Grok, pakai penanda kata."""
import json
from datetime import datetime, timezone

import requests

from dashboard_api.paths import DATA, ensure_dirs
from dashboard_api.services import events
from dashboard_api.services.netguard import public_url

KEYWORDS = {
    "ict": "ICT",
    "smc": "SMC",
    "order block": "SMC",
    "supply": "SND",
    "demand": "SND",
    "crt": "CRT",
    "breakout": "breakout",
    "order flow": "order flow",
    "mean reversion": "mean reversion",
    "volatil": "volatility",
    "risk": "risk",
}


def _dir():
    folder = DATA / "research"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _tag(text: str):
    lowered = text.lower()
    found = []
    for needle, label in KEYWORDS.items():
        if needle in lowered and label not in found:
            found.append(label)
    if not found:
        found = ["note"]
    source = "note"
    if "youtube.com" in lowered or "youtu.be" in lowered:
        source = "youtube"
    elif "github.com" in lowered:
        source = "github"
    elif "arxiv.org" in lowered:
        source = "arxiv"
    elif lowered.startswith("http"):
        source = "article"
    return {"concepts": found[:8], "source_type": source, "summary": text[:280], "tagger": "keyword"}


def ingest(kind: str, value: str):
    if kind not in {"url", "text"}:
        raise ValueError("Jenis harus url atau text")
    value = (value or "").strip()
    if len(value) < 4 or len(value) > 20000:
        raise ValueError("Isi terlalu pendek atau terlalu panjang")
    text = value
    if kind == "url":
        if not public_url(value):
            raise ValueError("URL ditolak")
        try:
            response = requests.get(value, timeout=5, allow_redirects=False, headers={"User-Agent": "PYTHON_AI_LAB"})
        except requests.RequestException as exc:
            raise ValueError("Gagal mengambil URL") from exc
        if response.status_code >= 400:
            raise ValueError(f"URL menjawab {response.status_code}")
        text = response.text[:20000]
    tagged = _tag(text if kind == "text" else value + "\n" + text[:500])
    row = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
        "kind": kind,
        "value": value[:500],
        "concepts": tagged["concepts"],
        "source_type": tagged["source_type"],
        "summary": tagged["summary"],
        "tagger": tagged["tagger"],
        "source": "real",
    }
    path = _dir() / "items.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    events.append_event({
        "ts": row["ts"], "agent": "PROFILER", "type": "research", "symbol": "", "level": "info",
        "summary": f"Riset: {', '.join(row['concepts'])}",
        "msg": f"Riset: {', '.join(row['concepts'])}",
        "data": {"source_type": row["source_type"], "source": "real"},
        "run_id": "",
    })
    return row


def items(limit=100):
    path = _dir() / "items.jsonl"
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows[-limit:]


def clusters():
    grouped = {}
    counts = {}
    for row in items(400):
        counts[row.get("source_type") or "note"] = counts.get(row.get("source_type") or "note", 0) + 1
        for concept in row.get("concepts") or []:
            grouped.setdefault(concept, []).append({"ts": row.get("ts"), "summary": row.get("summary"), "source_type": row.get("source_type")})
    return {"clusters": grouped, "counts": counts, "source": "real" if grouped else "sample"}
