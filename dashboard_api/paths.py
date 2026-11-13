import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("DASHBOARD_DATA_DIR", ROOT / "data"))
LOGS = Path(os.environ.get("DASHBOARD_LOG_DIR", ROOT / "logs"))
ENV_FILE = Path(os.environ.get("DASHBOARD_ENV_FILE", ROOT / ".env"))
GITIGNORE = ROOT / ".gitignore"
EVENTS = LOGS / "events.jsonl"
AUDIT = LOGS / "audit.jsonl"
ARCHIVE = LOGS / "archive"


def ensure_dirs():
    for folder in (DATA, DATA / "agents", DATA / "backups", LOGS, ARCHIVE):
        folder.mkdir(parents=True, exist_ok=True)
    if not EVENTS.exists():
        EVENTS.write_text("", encoding="utf-8")
    if not AUDIT.exists():
        AUDIT.write_text("", encoding="utf-8")
