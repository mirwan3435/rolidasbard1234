"""Skema event dan snapshot. Backend tetap toleran: baris rusak dilewati."""
from typing import Any

from pydantic import BaseModel, Field

AGENTS = ("DATA", "SCOPE", "WHALES", "DEBATE", "RISK", "EXEC", "CORE", "SYSTEM")
EVENT_TYPES = ("status", "input", "output", "decision", "error", "heartbeat", "config_change")
LEVELS = ("debug", "info", "warn", "error")
NODE_STATUS = ("idle", "running", "ok", "warn", "error", "disabled")


class EventIn(BaseModel):
    ts: str = ""
    agent: str
    type: str
    symbol: str = ""
    level: str = "info"
    summary: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
    run_id: str = ""


class KillSwitchView(BaseModel):
    active: bool
    reason: str = ""
    since: str = ""
    reset_hint: str = r"Reset manual: hapus file logs\KILL_SWITCH.lock. Dashboard tidak bisa mereset."
