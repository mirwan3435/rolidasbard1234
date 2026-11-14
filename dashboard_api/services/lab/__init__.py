"""Lab backtest: registry plugin, unggah CSV, jalankan di thread."""
import csv
import importlib
import io
import json
import pkgutil
import threading
import uuid
from datetime import datetime, timedelta, timezone

from dashboard_api.paths import DATA, ensure_dirs
from dashboard_api.services import events
from dashboard_api.services.lab.engine import kpis, run_backtest
import strategies

RUNS = {}
_lock = threading.Lock()


def _plugins():
    found = []
    for info in pkgutil.iter_modules(strategies.__path__):
        if info.name in {"common"} or info.name.startswith("_"):
            continue
        module = importlib.import_module(f"strategies.{info.name}")
        if not hasattr(module, "id") or not hasattr(module, "detect"):
            continue
        found.append(module)
    return found


def _plugin(strategy_id):
    for module in _plugins():
        if module.id == strategy_id:
            return module
    raise KeyError(strategy_id)


def discover():
    rows = []
    for module in _plugins():
        rows.append({
            "id": module.id,
            "kind": getattr(module, "kind", "detector"),
            "param_schema": getattr(module, "param_schema", {}),
            "source": getattr(module, "source", "sample"),
            "note": getattr(module, "note", ""),
        })
    return rows


def _runs_dir():
    folder = DATA / "lab" / "runs"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def list_runs():
    rows = []
    folder = _runs_dir()
    for path in sorted(folder.glob("*.json"), reverse=True)[:40]:
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        curve = doc.get("equity_curve") if isinstance(doc.get("equity_curve"), list) else []
        rows.append({
            "id": doc.get("id"),
            "strategy": doc.get("strategy"),
            "symbol": doc.get("symbol"),
            "status": doc.get("status"),
            "created_at": doc.get("created_at"),
            "kpis": doc.get("kpis"),
            "source": doc.get("source"),
            "equity_curve": [{"equity": point.get("equity")} for point in curve[-32:] if isinstance(point, dict)],
        })
    return rows


def get_run(run_id):
    path = _runs_dir() / f"{run_id}.json"
    if not path.is_file():
        raise KeyError(run_id)
    return json.loads(path.read_text(encoding="utf-8"))


def save_history_csv(symbol, timeframe, raw: bytes):
    if timeframe not in {"M1", "M5", "M15"}:
        raise ValueError("Timeframe harus M1, M5, atau M15")
    safe = "".join(ch for ch in symbol if ch.isalnum() or ch in {"_", "."})
    if not safe or safe != symbol:
        raise ValueError("Nama simbol tidak aman")
    text = raw.decode("utf-8-sig")
    if len(text) > 5_000_000:
        raise ValueError("CSV terlalu besar")
    reader = csv.DictReader(io.StringIO(text))
    fields = [name.strip().lower() for name in (reader.fieldnames or [])]
    needed = ["time", "open", "high", "low", "close", "volume"]
    if fields != needed and not set(needed) <= set(fields):
        raise ValueError("Kolom wajib: time,open,high,low,close,volume")
    rows = []
    for row in reader:
        lowered = {k.strip().lower(): v for k, v in row.items() if k}
        rows.append({
            "time": lowered["time"],
            "open": float(lowered["open"]),
            "high": float(lowered["high"]),
            "low": float(lowered["low"]),
            "close": float(lowered["close"]),
            "volume": float(lowered.get("volume") or 0),
        })
    if len(rows) < 30:
        raise ValueError("CSV kurang dari 30 bar")
    folder = DATA / "history"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{safe}_{timeframe}.csv"
    path.write_text(text, encoding="utf-8")
    return {"symbol": safe, "timeframe": timeframe, "bars": len(rows), "source": "real"}


def _load_csv(symbol, timeframe):
    path = DATA / "history" / f"{symbol}_{timeframe}.csv"
    if not path.is_file():
        return []
    return save_rows(path.read_text(encoding="utf-8"))


def save_rows(text):
    reader = csv.DictReader(io.StringIO(text))
    rows = []
    for row in reader:
        lowered = {k.strip().lower(): v for k, v in row.items() if k}
        rows.append({
            "time": lowered["time"],
            "open": float(lowered["open"]),
            "high": float(lowered["high"]),
            "low": float(lowered["low"]),
            "close": float(lowered["close"]),
            "volume": float(lowered.get("volume") or 0),
        })
    return rows


def _load_mt5(symbol, timeframe, date_from, date_to):
    try:
        import MetaTrader5 as mt5
    except Exception:
        return []
    tf = {"M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15}.get(timeframe)
    if tf is None or not mt5.initialize():
        return []
    try:
        start = datetime.fromisoformat(date_from) if date_from else datetime.now(timezone.utc) - timedelta(days=30)
        end = datetime.fromisoformat(date_to) if date_to else datetime.now(timezone.utc)
        rates = mt5.copy_rates_range(symbol, tf, start, end)
    except Exception:
        rates = None
    finally:
        mt5.shutdown()
    if rates is None:
        return []
    rows = []
    for bar in rates:
        rows.append({
            "time": datetime.fromtimestamp(int(bar["time"]), timezone.utc).isoformat(),
            "open": float(bar["open"]),
            "high": float(bar["high"]),
            "low": float(bar["low"]),
            "close": float(bar["close"]),
            "volume": float(bar["tick_volume"]),
        })
    return rows


def _filter_dates(bars, date_from, date_to):
    if not date_from and not date_to:
        return bars
    kept = []
    for bar in bars:
        stamp = str(bar.get("time") or "")
        if date_from and stamp < date_from:
            continue
        if date_to and stamp > date_to:
            continue
        kept.append(bar)
    return kept


def start_run(symbol, timeframe, params, spec, profile, strategy_id="reference_atr_breakout", date_from="", date_to=""):
    module = _plugin(strategy_id)
    bars = _filter_dates(_load_mt5(symbol, timeframe, date_from, date_to), date_from, date_to)
    data_source = "mt5"
    if len(bars) < 30:
        bars = _filter_dates(_load_csv(symbol, timeframe), date_from, date_to)
        data_source = "csv"
    if len(bars) < 30:
        raise FileNotFoundError("Tidak ada CSV history untuk simbol ini")
    run_id = uuid.uuid4().hex[:12]
    doc = {
        "id": run_id,
        "strategy": module.id,
        "symbol": symbol,
        "timeframe": timeframe,
        "status": "running",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
        "params": params,
        "source": "real",
        "data_source": data_source,
        "kind": getattr(module, "kind", "detector"),
        "progress": 0,
        "date_from": date_from,
        "date_to": date_to,
    }
    path = _runs_dir() / f"{run_id}.json"
    path.write_text(json.dumps(doc), encoding="utf-8")

    def _job():
        try:
            events.append_event({
                "ts": doc["created_at"],
                "agent": "PROFILER",
                "type": "lab",
                "symbol": symbol,
                "level": "info",
                "summary": f"Backtest {run_id} mulai",
                "msg": f"Backtest {run_id} mulai",
                "data": {"run_id": run_id, "progress": 10, "source": "real"},
                "run_id": run_id,
            })
            result = run_backtest(
                bars,
                module.detect,
                params,
                spec,
                float(profile.get("virtual_capital_usd") or profile.get("equity") or 95),
                float(profile["risk_per_trade_pct"]),
                float(profile["commission_per_lot_usd"]),
                profile.get("skip_if_min_lot_risk_pct", profile.get("risk_per_trade_pct")),
            )
            doc.update({
                "status": "done",
                "trades": result["trades"],
                "equity_curve": result["equity_curve"],
                "kpis": kpis(result),
                "progress": 100,
                "warning": _commission_warning(profile),
            })
        except Exception as exc:
            doc.update({"status": "error", "error": str(exc)[:200], "progress": 100})
        path.write_text(json.dumps(doc), encoding="utf-8")

    threading.Thread(target=_job, name=f"lab-{run_id}", daemon=True).start()
    return {"run_id": run_id, "status": "running"}


def _commission_warning(profile):
    if profile.get("commission_verified"):
        return ""
    if float(profile.get("commission_per_lot_usd") or 0) == 7.0 or not profile.get("commission_verified"):
        return "Komisi belum diverifikasi. Hasil tidak bisa dipakai sebagai bukti edge."
    return ""
