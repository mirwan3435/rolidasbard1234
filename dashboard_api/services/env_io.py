"""Baca/tulis .env secara atomik. Nilai key tidak pernah dikembalikan utuh."""
import re

from dashboard_api.paths import ENV_FILE, GITIGNORE, ensure_dirs

SLOTS = ("XAI_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID")
_SLOT_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,40}$")
REQUIRED_GITIGNORE = (".env", "logs/", "data/backups/")


def _parse(text: str):
    rows = []
    values = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            rows.append(("raw", line, None))
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        rows.append(("kv", key, value))
        values[key] = value.strip().strip('"').strip("'")
    return rows, values


def read_values():
    if not ENV_FILE.exists():
        return {}
    _, values = _parse(ENV_FILE.read_text(encoding="utf-8"))
    return values


def last4(value: str):
    if not value:
        return ""
    return value[-4:]


def public_slots():
    values = read_values()
    out = []
    for slot in SLOTS:
        value = values.get(slot, "")
        out.append({
            "slot": slot,
            "filled": bool(value),
            "last4": last4(value) if value else "",
            "required": slot == "XAI_API_KEY",
        })
    return out


def write_slot(slot: str, value: str):
    if slot not in SLOTS or not _SLOT_RE.match(slot):
        raise KeyError(slot)
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Nilai kosong")
    if any(ch in value for ch in ("\n", "\r", "\x00")):
        raise ValueError("Nilai mengandung karakter terlarang")
    ensure_dirs()
    ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
    text = ENV_FILE.read_text(encoding="utf-8") if ENV_FILE.exists() else ""
    rows, _ = _parse(text)
    found = False
    new_lines = []
    for kind, key, old in rows:
        if kind == "kv" and key == slot:
            new_lines.append(f"{slot}={value}")
            found = True
        elif kind == "kv":
            new_lines.append(f"{key}={old}")
        else:
            new_lines.append(key)
    if not found:
        if new_lines and new_lines[-1] != "":
            new_lines.append(f"{slot}={value}")
        else:
            new_lines.append(f"{slot}={value}")
    body = "\n".join(new_lines)
    if not body.endswith("\n"):
        body += "\n"
    tmp = ENV_FILE.with_suffix(ENV_FILE.suffix + ".tmp")
    tmp.write_text(body, encoding="utf-8")
    tmp.replace(ENV_FILE)
    from dashboard_api.services import events
    events.append_audit("api_key", f"Slot {slot} diperbarui", {"slot": slot})


def gitignore_missing():
    if not GITIGNORE.exists():
        return list(REQUIRED_GITIGNORE)
    text = GITIGNORE.read_text(encoding="utf-8")
    missing = []
    for item in REQUIRED_GITIGNORE:
        if item not in text:
            missing.append(item)
    return missing


def ensure_gitignore_lines():
    missing = gitignore_missing()
    if not missing:
        return []
    existing = GITIGNORE.read_text(encoding="utf-8") if GITIGNORE.exists() else ""
    addition = "\n# Ditambahkan dashboard\n" + "\n".join(missing) + "\n"
    GITIGNORE.write_text(existing.rstrip() + "\n" + addition, encoding="utf-8")
    return missing
