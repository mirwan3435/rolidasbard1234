"""Pemeriksaan koneksi. Tidak pernah mengembalikan rahasia."""
import socket
import sqlite3
import subprocess
import time
from datetime import datetime, timezone

import psutil

from dashboard_api.paths import DATA, ROOT, ensure_dirs
from dashboard_api.services.netguard import public_url

_cache = {"ts": 0.0, "payload": None}


def _stamp():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _card(cid, label, status, detail, motif):
    return {
        "id": cid,
        "label": label,
        "status": status,
        "detail": detail[:180],
        "checked_at": _stamp(),
        "motif": motif,
        "source": "real",
    }


def _mt5():
    try:
        import MetaTrader5 as mt5
    except Exception:
        return _card("mt5", "MetaTrader 5", "disconnected", "Paket MetaTrader5 tidak bisa dimuat.", "spark")
    try:
        if not mt5.initialize():
            return _card("mt5", "MetaTrader 5", "disconnected", "Terminal tidak merespons.", "spark")
        info = mt5.terminal_info()
        account = mt5.account_info()
        mt5.shutdown()
    except Exception:
        return _card("mt5", "MetaTrader 5", "disconnected", "Gagal membaca terminal.", "spark")
    if info is None:
        return _card("mt5", "MetaTrader 5", "disconnected", "terminal_info kosong.", "spark")
    server = getattr(account, "server", "") if account else ""
    currency = getattr(account, "currency", "") if account else ""
    trade_allowed = getattr(info, "trade_allowed", None)
    return _card("mt5", "MetaTrader 5", "connected", f"{server} · {currency} · trade_allowed={trade_allowed}", "spark")


def _xai():
    from dashboard_api.services.env_io import read_values
    if not read_values().get("XAI_API_KEY"):
        return _card("xai", "xAI Grok API", "not_configured", "XAI_API_KEY belum diisi.", "sphere")
    return _card("xai", "xAI Grok API", "disconnected", "Gunakan tombol cek untuk memanggil endpoint model.", "sphere")


async def _xai_live():
    from dashboard_api.services.grok_client import test_slot
    result = await test_slot("XAI_API_KEY")
    status = "connected" if result.get("ok") else "disconnected"
    if result.get("message") == "Slot masih kosong":
        status = "not_configured"
    return _card("xai", "xAI Grok API", status, result.get("message") or "", "sphere")


def _calendar():
    from dashboard_api.services.state import read_settings
    settings = read_settings()
    if settings.get("calendar_provider") == "csv":
        path = DATA / "calendar.csv"
        if not path.is_file():
            return _card("calendar", "Kalender berita", "not_configured", "Letakkan data/calendar.csv", "clock")
        age_h = (time.time() - path.stat().st_mtime) / 3600
        if age_h > 24 * 7:
            return _card("calendar", "Kalender berita", "disconnected", "CSV lebih tua dari 7 hari.", "clock")
        return _card("calendar", "Kalender berita", "connected", "CSV tersedia.", "clock")
    return _card("calendar", "Kalender berita", "not_configured", "Mode HTTP belum diisi.", "clock")


def _db():
    ensure_dirs()
    path = DATA / "journal.db"
    try:
        con = sqlite3.connect(path)
        row = con.execute("PRAGMA quick_check").fetchone()
        con.close()
    except sqlite3.Error:
        return _card("db", "Database jurnal", "disconnected", "quick_check gagal.", "bars")
    ok = row and row[0] == "ok"
    return _card("db", "Database jurnal", "connected" if ok else "disconnected", "quick_check " + str(row[0] if row else ""), "bars")


def _telegram():
    from dashboard_api.services.env_io import read_values
    values = read_values()
    if not values.get("TELEGRAM_BOT_TOKEN") or not values.get("TELEGRAM_CHAT_ID"):
        return _card("telegram", "Notifikasi", "not_configured", "Token dan chat bersifat opsional.", "ripple")
    return _card("telegram", "Notifikasi", "disconnected", "Kedua slot terisi. Tekan cek.", "ripple")


async def _telegram_live():
    from dashboard_api.services.grok_client import test_slot
    base = _telegram()
    if base["status"] == "not_configured":
        return base
    result = await test_slot("TELEGRAM_BOT_TOKEN")
    status = "connected" if result.get("ok") else "disconnected"
    return _card("telegram", "Notifikasi", status, result.get("message") or "", "ripple")


def _machine():
    vm = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=0.05)
    detail = f"CPU {cpu:.0f}% · RAM {vm.percent:.0f}%"
    status = "connected"
    if cpu > 90 or vm.percent > 90:
        status = "disconnected"
        detail += " · melewati ambang"
    return _card("machine", "Mesin lokal", status, detail, "led")


def _git():
    try:
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
        dirty = subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL)
        subject = subprocess.check_output(["git", "log", "-1", "--pretty=%s"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return _card("git", "Repositori git", "disconnected", "git tidak tersedia.", "branch")
    count = len([line for line in dirty.splitlines() if line.strip()])
    return _card("git", "Repositori git", "connected", f"{commit} · {count} berubah · {subject[:80]}", "branch")


def _web():
    from dashboard_api.services.state import read_settings
    url = read_settings().get("net_check_url") or ""
    if not public_url(url):
        return _card("web", "Akses web riset", "not_configured", "URL cek tidak aman atau kosong.", "orbit")
    try:
        sock_host = url.split("/")[2]
        socket.create_connection((sock_host, 443), timeout=5).close()
    except OSError:
        return _card("web", "Akses web riset", "disconnected", "Tidak bisa menjangkau host.", "orbit")
    return _card("web", "Akses web riset", "connected", sock_host, "orbit")


def all_cards(force=False):
    now = time.time()
    if not force and _cache["payload"] and now - _cache["ts"] < 10:
        return _cache["payload"]
    payload = {
        "connections": [_mt5(), _xai(), _calendar(), _db(), _telegram(), _machine(), _git(), _web()],
    }
    _cache["ts"] = now
    _cache["payload"] = payload
    return payload


async def check_one(cid: str):
    mapping = {
        "mt5": _mt5,
        "calendar": _calendar,
        "db": _db,
        "machine": _machine,
        "git": _git,
        "web": _web,
    }
    if cid == "xai":
        card = await _xai_live()
    elif cid == "telegram":
        card = await _telegram_live()
    elif cid in mapping:
        card = mapping[cid]()
    else:
        raise KeyError(cid)
    payload = all_cards()
    payload["connections"] = [card if item["id"] == cid else item for item in payload["connections"]]
    _cache["payload"] = payload
    _cache["ts"] = time.time()
    return card
