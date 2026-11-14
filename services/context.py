"""CONTEXT: sesi, berita dari CSV, dan bias kasar. Tidak memanggil internet."""
from datetime import datetime, timezone
from pathlib import Path


def session_name(hour_utc: int):
    if 0 <= hour_utc < 7:
        return "tokyo"
    if 7 <= hour_utc < 12:
        return "london"
    if 12 <= hour_utc < 21:
        return "ny"
    return "off"


def news_blackout(calendar: Path, now: datetime, minutes: int):
    if not calendar.is_file():
        return {"blocked": False, "detail": "data/calendar.csv belum ada", "source": "sample"}
    text = calendar.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines()[1:]:
        stamp = line.split(",")[0].strip()
        try:
            when = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        except ValueError:
            continue
        delta = abs((when - now).total_seconds()) / 60
        if delta <= minutes:
            return {"blocked": True, "detail": f"Berita dalam {int(delta)} menit", "source": "real"}
    return {"blocked": False, "detail": "Tidak ada berita di jendela ini", "source": "real"}


def bias(bars):
    if len(bars) < 5:
        return "flat"
    first = bars[0]["close"]
    last = bars[-1]["close"]
    if last > first:
        return "up"
    if last < first:
        return "down"
    return "flat"


def build(bars, calendar: Path, blackout_min: int = 20):
    now = datetime.now(timezone.utc)
    return {
        "session": session_name(now.hour),
        "news": news_blackout(calendar, now, blackout_min),
        "bias": bias(bars),
        "source": "real" if bars else "sample",
    }
