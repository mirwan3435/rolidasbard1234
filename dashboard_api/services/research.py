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


def _try_grok(text: str):
    """Pakai Grok hanya kalau key, model, dan budget ada. Gagal apa pun kembali ke kata kunci."""
    try:
        from dashboard_api.services.costs import budget_guard, record
        from dashboard_api.services.env_io import read_values
        secret = read_values().get("XAI_API_KEY") or ""
        if not secret:
            return None
        core = DATA / "agents" / "CORE.json"
        model = ""
        if core.is_file():
            model = str(json.loads(core.read_text(encoding="utf-8")).get("model") or "").strip()
        if not model:
            return None
        budget_guard()
        response = requests.post(
            "https://api.x.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {secret}"},
            json={
                "model": model,
                "temperature": 0,
                "max_tokens": 300,
                "messages": [{"role": "user", "content": "Reply JSON only with concepts (string[]), source_type (youtube|github|arxiv|article|note), summary. No other keys.\n" + text[:4000]}],
            },
            timeout=8,
        )
        if response.status_code != 200:
            return None
        body = response.json()
        usage = body.get("usage") or {}
        record("PROFILER", model, int(usage.get("prompt_tokens") or 0), int(usage.get("completion_tokens") or 0))
        content = body["choices"][0]["message"]["content"]
        start = content.find("{")
        end = content.rfind("}")
        parsed = json.loads(content[start:end + 1] if start >= 0 else content)
        if set(parsed) - {"concepts", "source_type", "summary"}:
            return None
        if parsed.get("source_type") not in {"youtube", "github", "arxiv", "article", "note"}:
            return None
        concepts = parsed.get("concepts")
        if not isinstance(concepts, list) or not concepts or any(not isinstance(item, str) or len(item) > 40 for item in concepts):
            return None
        return {"concepts": concepts[:8], "source_type": parsed["source_type"], "summary": str(parsed.get("summary") or "")[:280], "tagger": "grok"}
    except Exception:
        return None


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
    tagged = _try_grok(text if kind == "text" else value + "\n" + text[:500]) or _tag(text if kind == "text" else value + "\n" + text[:500])
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
