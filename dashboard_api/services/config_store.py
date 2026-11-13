"""Baca/tulis data/config.json dengan batas keras, diff, dan backup."""
import json
from datetime import datetime

from dashboard_api import hard_limits as limits
from dashboard_api.paths import DATA, ensure_dirs
from dashboard_api.services import events

FIELDS = [
    "risk_per_trade_pct",
    "stop_pct_of_price",
    "max_open_positions",
    "max_total_risk_pct",
    "max_margin_pct",
    "daily_loss_limit_pct",
    "max_drawdown_pct",
    "max_spread_to_stop_ratio",
    "commission_per_lot_usd",
]


def config_path():
    return DATA / "config.json"


def read_config():
    ensure_dirs()
    path = config_path()
    if not path.exists():
        write_raw(limits.DEFAULTS)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raw = json.loads(json.dumps(limits.DEFAULTS))
    return _normalize(raw)


def write_raw(data):
    ensure_dirs()
    path = config_path()
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def _normalize(raw):
    base = json.loads(json.dumps(limits.DEFAULTS))
    if not isinstance(raw, dict):
        return base
    if isinstance(raw.get("virtual_capital"), (int, float)) and not isinstance(raw.get("virtual_capital"), bool):
        base["virtual_capital"] = float(raw["virtual_capital"])
    if raw.get("active_profile") in limits.PROFILE_NAMES:
        base["active_profile"] = raw["active_profile"]
    base["commission_confirmed"] = bool(raw.get("commission_confirmed"))
    incoming = raw.get("profiles") if isinstance(raw.get("profiles"), dict) else {}
    for name in limits.PROFILE_NAMES:
        patch = incoming.get(name) if isinstance(incoming.get(name), dict) else {}
        for field in FIELDS:
            if field not in patch:
                continue
            value = patch[field]
            if field == "stop_pct_of_price" and value is None:
                base["profiles"][name][field] = None
            elif isinstance(value, (int, float)) and not isinstance(value, bool):
                if field in limits.INT_FIELDS:
                    base["profiles"][name][field] = int(value)
                else:
                    base["profiles"][name][field] = float(value)
    return base


def diff_config(old, new):
    changes = []
    if old.get("virtual_capital") != new.get("virtual_capital"):
        changes.append({"path": "virtual_capital", "before": old.get("virtual_capital"), "after": new.get("virtual_capital")})
    if old.get("active_profile") != new.get("active_profile"):
        changes.append({"path": "active_profile", "before": old.get("active_profile"), "after": new.get("active_profile")})
    if old.get("commission_confirmed") != new.get("commission_confirmed"):
        changes.append({"path": "commission_confirmed", "before": old.get("commission_confirmed"), "after": new.get("commission_confirmed")})
    for name in limits.PROFILE_NAMES:
        for field in FIELDS:
            before = old["profiles"][name].get(field)
            after = new["profiles"][name].get(field)
            if before != after:
                changes.append({"path": f"profiles.{name}.{field}", "before": before, "after": after})
    return changes


def _check_number(profile, field, value):
    if field == "stop_pct_of_price":
        if profile == "standard":
            if value is not None:
                return "Profil standard tidak memakai stop_pct_of_price (harus kosong)"
            return None
        if value is None:
            return "Profil eksperimen wajib punya stop_pct_of_price"
        if value < limits.FLOOR["stop_pct_of_price"] or value > limits.CEILING["experiment_a"]["stop_pct_of_price"]:
            return f"stop_pct_of_price di luar batas {limits.FLOOR['stop_pct_of_price']}–{limits.CEILING['experiment_a']['stop_pct_of_price']}"
        return None
    floor = limits.FLOOR[field]
    ceiling = limits.CEILING[profile][field]
    if value < floor or value > ceiling:
        return f"{profile}.{field} di luar batas {floor}–{ceiling}"
    return None


def validate(config):
    errors = []
    capital = config["virtual_capital"]
    if capital < limits.VIRTUAL_CAPITAL_MIN or capital > limits.VIRTUAL_CAPITAL_MAX:
        errors.append(f"virtual_capital di luar batas {limits.VIRTUAL_CAPITAL_MIN}–{limits.VIRTUAL_CAPITAL_MAX}")
    if config["active_profile"] not in limits.PROFILE_NAMES:
        errors.append("active_profile tidak dikenal")
    for name in limits.PROFILE_NAMES:
        profile = config["profiles"][name]
        for field in FIELDS:
            message = _check_number(name, field, profile.get(field))
            if message:
                errors.append(message)
    return errors


def save_config(new_config, confirm: bool):
    current = read_config()
    proposed = _normalize(new_config)
    errors = validate(proposed)
    changes = diff_config(current, proposed)
    if errors:
        return {"saved": False, "errors": errors, "diff": changes}
    if not confirm:
        return {"saved": False, "needs_confirm": True, "diff": changes, "errors": []}
    if not changes:
        return {"saved": False, "needs_confirm": False, "diff": [], "errors": [], "message": "Tidak ada perubahan"}
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = DATA / "backups" / f"config_{stamp}.json.bak"
    backup.write_text(json.dumps(current, indent=2, ensure_ascii=False), encoding="utf-8")
    write_raw(proposed)
    summary = "Config diubah: " + ", ".join(item["path"] for item in changes[:12])
    events.append_audit("config_change", summary, {"diff": changes, "backup": backup.name})
    return {
        "saved": True,
        "diff": changes,
        "backup": backup.name,
        "reload_note": "Perubahan berlaku setelah sistem trading di-reload (sesi yang sedang berjalan tidak diubah diam-diam).",
    }


def public_view():
    config = read_config()
    return {
        "config": config,
        "limits": {"ceiling": limits.CEILING, "floor": limits.FLOOR, "virtual_capital": [limits.VIRTUAL_CAPITAL_MIN, limits.VIRTUAL_CAPITAL_MAX]},
        "reload_note": "Nilai dibaca config.py dari data/config.json saat proses trading berikutnya dimulai.",
        "experiment_label": "EKSPERIMEN, tidak aman di modal kecil",
    }
