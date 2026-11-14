"""Stat mesin lokal. Tidak mengirim order."""
import platform
import shutil
import time

import psutil

from dashboard_api.paths import ROOT


def snapshot():
    disk = shutil.disk_usage(ROOT)
    vm = psutil.virtual_memory()
    return {
        "cpu_pct": psutil.cpu_percent(interval=0.1),
        "ram_pct": vm.percent,
        "ram_used_mb": round(vm.used / 1048576),
        "disk_free_gb": round(disk.free / 1073741824, 2),
        "disk_pct": round(disk.used / disk.total * 100, 1) if disk.total else 0,
        "uptime_sec": int(time.time() - psutil.boot_time()),
        "python": platform.python_version(),
        "source": "real",
    }
