"""Definisi 13 agen. File JSON yang sudah ada tidak ditimpa, hanya dilengkapi."""
import json
from datetime import datetime, timezone

from dashboard_api.paths import DATA, ensure_dirs

SPECS = {
    "SCOPE": {"label": "Scope", "tier": "A", "llm": False, "color": "#22d3ee", "summary": "Detektor strategi. Skor zona 0-100, bukan probabilitas profit.", "params": {"min_score": 80}},
    "WHALES": {"label": "Whales", "tier": "A", "llm": True, "color": "#a78bfa", "summary": "Konteks aliran besar. Bukan keputusan masuk.", "params": {}},
    "DEBATE": {"label": "Debate", "tier": "A", "llm": True, "color": "#fbbf24", "summary": "Mencari alasan sinyal bisa gagal.", "params": {}},
    "RISK": {"label": "Risk", "tier": "A", "llm": False, "color": "#ff6b4a", "summary": "Hak veto mutlak. Deterministik, tanpa prompt.", "params": {}},
    "EXEC": {"label": "Exec", "tier": "A", "llm": False, "color": "#59f08b", "summary": "Kirim order paper/demo. Tanpa LLM.", "params": {}},
    "CORE": {"label": "Grok Core", "tier": "A", "llm": True, "color": "#f5ecd0", "summary": "Hanya boleh menurunkan skor atau menolak.", "params": {}},
    "DATA": {"label": "Data", "tier": "B", "llm": False, "color": "#7dd3fc", "summary": "Kualitas candle, spread, dan jam server.", "params": {"max_tick_age_sec": 15}},
    "CONTEXT": {"label": "Context", "tier": "B", "llm": False, "color": "#34d399", "summary": "Sesi, berita, dan bias timeframe besar.", "params": {"news_blackout_min": 20}},
    "PROFILER": {"label": "Profiler", "tier": "B", "llm": False, "color": "#f472b6", "summary": "Edge pair × strategi setelah biaya.", "params": {"min_trades_valid": 100}},
    "POSMGR": {"label": "PosMgr", "tier": "B", "llm": False, "color": "#fb923c", "summary": "Trailing di EA. Dashboard hanya memantau.", "params": {"trail_atr_mult": 1.0}},
    "PORTFOLIO": {"label": "Portfolio", "tier": "B", "llm": False, "color": "#818cf8", "summary": "Korelasi dan panas portofolio.", "params": {"max_heat_pct": 5}},
    "JOURNAL": {"label": "Journal", "tier": "B", "llm": False, "color": "#94a3b8", "summary": "Catatan keputusan lengkap.", "params": {}},
    "WATCHDOG": {"label": "Watchdog", "tier": "B", "llm": False, "color": "#e879f9", "summary": "Heartbeat, data basi, koneksi putus.", "params": {"stale_sec": 30}},
}

READONLY = {"RISK", "EXEC"}
ORDER = list(SPECS)


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def path_for(name: str):
    if name not in SPECS:
        raise KeyError(name)
    return DATA / "agents" / f"{name}.json"


def ensure_files():
    """Tambah field yang hilang. Prompt yang sudah tersimpan tidak diganti."""
    ensure_dirs()
    backup_dir = DATA / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    for name, spec in SPECS.items():
        path = path_for(name)
        if not path.exists():
            doc = {
                "id": name,
                "name": name,
                "label": spec["label"],
                "tier": spec["tier"],
                "llm": spec["llm"],
                "color": spec["color"],
                "enabled": True,
                "model": "",
                "temperature": 0.2,
                "max_tokens": 600,
                "timeout_sec": 30,
                "system_prompt": "",
                "output_schema": {},
                "skill": {
                    "summary": spec["summary"],
                    "prompt": "",
                    "params": dict(spec["params"]),
                    "output_schema_ref": "verdict" if spec["llm"] else "",
                },
                "limits": {},
                "version": 1,
                "updated_at": _now(),
                "versions": [],
            }
            _write(path, doc)
            continue
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(doc, dict):
            continue
        original = json.dumps(doc, sort_keys=True)
        doc.setdefault("id", name)
        doc.setdefault("name", name)
        doc.setdefault("label", spec["label"])
        doc.setdefault("tier", spec["tier"])
        doc.setdefault("llm", spec["llm"])
        doc.setdefault("color", spec["color"])
        skill = doc.get("skill") if isinstance(doc.get("skill"), dict) else {}
        skill.setdefault("summary", spec["summary"])
        skill.setdefault("prompt", str(doc.get("system_prompt") or ""))
        skill.setdefault("params", dict(spec["params"]))
        skill.setdefault("output_schema_ref", "verdict" if spec["llm"] else "")
        doc["skill"] = skill
        doc.setdefault("limits", {})
        doc.setdefault("version", max([int(v.get("n") or 0) for v in doc.get("versions") or []] or [1]))
        doc.setdefault("updated_at", _now())
        if json.dumps(doc, sort_keys=True) == original:
            continue
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        (backup_dir / f"agent_{name}_{stamp}.json.bak").write_text(original, encoding="utf-8")
        _write(path, doc)


def _write(path, doc):
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)
