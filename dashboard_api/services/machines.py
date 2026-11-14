"""Stat mesin lokal. Tidak mengirim order."""
import platform
import shutil
import socket
import subprocess
import time

import psutil

from dashboard_api.paths import ROOT


def _listening(port: int):
    sock = socket.socket()
    sock.settimeout(0.3)
    try:
        sock.connect(("127.0.0.1", port))
        return "open"
    except OSError:
        return "closed"
    finally:
        sock.close()


def _node_version():
    try:
        return subprocess.check_output(["node", "-v"], text=True, timeout=2, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None


def _terminal_running():
    try:
        for proc in psutil.process_iter(["name"]):
            name = (proc.info.get("name") or "").lower()
            if name == "terminal64.exe":
                return True
    except (psutil.Error, OSError):
        return False
    return False


_xai_cache = {"ts": 0.0, "value": {"status": "not_configured", "latency_ms": None}}


def _xai_latency():
    from dashboard_api.services.env_io import read_values
    if not read_values().get("XAI_API_KEY"):
        return {"status": "not_configured", "latency_ms": None}
    now = time.time()
    if now - _xai_cache["ts"] < 30:
        return _xai_cache["value"]
    started = time.perf_counter()
    try:
        socket.create_connection(("api.x.ai", 443), timeout=3).close()
        value = {"status": "reachable", "latency_ms": round((time.perf_counter() - started) * 1000)}
    except OSError:
        value = {"status": "disconnected", "latency_ms": None}
    _xai_cache["ts"] = now
    _xai_cache["value"] = value
    return value


def snapshot():
    disk = shutil.disk_usage(ROOT)
    vm = psutil.virtual_memory()
    sample = {
        "cpu_pct": psutil.cpu_percent(interval=0.1),
        "ram_pct": vm.percent,
        "ram_used_mb": round(vm.used / 1048576),
        "disk_free_gb": round(disk.free / 1073741824, 2),
        "disk_pct": round(disk.used / disk.total * 100, 1) if disk.total else 0,
        "uptime_sec": int(time.time() - psutil.boot_time()),
        "python": platform.python_version(),
        "node": _node_version(),
        "port_8765": _listening(8765),
        "port_5173": _listening(5173),
        "terminal64": _terminal_running(),
        "xai": _xai_latency(),
        "source": "real",
    }
    remember(sample)
    sample["history"] = _history()
    return sample


_ring = []


def _history():
    global _ring
    return list(_ring)


def remember(sample):
    global _ring
    _ring = (_ring + [{"t": time.time(), "cpu": sample["cpu_pct"], "ram": sample["ram_pct"]}])[-150]
