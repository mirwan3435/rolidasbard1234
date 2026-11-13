"""Penghasil event palsu. Tidak menyentuh MT5 dan tidak membuat KILL_SWITCH.lock."""
import random
import threading
import time
from datetime import datetime, timezone

from dashboard_api.services import events
from dashboard_api.services.state import (
    SYMBOL_SPECS,
    read_account,
    read_paper,
    read_symbols,
    write_account,
    write_paper,
    write_status_snapshot,
)

_stop = threading.Event()
_thread = None

REJECTIONS = [
    "Spread terlalu besar dibanding jarak stop",
    "Lot minimum 0.01 butuh risiko 12.40 USD, batas 1.90 USD",
    "Posisi terbuka sudah 2 (maks 2)",
    "Data tidak valid, trade ditolak",
    "Batas rugi sesi terlewati (5.2%)",
    "Sudah ada posisi terbuka di EURUSDm",
    "Total risiko 4.10 melebihi batas 3.80",
    "Stop berada di sisi yang salah dari entry",
]


def _ts():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _event(agent, type_, summary, symbol="", level="info", data=None, run_id=""):
    events.append_event({
        "ts": _ts(),
        "agent": agent,
        "type": type_,
        "symbol": symbol,
        "level": level,
        "summary": summary,
        "data": data or {},
        "run_id": run_id,
    })


def _seed_paper(equity):
    journal = []
    curve = []
    value = equity
    reasons = ["SCOPE skor 71", "WHALES netral", "DEBATE condong tunggu"]
    for index in range(8):
        result = round(random.choice([1.2, -0.8, 0.6, -1.1, 1.8, -0.4]), 2)
        value = round(value + result, 2)
        symbol = random.choice(["EURUSDm", "USDJPYm"])
        journal.append({
            "id": index + 1,
            "symbol": symbol,
            "direction": random.choice(["BUY", "SELL"]),
            "entry": 1.1,
            "exit": 1.101,
            "lot": 0.01,
            "result_usd": result,
            "spread_cost_usd": 0.08,
            "commission_usd": 0.07,
            "r_multiple": round(result / 1.5, 2),
            "reason": random.choice(reasons),
            "scope_score": random.randint(40, 90),
            "closed_at": _ts(),
        })
        curve.append({"ts": _ts(), "equity": value})
    write_paper({"journal": journal, "equity_curve": curve})
    return value


def _bootstrap_account():
    account = read_account()
    if account.get("updated_at"):
        return
    equity = _seed_paper(float(account["virtual_capital"]))
    account.update({
        "equity": equity,
        "peak": max(float(account["virtual_capital"]), equity),
        "session_start": float(account["virtual_capital"]),
        "positions": [{
            "symbol": "EURUSDm",
            "direction": "BUY",
            "lot": 0.01,
            "entry": 1.1066,
            "stop": 1.1051,
            "risk_usd": 1.57,
            "margin_usd": 0.55,
        }],
        "server_offset_hours": 2,
        "mt5_connected": False,
        "mt5_message": "MOCK: MT5 tidak terhubung. Data simbol disimulasikan.",
        "grok_tokens_today": 1200,
        "updated_at": _ts(),
    })
    write_account(account)


def _loop():
    _bootstrap_account()
    counter = 0
    symbols = [name for name in SYMBOL_SPECS if name != "DXYm"]
    while not _stop.is_set():
        counter += 1
        run_id = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") + f"-{counter:04d}"
        enabled = {row["name"] for row in read_symbols()["symbols"] if row["enabled"]}
        symbol = random.choice(symbols)
        if symbol not in enabled:
            symbol = "EURUSDm"
        latency = random.randint(8, 240)
        _event("SYSTEM", "heartbeat", "Tick mock masuk", symbol, data={"latency_ms": latency}, run_id=run_id)
        _event("DATA", "output", "Data tervalidasi" if random.random() > 0.08 else "Gap candle", symbol,
               level="info" if random.random() > 0.08 else "warn", data={"latency_ms": latency, "input": {"bars": 120}, "output": {"valid": True}}, run_id=run_id)
        if "DXYm" in enabled and random.random() > 0.4:
            _event("DATA", "output", "DXY konteks diperbarui", "DXYm", data={"latency_ms": 20, "bias": random.choice(["kuat", "lemah", "netral"])}, run_id=run_id)
        score = random.randint(35, 92)
        _event("SCOPE", "output", f"Zona skor {score}", symbol, data={"latency_ms": random.randint(5, 40), "output": {"score": score, "kind": "order block"}}, run_id=run_id)
        _event("WHALES", "output", "Aliran besar netral", symbol, data={"latency_ms": random.randint(10, 80)}, run_id=run_id)
        _event("DEBATE", "output", "Debat selesai, tidak ada konsensus kuat", symbol, data={"latency_ms": random.randint(40, 300), "tokens": random.randint(80, 400)}, run_id=run_id)
        _event("CORE", "output", "Usulan dikirim ke RISK", symbol, data={"latency_ms": random.randint(30, 200), "output": {"stance": "tahan"}}, run_id=run_id)
        heavy = symbol in {"XAUUSDm", "XAGUSDm", "USOILm", "USTEC_x100m"}
        reject = heavy or random.random() < 0.35
        if reject:
            reason = REJECTIONS[0] if not heavy else REJECTIONS[1]
            if random.random() < 0.3:
                reason = random.choice(REJECTIONS)
            _event("RISK", "decision", f"Ditolak: {reason}", symbol, level="warn",
                   data={"approved": False, "lot": 0, "risk_usd": 0, "reasons": [reason], "latency_ms": 4}, run_id=run_id)
        else:
            _event("RISK", "decision", "Trade disetujui, lot 0.01", symbol, data={"approved": True, "lot": 0.01, "risk_usd": 1.57, "reasons": [], "latency_ms": 4}, run_id=run_id)
            _event("EXEC", "output", "Paper fill lot 0.01", symbol, data={"latency_ms": 6, "paper": True}, run_id=run_id)
        if random.random() < 0.05:
            _event("CORE", "error", "Timeout contoh (mock)", symbol, level="error", data={"latency_ms": 8000, "trace": "TimeoutError: mock"}, run_id=run_id)
        account = read_account()
        drift = random.choice([-0.15, 0.1, 0.0, -0.05, 0.2])
        equity = round(float(account["equity"]) + drift, 2)
        account["equity"] = equity
        account["peak"] = round(max(float(account["peak"]), equity), 2)
        account["updated_at"] = _ts()
        account["grok_tokens_today"] = int(account.get("grok_tokens_today") or 0) + random.randint(10, 80)
        write_account(account)
        paper = read_paper()
        curve = paper["equity_curve"][-80:]
        curve.append({"ts": _ts(), "equity": equity})
        write_paper({"journal": paper["journal"], "equity_curve": curve})
        try:
            write_status_snapshot()
        except Exception:
            pass
        _stop.wait(1.3)


def start():
    global _thread
    if _thread is not None and _thread.is_alive():
        return
    _stop.clear()
    _thread = threading.Thread(target=_loop, name="mock-feeder", daemon=True)
    _thread.start()


def stop():
    _stop.set()
