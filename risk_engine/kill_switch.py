import os
from datetime import datetime, timezone

DEFAULT_PATH = os.path.join("logs", "KILL_SWITCH.lock")


class KillSwitch:
    """Saklar darurat berbasis file. Sengaja TIDAK ada fungsi reset:
    buat nyalain lagi, hapus file lock-nya secara manual."""

    def __init__(self, path=DEFAULT_PATH):
        self.path = path

    def is_active(self):
        return os.path.exists(self.path)

    def reason(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except OSError:
            return "kill-switch aktif (alasan tidak terbaca)"

    def trigger(self, reason):
        if self.is_active():
            return
        folder = os.path.dirname(self.path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            f.write(f"{datetime.now(timezone.utc).isoformat()} | {reason}")
