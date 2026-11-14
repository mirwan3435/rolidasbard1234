"""Baca snapshot, simbol, akun virtual, dan pengaturan. Tidak mengirim order."""
import json
from datetime import datetime, timezone, timedelta

from dashboard_api.paths import DATA, ensure_dirs
from dashboard_api.services import events

# TODO: sambungkan ke MT5 read-only (data.market_data) saat mode live.
# Spesifikasi di bawah hanya mock agar UI bisa jalan tanpa terminal.
SYMBOL_SPECS = {
    "XAUUSDm": {"role": "entry", "tick_size": 0.001, "tick_value": 0.1, "volume_min": 0.01, "volume_step": 0.01, "volume_max": 50, "margin_per_lot": 195.0, "spread": 0.25, "stops_level": 50, "price": 3892.0, "typical_stop": 5.0, "session_open": True},
    "XAGUSDm": {"role": "entry", "tick_size": 0.001, "tick_value": 0.05, "volume_min": 0.01, "volume_step": 0.01, "volume_max": 50, "margin_per_lot": 80.0, "spread": 0.02, "stops_level": 40, "price": 32.4, "typical_stop": 0.15, "session_open": True},
    "USOILm": {"role": "entry", "tick_size": 0.01, "tick_value": 1.0, "volume_min": 0.01, "volume_step": 0.01, "volume_max": 50, "margin_per_lot": 120.0, "spread": 0.04, "stops_level": 30, "price": 74.2, "typical_stop": 0.40, "session_open": True},
    "USDJPYm": {"role": "entry", "tick_size": 0.001, "tick_value": 0.6253, "volume_min": 0.01, "volume_step": 0.01, "volume_max": 100, "margin_per_lot": 50.0, "spread": 0.012, "stops_level": 20, "price": 159.9, "typical_stop": 0.20, "session_open": True},
    "EURUSDm": {"role": "entry", "tick_size": 1e-5, "tick_value": 1.0, "volume_min": 0.01, "volume_step": 0.01, "volume_max": 100, "margin_per_lot": 55.0, "spread": 0.00008, "stops_level": 20, "price": 1.1066, "typical_stop": 0.0015, "session_open": True},
    "USTEC_x100m": {"role": "entry", "tick_size": 0.01, "tick_value": 1.0, "volume_min": 0.01, "volume_step": 0.01, "volume_max": 20, "margin_per_lot": 250.0, "spread": 1.5, "stops_level": 80, "price": 20150.0, "typical_stop": 40.0, "session_open": True},
    "DXYm": {"role": "context", "tick_size": 0.001, "tick_value": 1.0, "volume_min": 0.01, "volume_step": 0.01, "volume_max": 20, "margin_per_lot": 40.0, "spread": 0.02, "stops_level": 20, "price": 104.2, "typical_stop": 0.2, "session_open": True},
}

NODE_IDS = ["mt5", "validator", "scope", "whales", "debate", "core", "risk", "exec", "dxy", "kill"]
AGENT_NODE = {
    "SYSTEM": "mt5",
    "DATA": "validator",
    "SCOPE": "scope",
    "WHALES": "whales",
    "DEBATE": "debate",
    "CORE": "core",
    "RISK": "risk",
    "EXEC": "exec",
}

DEFAULT_SETTINGS = {
    "theme": "dark",
    "timezone": "Asia/Makassar",
    "refresh_ms": 2000,
    "log_retention_days": 14,
    "token_usd_per_million": 5.0,
    "language": "id",
    "app_title": "JARVIS // TRADE-BREIN",
    "calendar_provider": "csv",
    "net_check_url": "https://example.com",
    "grok_price_in_per_million": None,
    "grok_price_out_per_million": None,
    "grok_daily_token_budget": 100000,
    "grok_daily_usd_budget": None,
}

TIMEZONES = ["Asia/Makassar", "Asia/Jakarta", "UTC"]


def _read_json(path, default):
    if not path.exists():
        return default
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default
    return data if isinstance(data, dict) else default


def _write_json(path, data):
    ensure_dirs()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def symbols_path():
    return DATA / "symbols.json"


def default_symbols():
    rows = []
    for name, spec in SYMBOL_SPECS.items():
        rows.append({"name": name, "enabled": True, "role": spec["role"]})
    return {"symbols": rows}


def read_symbols():
    raw = _read_json(symbols_path(), default_symbols())
    known = {row["name"]: row for row in raw.get("symbols", []) if isinstance(row, dict) and row.get("name") in SYMBOL_SPECS}
    rows = []
    for name, spec in SYMBOL_SPECS.items():
        saved = known.get(name, {})
        rows.append({
            "name": name,
            "enabled": bool(saved.get("enabled", True)),
            "role": spec["role"],
        })
    return {"symbols": rows}


def write_symbol_enabled(name, enabled):
    if name not in SYMBOL_SPECS:
        raise KeyError(name)
    doc = read_symbols()
    for row in doc["symbols"]:
        if row["name"] == name:
            row["enabled"] = bool(enabled)
    _write_json(symbols_path(), doc)
    events.append_audit("symbol_change", f"Simbol {name} {'aktif' if enabled else 'nonaktif'}", {"symbol": name, "enabled": bool(enabled)})
    return doc


def settings_path():
    return DATA / "settings.json"


def read_settings():
    raw = _read_json(settings_path(), dict(DEFAULT_SETTINGS))
    out = dict(DEFAULT_SETTINGS)
    if raw.get("theme") in {"dark", "light"}:
        out["theme"] = raw["theme"]
    if raw.get("timezone") in TIMEZONES:
        out["timezone"] = raw["timezone"]
    try:
        refresh = int(raw.get("refresh_ms", out["refresh_ms"]))
        if 500 <= refresh <= 30000:
            out["refresh_ms"] = refresh
    except (TypeError, ValueError):
        pass
    try:
        days = int(raw.get("log_retention_days", out["log_retention_days"]))
        if 1 <= days <= 90:
            out["log_retention_days"] = days
    except (TypeError, ValueError):
        pass
    try:
        rate = float(raw.get("token_usd_per_million", out["token_usd_per_million"]))
        if 0 <= rate <= 100:
            out["token_usd_per_million"] = rate
    except (TypeError, ValueError):
        pass
    if raw.get("language") in {"id", "en"}:
        out["language"] = raw["language"]
    title = raw.get("app_title")
    if isinstance(title, str) and 3 <= len(title.strip()) <= 80:
        out["app_title"] = title.strip()
    if raw.get("calendar_provider") in {"csv", "http"}:
        out["calendar_provider"] = raw["calendar_provider"]
    url = raw.get("net_check_url")
    if isinstance(url, str) and url.startswith("https://") and len(url) < 200:
        out["net_check_url"] = url
    for key in ("grok_price_in_per_million", "grok_price_out_per_million", "grok_daily_usd_budget"):
        value = raw.get(key, out[key])
        if value is None or value == "":
            out[key] = None
        else:
            try:
                number = float(value)
            except (TypeError, ValueError):
                number = None
            if number is not None and 0 <= number <= 100:
                out[key] = number
    try:
        budget = int(raw.get("grok_daily_token_budget", out["grok_daily_token_budget"]))
        from dashboard_api.hard_limits import GROK_TOKEN_BUDGET_MAX, GROK_TOKEN_BUDGET_MIN
        if GROK_TOKEN_BUDGET_MIN <= budget <= GROK_TOKEN_BUDGET_MAX:
            out["grok_daily_token_budget"] = budget
    except (TypeError, ValueError):
        pass
    return out


def write_settings(payload):
    _write_json(settings_path(), payload)
    return read_settings()


def account_path():
    return DATA / "account.json"


def paper_path():
    return DATA / "paper.json"


def read_account():
    # TODO: sambungkan ke jurnal EXEC asli. File ini diisi mock feeder atau sistem trading.
    # Dashboard membaca data/config.json (bukan cache import config.py) supaya UI
    # menampilkan nilai tersimpan. Proses trading tetap overlay saat sesi berikutnya.
    from dashboard_api.services.config_store import read_config
    cfg = read_config()
    VIRTUAL_CAPITAL = float(cfg["virtual_capital"])
    ACTIVE_PROFILE = cfg["active_profile"]
    PROFILES = cfg["profiles"]
    base = {
        "virtual_capital": VIRTUAL_CAPITAL,
        "equity": VIRTUAL_CAPITAL,
        "peak": VIRTUAL_CAPITAL,
        "session_start": VIRTUAL_CAPITAL,
        "positions": [],
        "server_offset_hours": 0,
        "mt5_connected": False,
        "mt5_message": "Mode tanpa terminal. MT5 tidak dipanggil dashboard.",
        "grok_tokens_today": 0,
        "grok_last_ok": None,
        "grok_last_message": "Belum dites",
        "updated_at": None,
    }
    raw = _read_json(account_path(), {})
    for key in ("equity", "peak", "session_start", "virtual_capital", "server_offset_hours", "grok_tokens_today"):
        if isinstance(raw.get(key), (int, float)) and not isinstance(raw.get(key), bool):
            base[key] = raw[key]
    if isinstance(raw.get("positions"), list):
        base["positions"] = raw["positions"]
    if isinstance(raw.get("mt5_connected"), bool):
        base["mt5_connected"] = raw["mt5_connected"]
    if isinstance(raw.get("mt5_message"), str):
        base["mt5_message"] = raw["mt5_message"][:240]
    if isinstance(raw.get("grok_last_message"), str):
        base["grok_last_message"] = raw["grok_last_message"][:240]
    if raw.get("grok_last_ok") in {True, False, None}:
        base["grok_last_ok"] = raw.get("grok_last_ok")
    if isinstance(raw.get("updated_at"), str):
        base["updated_at"] = raw["updated_at"]
    base["active_profile"] = ACTIVE_PROFILE
    base["profile"] = PROFILES[ACTIVE_PROFILE]
    return base


def write_account(data):
    _write_json(account_path(), data)


def read_paper():
    raw = _read_json(paper_path(), {"journal": [], "equity_curve": []})
    journal = raw.get("journal") if isinstance(raw.get("journal"), list) else []
    curve = raw.get("equity_curve") if isinstance(raw.get("equity_curve"), list) else []
    return {"journal": journal, "equity_curve": curve}


def write_paper(data):
    _write_json(paper_path(), data)


def write_status_snapshot(doc=None):
    """Tulis data/status.json. Dipakai mock; sistem trading boleh menimpa file yang sama."""
    payload = doc if isinstance(doc, dict) else build_status()
    slim = {
        "updated_at": payload.get("updated_at"),
        "mode": payload.get("mode"),
        "nodes": payload.get("nodes"),
        "kill_switch": payload.get("kill_switch"),
        "equity": payload.get("equity"),
        "peak": payload.get("peak"),
        "drawdown_pct": payload.get("drawdown_pct"),
        "session_loss_pct": payload.get("session_loss_pct"),
        "open_positions": payload.get("open_positions"),
        "mt5_connected": payload.get("mt5_connected"),
        "server_offset_hours": payload.get("server_offset_hours"),
        "grok_tokens_today": payload.get("grok_tokens_today"),
        "data_age_sec": payload.get("data_age_sec"),
        "corrupt_lines": payload.get("corrupt_lines"),
    }
    _write_json(DATA / "status.json", slim)
    return slim


def read_kill_switch():
    """Baca file lock. Tidak ada trigger dan tidak ada penghapusan."""
    from risk_engine.kill_switch import KillSwitch
    from dashboard_api.paths import LOGS
    ks = KillSwitch(str(LOGS / "KILL_SWITCH.lock"))
    active = bool(ks.is_active())
    raw = ks.reason() if active else ""
    since, _, reason = raw.partition("|")
    return {
        "active": active,
        "raw": raw,
        "since": since.strip(),
        "reason": (reason or raw).strip(),
        "reset_hint": r"Reset manual: hapus file logs\KILL_SWITCH.lock. Dashboard tidak bisa mereset.",
    }


def risk_snapshot():
    from risk_engine.drawdown import DrawdownMonitor
    account = read_account()
    cfg = account["profile"]
    equity = float(account["equity"] or 0)
    peak = float(account["peak"] or equity or 1)
    session_start = float(account["session_start"] or account["virtual_capital"] or 1)
    if session_start <= 0:
        session_start = 1.0
    if peak <= 0:
        peak = max(equity, 1.0)
    monitor = DrawdownMonitor(equity or session_start)
    monitor.peak = peak
    monitor.session_start = session_start
    monitor.equity = equity
    status = monitor.status(cfg)
    positions = []
    for pos in account["positions"]:
        if not isinstance(pos, dict):
            continue
        positions.append({
            "symbol": str(pos.get("symbol", "")),
            "direction": str(pos.get("direction", "")),
            "lot": pos.get("lot", 0),
            "entry": pos.get("entry", 0),
            "stop": pos.get("stop", 0),
            "risk_usd": pos.get("risk_usd", 0),
            "margin_usd": pos.get("margin_usd", 0),
        })
    total_risk = sum(float(p.get("risk_usd") or 0) for p in positions)
    total_margin = sum(float(p.get("margin_usd") or 0) for p in positions)
    capital = float(account["virtual_capital"]) or 1.0
    return {
        "virtual_capital": capital,
        "equity": account["equity"],
        "peak": account["peak"],
        "drawdown_pct": status["drawdown_pct"],
        "max_drawdown_pct": cfg["max_drawdown_pct"],
        "session_loss_pct": status["daily_loss_pct"],
        "daily_loss_limit_pct": cfg["daily_loss_limit_pct"],
        "open_positions": len(positions),
        "max_open_positions": cfg["max_open_positions"],
        "total_risk_usd": total_risk,
        "risk_limit_usd": capital * cfg["max_total_risk_pct"] / 100,
        "total_margin_usd": total_margin,
        "margin_limit_usd": capital * cfg["max_margin_pct"] / 100,
        "positions": positions,
        "kill_switch": read_kill_switch(),
        "active_profile": account["active_profile"],
    }


def _parse_ts(value):
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
    except ValueError:
        try:
            return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        except ValueError:
            return None


def _min_lot_fit(name, spec, commission, capital, risk_pct):
    if spec["role"] != "entry":
        return None
    stop = spec["typical_stop"]
    loss = stop / spec["tick_size"] * spec["tick_value"]
    spread_cost = spec["spread"] / spec["tick_size"] * spec["tick_value"]
    need = spec["volume_min"] * (loss + spread_cost + commission)
    budget = capital * risk_pct / 100
    return {
        "min_lot_risk_usd": round(need, 2),
        "risk_budget_usd": round(budget, 2),
        "fits": need <= budget + 1e-9,
        "note": f"Perkiraan stop tipikal {stop} untuk {name}. Keputusan akhir tetap di RISK.",
    }


def build_status(symbol_filter=""):
    from dashboard_api.services.config_store import read_config
    cfg_doc = read_config()
    PROFILES = cfg_doc["profiles"]
    ACTIVE_PROFILE = cfg_doc["active_profile"]
    account = read_account()
    snap = risk_snapshot()
    now = datetime.now(timezone.utc)
    hour_ago = now - timedelta(hours=1)
    with events._lock:
        recent = list(events.bus_recent)
    symbols_doc = read_symbols()
    enabled = {row["name"]: row["enabled"] for row in symbols_doc["symbols"]}

    def match(event):
        if not symbol_filter:
            return True
        sym = event.get("symbol") or ""
        return sym in {symbol_filter, ""}

    filtered = [e for e in recent if match(e)]
    nodes = {}
    for node in NODE_IDS:
        nodes[node] = {"id": node, "status": "idle", "updated_at": None, "latency_ms": None, "errors_1h": 0, "spark": [0] * 12, "last_summary": ""}

    for event in filtered:
        node = AGENT_NODE.get(event.get("agent"))
        if event.get("symbol") == "DXYm":
            node = node or "dxy"
            if event.get("agent") in {"DATA", "SYSTEM"}:
                node = "dxy"
        if node is None:
            continue
        slot = nodes[node]
        ts = _parse_ts(event.get("ts"))
        slot["updated_at"] = event.get("ts")
        slot["last_summary"] = event.get("summary") or ""
        level = event.get("level")
        if level == "error" or event.get("type") == "error":
            slot["status"] = "error"
        elif level == "warn":
            slot["status"] = "warn"
        elif event.get("type") in {"heartbeat", "status", "input"}:
            slot["status"] = "running"
        else:
            slot["status"] = "ok"
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        if isinstance(data.get("latency_ms"), (int, float)):
            slot["latency_ms"] = data["latency_ms"]
        if ts and ts >= hour_ago and (level == "error" or event.get("type") == "error"):
            slot["errors_1h"] += 1
        if ts:
            age = (now - ts).total_seconds()
            bucket = 11 - int(min(11, age // 10))
            if 0 <= bucket <= 11:
                slot["spark"][bucket] += 1

    file_status = _read_json(DATA / "status.json", {})
    file_nodes = file_status.get("nodes") if isinstance(file_status.get("nodes"), dict) else {}
    for nid, node in nodes.items():
        if node["status"] != "idle":
            continue
        patch = file_nodes.get(nid)
        if not isinstance(patch, dict):
            continue
        for key in ("status", "updated_at", "latency_ms", "errors_1h", "last_summary", "spark"):
            if key in patch:
                node[key] = patch[key]

    if not enabled.get("DXYm", True):
        nodes["dxy"]["status"] = "disabled"
        nodes["dxy"]["last_summary"] = "Konteks DXYm dimatikan"
    kill = snap["kill_switch"]
    nodes["kill"]["status"] = "error" if kill["active"] else "ok"
    nodes["kill"]["updated_at"] = kill["since"] or None
    nodes["kill"]["last_summary"] = kill["reason"] if kill["active"] else "Tidak aktif"
    if not account["mt5_connected"]:
        if nodes["mt5"]["status"] == "idle":
            nodes["mt5"]["status"] = "warn"
            nodes["mt5"]["last_summary"] = account["mt5_message"]

    ages = {}
    for name in SYMBOL_SPECS:
        ages[name] = None
    for event in reversed(recent):
        sym = event.get("symbol")
        if sym in ages and ages[sym] is None:
            ts = _parse_ts(event.get("ts"))
            if ts:
                ages[sym] = round((now - ts).total_seconds(), 1)

    cfg = PROFILES[ACTIVE_PROFILE]
    symbol_rows = []
    for name, spec in SYMBOL_SPECS.items():
        fit = _min_lot_fit(name, spec, cfg["commission_per_lot_usd"], snap["virtual_capital"], cfg["risk_per_trade_pct"])
        symbol_rows.append({
            "name": name,
            "role": spec["role"],
            "enabled": enabled.get(name, True),
            "spread": spec["spread"],
            "volume_min": spec["volume_min"],
            "volume_step": spec["volume_step"],
            "tick_size": spec["tick_size"],
            "tick_value": spec["tick_value"],
            "margin_per_lot": spec["margin_per_lot"],
            "stops_level": spec["stops_level"],
            "tick_age_sec": ages.get(name),
            "session_open": spec["session_open"],
            "fit": fit,
        })

    data_age = None
    stamps = [a for a in ages.values() if a is not None]
    if stamps:
        data_age = min(stamps)
    elif account.get("updated_at"):
        ts = _parse_ts(account["updated_at"])
        if ts:
            data_age = round((now - ts).total_seconds(), 1)

    flow = False
    if recent:
        last = _parse_ts(recent[-1].get("ts"))
        flow = bool(last and (now - last).total_seconds() < 4)

    return {
        "mode": __import__("os").environ.get("DASHBOARD_MODE", "mock"),
        "mt5_connected": account["mt5_connected"],
        "mt5_message": account["mt5_message"],
        "kill_switch": kill,
        "commission_placeholder": (not _commission_confirmed()) and float(cfg["commission_per_lot_usd"]) == 7.0,
        "commission_per_lot_usd": cfg["commission_per_lot_usd"],
        "data_age_sec": data_age,
        "equity": snap["equity"],
        "peak": snap["peak"],
        "drawdown_pct": snap["drawdown_pct"],
        "session_loss_pct": snap["session_loss_pct"],
        "open_positions": snap["open_positions"],
        "server_offset_hours": account["server_offset_hours"],
        "grok_tokens_today": account["grok_tokens_today"],
        "nodes": nodes,
        "symbols": symbol_rows,
        "corrupt_lines": events.corrupt_total(),
        "flowing": flow,
        "round": _count_today({"signal", "heartbeat", "decision", "handoff"}),
        "decisions_today": _count_today({"decision", "veto"}),
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
    }


def _count_today(types):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        rows = events.query_events(limit=500)
    except Exception:
        return 0
    return sum(1 for row in rows if str(row.get("ts") or "").startswith(today) and row.get("type") in types)


def _commission_confirmed():
    from dashboard_api.services.config_store import read_config
    return bool(read_config().get("commission_confirmed"))


def correlation_matrix():
    # TODO: hitung rolling dari data pasar asli. Angka ini mock.
    names = list(SYMBOL_SPECS)
    seed = {
        ("XAUUSDm", "XAGUSDm"): 0.82,
        ("XAUUSDm", "DXYm"): -0.61,
        ("EURUSDm", "DXYm"): -0.78,
        ("USDJPYm", "DXYm"): 0.66,
        ("EURUSDm", "USDJPYm"): -0.42,
        ("USOILm", "XAUUSDm"): 0.28,
        ("USTEC_x100m", "DXYm"): -0.35,
    }
    matrix = []
    for a in names:
        row = []
        for b in names:
            if a == b:
                row.append(1.0)
            else:
                row.append(seed.get((a, b), seed.get((b, a), 0.12)))
        matrix.append(row)
    positions = read_account().get("positions") or []
    open_names = [p.get("symbol") for p in positions if isinstance(p, dict)]
    warnings = []
    for i, a in enumerate(open_names):
        for b in open_names[i + 1:]:
            if a in names and b in names:
                value = matrix[names.index(a)][names.index(b)]
                if abs(value) >= 0.7:
                    warnings.append(f"{a} dan {b} berkorelasi {value:.2f}")
    return {"symbols": names, "matrix": matrix, "warnings": warnings, "mock": True}


def risk_decisions(limit=40):
    rows = []
    for event in events.query_events(agent="RISK", limit=300):
        if event.get("type") not in {"decision", "error"}:
            continue
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        reasons = data.get("reasons") if isinstance(data.get("reasons"), list) else []
        rows.append({
            "ts": event.get("ts"),
            "symbol": event.get("symbol"),
            "approved": bool(data.get("approved")),
            "lot": data.get("lot"),
            "risk_usd": data.get("risk_usd"),
            "reasons": [str(r) for r in reasons],
            "summary": event.get("summary"),
        })
        if len(rows) >= limit:
            break
    return rows


def paper_stats():
    paper = read_paper()
    journal = paper["journal"]
    wins = [t for t in journal if isinstance(t, dict) and float(t.get("result_usd") or 0) > 0]
    rs = [float(t.get("r_multiple") or 0) for t in journal if isinstance(t, dict)]
    equity = [float(p.get("equity")) for p in paper["equity_curve"] if isinstance(p, dict) and isinstance(p.get("equity"), (int, float))]
    peak = equity[0] if equity else 0
    max_dd = 0.0
    for value in equity:
        peak = max(peak, value)
        if peak:
            max_dd = max(max_dd, (peak - value) / peak * 100)
    count = len([t for t in journal if isinstance(t, dict)])
    return {
        "journal": journal,
        "equity_curve": paper["equity_curve"],
        "trade_count": count,
        "win_rate": (len(wins) / count * 100) if count else 0,
        "avg_r": (sum(rs) / len(rs)) if rs else 0,
        "max_drawdown_pct": max_dd,
        "disclaimer": "Hasil dari akun spread/komisi berbeda tidak valid untuk akun lain.",
    }
