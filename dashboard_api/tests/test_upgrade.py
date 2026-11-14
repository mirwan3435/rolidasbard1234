import os
from pathlib import Path

os.environ.setdefault("DASHBOARD_TEST", "1")
os.environ.setdefault("DASHBOARD_MODE", "live")
os.environ.setdefault("DASHBOARD_DISABLE_TAIL", "1")
_ROOT = Path(__file__).resolve().parents[2]
_TMP = _ROOT / ".pytest_dashboard"
os.environ.setdefault("DASHBOARD_DATA_DIR", str(_TMP / "data"))
os.environ.setdefault("DASHBOARD_LOG_DIR", str(_TMP / "logs"))
os.environ.setdefault("DASHBOARD_ENV_FILE", str(_TMP / ".env"))

from fastapi.testclient import TestClient

from dashboard_api.main import app
from dashboard_api.security import TOKEN
from dashboard_api.services.grok_client import parse_verdict
from dashboard_api.services.lab.engine import kpis, run_backtest
from dashboard_api.services.netguard import public_url
from strategies.reference_atr_breakout import detect

ORIGIN = {"Origin": "http://127.0.0.1:5173", "X-Dashboard-Token": TOKEN}


def _bars():
    bars = []
    price = 100.0
    for i in range(40):
        price += 0.4
        bars.append({"time": str(i), "open": price, "high": price + 0.2, "low": price - 0.2, "close": price + 0.15, "volume": 1})
    return bars


def test_new_routes_need_token():
    with TestClient(app) as client:
        assert client.get("/api/connections").status_code == 401
        assert client.get("/api/costs").status_code == 401
        assert client.get("/api/promotion").status_code == 401
        ok = client.get("/api/connections", headers=ORIGIN)
        assert ok.status_code == 200
        assert len(ok.json()["connections"]) == 8


def test_micro_profile_cannot_loosen():
    with TestClient(app) as client:
        current = client.get("/api/config").json()["config"]
        current["profiles"]["micro_10usd"]["risk_per_trade_pct"] = 4
        current["confirm"] = True
        response = client.put("/api/config", json=current, headers=ORIGIN)
        assert response.status_code == 422


def test_parse_verdict_rejects_raise_and_extra():
    good = {
        "signal_id": "abc",
        "verdict": "reduce",
        "score_adjust": -3,
        "reasons": ["lebar"],
        "risk_flags": ["spread"],
        "confidence": 0.4,
    }
    assert parse_verdict(good)["ok"] is True
    raised = dict(good)
    raised["score_adjust"] = 2
    assert parse_verdict(raised)["verdict"] == "reject"
    extra = dict(good)
    extra["lot"] = 1
    assert parse_verdict(extra)["ok"] is False
    assert parse_verdict("bukan json")["verdict"] == "reject"


def test_backtest_rules():
    bars = _bars()
    spec = {"tick_size": 0.01, "tick_value": 1, "volume_min": 0.01, "volume_step": 0.01, "volume_max": 5, "spread": 0.02}
    result = run_backtest(bars, detect, {"atr_period": 5, "atr_sl_mult": 1, "atr_tp_mult": 2}, spec, 1000, 1, 1, 5, slippage_points=1)
    assert result["trades"], "referensi harus menghasilkan trade di tren naik"
    trade = result["trades"][0]
    assert trade["entry"] == bars[trade["entry_index"]]["open"]
    both = [{"open": 10, "high": 12, "low": 8, "close": 10, "time": "0"}]
    price, reason = __import__("dashboard_api.services.lab.engine", fromlist=["_resolve"])._resolve(
        "buy", {"high": 12, "low": 8}, 9, 11
    )
    assert reason == "sl" and price == 9
    costly = run_backtest(bars, detect, {"atr_period": 5}, spec, 1000, 1, 50, 80, slippage_points=0)
    plain = run_backtest(bars, detect, {"atr_period": 5}, spec, 1000, 1, 0, 80, slippage_points=0)
    if costly["trades"] and plain["trades"]:
        assert sum(t["result_usd"] for t in costly["trades"]) < sum(t["result_usd"] for t in plain["trades"])
    assert "trade_count" in kpis(result)


def test_ssrf_blocks_loopback():
    assert public_url("http://127.0.0.1/secret") is False
    assert public_url("http://localhost/x") is False
    assert public_url("file:///etc/passwd") is False


def test_research_rejects_local_url():
    with TestClient(app) as client:
        response = client.post("/api/research/ingest", json={"kind": "url", "value": "http://127.0.0.1/admin"}, headers=ORIGIN)
        assert response.status_code == 422
        pasted = client.post("/api/research/ingest", json={"kind": "text", "value": "catatan SMC dan ICT untuk diuji"}, headers=ORIGIN)
        assert pasted.status_code == 200
        assert "SMC" in pasted.json()["concepts"]


def test_scope_params_stay_bounded_and_signal_rejects_extra():
    from datetime import datetime, timedelta, timezone
    from brain.signal import validate_signal
    now = datetime.now(timezone.utc)
    raw = {
        "id": "a", "ts": now.isoformat(), "symbol": "XAUUSD", "broker_symbol": "XAUUSDm",
        "direction": "buy", "strategy": "smc", "mode": "scalp", "tf_entry": "M5", "tf_bias": "H1",
        "order_type": "market", "entry": 100.0, "sl": 99.0, "tp": 102.0, "rr": 2.0, "atr": 1.0,
        "spread_at_signal": 0.1, "tags": [], "score_components": {}, "score": 80,
        "valid_until": (now + timedelta(minutes=5)).isoformat(), "invalidation": "zona batal",
        "source": "sample",
    }
    assert validate_signal(raw)["ok"] is True
    raw["lot"] = 1
    assert validate_signal(raw)["ok"] is False
    with TestClient(app) as client:
        denied = client.put(
            "/api/agents/SCOPE",
            json={"enabled": True, "model": "x", "temperature": 0.2, "max_tokens": 100, "timeout_sec": 10, "system_prompt": "x", "output_schema": {}},
            headers=ORIGIN,
        )
        assert denied.status_code == 403
        saved = client.put("/api/agents/SCOPE/params", json={"params": {"min_score": 82}}, headers=ORIGIN)
        assert saved.status_code == 200
        assert saved.json()["params"]["min_score"] == 82
        loose = client.put("/api/agents/SCOPE/params", json={"params": {"min_score": 10}}, headers=ORIGIN)
        assert loose.status_code == 422


def test_knowledge_feedback_and_budget(tmp_path, monkeypatch):
    with TestClient(app) as client:
        saved = client.post("/api/knowledge/cards/bos/verdict", json={"verdict": "ok", "note": "cocok"}, headers=ORIGIN)
        assert saved.status_code == 200
        from dashboard_api.services import costs
        monkeypatch.setattr(costs, "summary", lambda: {
            "tokens_today": 100, "token_budget": 100, "usd_today": None, "usd_budget": None,
        })
        try:
            costs.budget_guard()
            raised = False
        except costs.BudgetExceeded:
            raised = True
        assert raised is True
