"""Skill agent. Nama file hanya dari whitelist, bukan dari path mentah."""
import json
from datetime import datetime, timezone

from dashboard_api.paths import DATA, ensure_dirs
from dashboard_api.services import events

EDITABLE = {"DEBATE", "CORE", "WHALES"}
LOCKED = {
    "RISK": "RISK deterministik dan fail-closed. Prompt AI tidak boleh mengubah keputusannya.",
    "SCOPE": "SCOPE hitungan murni (order block, FVG, likuiditas, BOS/CHOCH, skor 0-100). Bukan probabilitas profit dan bukan prompt AI.",
    "EXEC": "EXEC tidak memakai LLM dan tidak punya prompt. Dashboard tidak mengirim order.",
}
VARIABLES = ["{symbol}", "{zones}", "{dxy_context}", "{whales}", "{debate}", "{risk_profile}", "{capital}"]

PRESETS = {
    "DEBATE": {
        "Konservatif": "Kamu sudut pandang pengawas. Nilai usulan setup sebagai data, sebut kelemahan, dan jangan menyuruh mengirim order. Keluaran JSON sesuai skema.",
        "Singkat": "Ringkas argumen pro dan kontra setup ini dalam JSON. Jangan menyebut ukuran lot final. RISK yang memutuskan.",
    },
    "CORE": {
        "Konservatif": "Gabungkan keluaran SCOPE, WHALES, dan DEBATE menjadi usulan. Jangan mengubah batas risiko. Tandai keyakinan sebagai skor diskusi, bukan probabilitas profit.",
        "Singkat": "Buat ringkasan usulan JSON. Jika data bertentangan, status=tahan.",
    },
    "WHALES": {
        "Konservatif": "Jelaskan jejak volume hanya sebagai konteks. Jangan mengeluarkan keputusan masuk.",
        "Singkat": "Satu paragraf konteks aliran besar, plus JSON ringkas.",
    },
}


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _path(name: str):
    if name not in EDITABLE and name not in LOCKED:
        raise KeyError(name)
    return DATA / "agents" / f"{name}.json"


def _default(name: str):
    return {
        "name": name,
        "enabled": True,
        "model": "",
        "temperature": 0.3,
        "max_tokens": 800,
        "timeout_sec": 30,
        "system_prompt": PRESETS[name]["Konservatif"],
        "output_schema": {
            "type": "object",
            "required": ["stance", "summary"],
            "properties": {
                "stance": {"type": "string"},
                "summary": {"type": "string"},
                "score": {"type": "number"},
            },
        },
        "versions": [],
    }


def _snapshot(doc):
    return {
        "enabled": doc["enabled"],
        "model": doc["model"],
        "temperature": doc["temperature"],
        "max_tokens": doc["max_tokens"],
        "timeout_sec": doc["timeout_sec"],
        "system_prompt": doc["system_prompt"],
        "output_schema": doc["output_schema"],
    }


def read_agent(name: str):
    from dashboard_api.services.agent_registry import SPECS
    if name in LOCKED:
        spec = SPECS[name]
        params = dict(spec["params"])
        path = DATA / "agents" / f"{name}.json"
        if path.exists():
            try:
                stored = json.loads(path.read_text(encoding="utf-8"))
                extra = (stored.get("skill") or {}).get("params")
                if isinstance(extra, dict):
                    params.update(extra)
            except (OSError, json.JSONDecodeError):
                pass
        return {
            "name": name,
            "locked": True,
            "reason": LOCKED[name],
            "editable": False,
            "label": spec["label"],
            "tier": spec["tier"],
            "llm": False,
            "color": spec["color"],
            "params": params,
            "params_editable": name == "SCOPE",
            "skill": {"summary": spec["summary"], "prompt": "", "params": params},
        }
    if name in SPECS and name not in EDITABLE:
        return _read_param_agent(name)
    if name not in EDITABLE:
        raise KeyError(name)
    ensure_dirs()
    path = _path(name)
    if not path.exists():
        doc = _default(name)
        doc["versions"].append({"n": 1, "ts": _now(), "note": "bawaan", "snapshot": _snapshot(doc)})
        _write(name, doc)
        return _public(doc)
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        doc = _default(name)
    if not doc.get("versions"):
        doc["versions"] = [{"n": 1, "ts": _now(), "note": "awal", "snapshot": _snapshot(doc)}]
        _write(name, doc)
    return _public(doc)


def _public(doc):
    from dashboard_api.services.agent_registry import SPECS
    spec = SPECS.get(doc["name"], {})
    versions = []
    for item in doc.get("versions", []):
        versions.append({"n": item.get("n"), "ts": item.get("ts"), "note": item.get("note", "")})
    return {
        "name": doc["name"],
        "locked": False,
        "editable": True,
        "enabled": bool(doc.get("enabled", True)),
        "model": str(doc.get("model") or ""),
        "temperature": doc.get("temperature", 0.3),
        "max_tokens": doc.get("max_tokens", 800),
        "timeout_sec": doc.get("timeout_sec", 30),
        "system_prompt": str(doc.get("system_prompt") or ""),
        "output_schema": doc.get("output_schema") if isinstance(doc.get("output_schema"), dict) else {},
        "versions": versions,
        "variables": VARIABLES,
        "presets": list(PRESETS.get(doc["name"], {})),
        "model_note": "Isi nama model yang berlaku di dokumentasi xAI. Dashboard tidak menebak nama model.",
        "llm": True,
        "label": spec.get("label", doc["name"]),
        "color": spec.get("color", "#f5ecd0"),
        "tier": spec.get("tier", "A"),
    }


def _write(name, doc):
    path = _path(name)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def _load_full(name):
    path = _path(name)
    if not path.exists():
        read_agent(name)
    return json.loads(_path(name).read_text(encoding="utf-8"))


def save_agent(name: str, payload: dict, note: str = ""):
    if name in LOCKED:
        raise PermissionError(LOCKED[name])
    if name not in EDITABLE:
        raise KeyError(name)
    doc = _load_full(name)
    doc["enabled"] = bool(payload["enabled"])
    doc["model"] = str(payload["model"]).strip()
    doc["temperature"] = float(payload["temperature"])
    doc["max_tokens"] = int(payload["max_tokens"])
    doc["timeout_sec"] = int(payload["timeout_sec"])
    doc["system_prompt"] = str(payload["system_prompt"])
    schema = payload["output_schema"]
    if not isinstance(schema, dict):
        raise ValueError("Skema keluaran harus objek JSON")
    json.dumps(schema)
    doc["output_schema"] = schema
    versions = doc.get("versions") or []
    number = 1 + max([int(v.get("n") or 0) for v in versions] or [0])
    versions.append({"n": number, "ts": _now(), "note": note[:200], "snapshot": _snapshot(doc)})
    doc["versions"] = versions[-30:]
    _write(name, doc)
    events.append_audit("skill_change", f"Skill {name} disimpan versi {number}", {"agent": name, "version": number})
    return _public(doc)


def version_detail(name: str, number: int):
    if name not in EDITABLE:
        raise KeyError(name)
    doc = _load_full(name)
    for item in doc.get("versions", []):
        if int(item.get("n") or 0) == number:
            return item
    raise KeyError(number)


def rollback(name: str, number: int):
    if name in LOCKED:
        raise PermissionError(LOCKED[name])
    item = version_detail(name, number)
    snap = item.get("snapshot") or {}
    return save_agent(name, snap, note=f"rollback ke v{number}")


def preset_text(name: str, preset: str):
    if name not in PRESETS or preset not in PRESETS[name]:
        raise KeyError(preset)
    return PRESETS[name][preset]


def _read_param_agent(name: str):
    from dashboard_api.services.agent_registry import SPECS, path_for
    spec = SPECS[name]
    path = path_for(name)
    params = dict(spec["params"])
    if path.exists():
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
            stored = (doc.get("skill") or {}).get("params")
            if isinstance(stored, dict):
                params.update(stored)
        except (OSError, json.JSONDecodeError):
            pass
    return {
        "name": name,
        "locked": False,
        "editable": True,
        "prompt_locked": True,
        "label": spec["label"],
        "tier": spec["tier"],
        "llm": False,
        "color": spec["color"],
        "enabled": True,
        "model": "",
        "temperature": 0,
        "max_tokens": 0,
        "timeout_sec": 30,
        "system_prompt": "",
        "output_schema": {},
        "params": params,
        "params_editable": True,
        "skill": {"summary": spec["summary"], "prompt": "", "params": params},
        "versions": [],
        "variables": [],
        "presets": [],
        "model_note": "Agen ini bukan LLM. Hanya parameter angka yang boleh diubah.",
    }


def save_params(name: str, params: dict, note: str = ""):
    """Hanya angka dalam batas. RISK dan EXEC tetap read-only. Prompt tidak disentuh."""
    from dashboard_api.services.agent_registry import INT_PARAMS, PARAM_BOUNDS, READONLY, SPECS, path_for

    if name in READONLY:
        raise PermissionError(LOCKED.get(name, "Agen ini read-only."))
    if name not in SPECS or SPECS[name]["llm"]:
        raise KeyError(name)
    allowed = set(SPECS[name]["params"])
    if not isinstance(params, dict) or set(params) - allowed:
        raise ValueError("Parameter di luar daftar agen ini")
    clean = {}
    for key, raw in params.items():
        lo, hi = PARAM_BOUNDS[key]
        try:
            number = float(raw)
        except (TypeError, ValueError):
            raise ValueError(f"{key} harus angka")
        if number < lo or number > hi:
            raise ValueError(f"{key} di luar batas {lo}..{hi}")
        clean[key] = int(number) if key in INT_PARAMS else round(number, 4)
    path = path_for(name)
    if not path.exists():
        from dashboard_api.services.agent_registry import ensure_files
        ensure_files()
    doc = json.loads(path.read_text(encoding="utf-8"))
    backup_dir = DATA / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = _now().replace(":", "").replace(".", "")
    (backup_dir / f"{name}-{stamp}.json").write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    skill = doc.get("skill") if isinstance(doc.get("skill"), dict) else {}
    stored = skill.get("params") if isinstance(skill.get("params"), dict) else {}
    stored.update(clean)
    skill["params"] = stored
    skill.setdefault("summary", SPECS[name]["summary"])
    skill["prompt"] = ""
    doc["skill"] = skill
    doc["version"] = int(doc.get("version") or 1) + 1
    doc["updated_at"] = _now()
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
    events.append_audit("skill_change", f"Parameter {name} disimpan", {"agent": name, "version": doc["version"], "note": note[:80]})
    fresh = _read_param_agent(name) if name != "SCOPE" else read_agent(name)
    fresh["params"] = stored
    return fresh


def list_agents():
    from dashboard_api.services.agent_registry import SPECS
    rows = []
    for name in SPECS:
        if name in LOCKED:
            rows.append({"name": name, "locked": True, "reason": LOCKED[name], "tier": SPECS[name]["tier"], "llm": False, "color": SPECS[name]["color"], "label": SPECS[name]["label"], "summary": SPECS[name]["summary"], "params_editable": name == "SCOPE"})
        elif name in EDITABLE:
            doc = read_agent(name)
            rows.append({"name": name, "locked": False, "enabled": doc["enabled"], "model": doc["model"], "tier": "A", "llm": True, "color": SPECS[name]["color"], "label": SPECS[name]["label"], "summary": SPECS[name]["summary"], "params_editable": False})
        else:
            doc = _read_param_agent(name)
            rows.append({"name": name, "locked": False, "enabled": True, "model": "", "tier": doc["tier"], "llm": False, "color": doc["color"], "label": doc["label"], "summary": SPECS[name]["summary"], "params_editable": True})
    return rows
