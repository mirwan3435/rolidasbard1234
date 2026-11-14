"""WATCHDOG: data basi dan niat tanpa SL. Tidak menutup posisi."""
from datetime import datetime, timezone


def check(tick_age_sec, has_sl: bool, connected: bool, stale_sec: int = 30):
    issues = []
    if tick_age_sec is None or tick_age_sec > stale_sec:
        issues.append("data basi")
    if not has_sl:
        issues.append("niat tanpa SL")
    if not connected:
        issues.append("koneksi data terputus")
    return {
        "ok": not issues,
        "issues": issues,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "source": "real",
    }
