import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ["DASHBOARD_TEST"] = "1"
os.environ["DASHBOARD_MODE"] = "live"
os.environ["DASHBOARD_DISABLE_TAIL"] = "1"

ROOT = Path(__file__).resolve().parents[2]
TMP = ROOT / ".pytest_dashboard"
if TMP.exists():
    import shutil
    shutil.rmtree(TMP, ignore_errors=True)
TMP.mkdir(exist_ok=True)
os.environ["DASHBOARD_DATA_DIR"] = str(TMP / "data")
os.environ["DASHBOARD_LOG_DIR"] = str(TMP / "logs")
os.environ["DASHBOARD_ENV_FILE"] = str(TMP / ".env")

from dashboard_api.main import app  # noqa: E402
from dashboard_api.security import TOKEN  # noqa: E402
from dashboard_api.services import events  # noqa: E402

ORIGIN = {"Origin": "http://127.0.0.1:5173"}


@pytest.fixture()
def client():
    with TestClient(app) as test:
        yield test


def auth(extra=None):
    headers = {"X-Dashboard-Token": TOKEN, **ORIGIN}
    if extra:
        headers.update(extra)
    return headers


def test_health_and_bootstrap(client):
    assert client.get("/api/health").json()["ok"] is True
    denied = client.get("/api/bootstrap")
    assert denied.status_code == 403
    ok = client.get("/api/bootstrap", headers=ORIGIN)
    assert ok.status_code == 200
    assert ok.json()["token"] == TOKEN


def test_host_rejected(client):
    response = client.get("/api/health", headers={"Host": "evil.example"})
    assert response.status_code == 400


def test_write_needs_token(client):
    response = client.put("/api/symbols/EURUSDm", json={"enabled": False}, headers=ORIGIN)
    assert response.status_code == 401
    ok = client.put("/api/symbols/EURUSDm", json={"enabled": True}, headers=auth())
    assert ok.status_code == 200


def test_no_order_or_kill_reset(client):
    schema = client.get("/api/openapi.json").json()
    blob = json.dumps(schema).lower()
    assert "order_send" not in blob
    assert "/reset" not in blob
    for path in schema["paths"]:
        assert "order" not in path.lower()
        assert "kill" not in path.lower()
    source = ""
    for path in (ROOT / "dashboard_api").rglob("*.py"):
        if "tests" in path.parts:
            continue
        source += path.read_text(encoding="utf-8").lower()
    assert "order_send" not in source
    assert ".trigger(" not in source


def test_corrupt_line_skipped():
    before = events.corrupt_total()
    assert events.ingest_line("{bukan json") is None
    assert events.corrupt_total() == before + 1
    event = events.ingest_line('{"agent":"RISK","type":"decision","summary":"ok","symbol":"EURUSDm","level":"info","data":{"approved":true,"reasons":[]}}')
    assert event["agent"] == "RISK"


def test_key_never_leaks(client):
    secret = "xai-TESTSECRET-a1b2"
    saved = client.put("/api/keys/XAI_API_KEY", json={"value": secret}, headers=auth())
    assert saved.status_code == 200
    listing = client.get("/api/keys").json()
    blob = json.dumps(listing)
    assert secret not in blob
    assert listing["slots"][0]["last4"] == "a1b2"
    assert listing["slots"][0]["filled"] is True
    audit = json.dumps(client.get("/api/audit").json())
    assert secret not in audit
    assert secret not in client.get("/api/health").text


def test_env_preserves_other_lines(client):
    path = Path(os.environ["DASHBOARD_ENV_FILE"])
    path.write_text("OTHER_FLAG=keep\nNOTE=jangan hilang\n", encoding="utf-8")
    secret = "telegram-token-zz99"
    response = client.put("/api/keys/TELEGRAM_BOT_TOKEN", json={"value": secret}, headers=auth())
    assert response.status_code == 200
    text = path.read_text(encoding="utf-8")
    assert "OTHER_FLAG=keep" in text
    assert "NOTE=jangan hilang" in text
    assert f"TELEGRAM_BOT_TOKEN={secret}" in text
    body = json.dumps(response.json())
    assert secret not in body


def test_validation_error_hides_secret(client):
    secret = "zz9leak"
    response = client.put("/api/keys/XAI_API_KEY", json={"value": secret}, headers=auth())
    assert response.status_code == 422
    assert secret not in response.text
    assert '"input"' not in response.text


def test_hard_limits_reject(client):
    current = client.get("/api/config").json()["config"]
    current["profiles"]["standard"]["risk_per_trade_pct"] = 9
    current["confirm"] = True
    response = client.put("/api/config", json=current, headers=auth())
    assert response.status_code == 422
    current["profiles"]["standard"]["risk_per_trade_pct"] = 2
    current["profiles"]["standard"]["daily_loss_limit_pct"] = 9
    response = client.put("/api/config", json=current, headers=auth())
    assert response.status_code == 422


def test_config_confirm_and_backup(client):
    current = client.get("/api/config").json()["config"]
    target = round(float(current["virtual_capital"]) + 7, 2)
    if target > 1_000_000:
        target = 95.0
    current["virtual_capital"] = target
    current["confirm"] = False
    preview = client.put("/api/config", json=current, headers=auth())
    assert preview.status_code == 200
    assert preview.json()["needs_confirm"] is True
    assert preview.json()["saved"] is False
    current["confirm"] = True
    saved = client.put("/api/config", json=current, headers=auth())
    assert saved.status_code == 200
    assert saved.json()["saved"] is True
    again = client.get("/api/config").json()["config"]
    assert again["virtual_capital"] == target


def test_symbol_path_traversal(client):
    response = client.put("/api/symbols/..%2F..%2F.env", json={"enabled": True}, headers=auth())
    assert response.status_code in {404, 422}


def test_agent_locked_and_rollback(client):
    locked = client.put(
        "/api/agents/RISK",
        json={
            "enabled": True,
            "model": "x",
            "temperature": 0.2,
            "max_tokens": 100,
            "timeout_sec": 10,
            "system_prompt": "jangan",
            "output_schema": {},
        },
        headers=auth(),
    )
    assert locked.status_code == 403
    scope = client.get("/api/agents/SCOPE").json()
    assert scope["locked"] is True
    body = {
        "enabled": True,
        "model": "",
        "temperature": 0.2,
        "max_tokens": 200,
        "timeout_sec": 15,
        "system_prompt": "versi-satu",
        "output_schema": {"type": "object", "required": ["stance"]},
        "note": "awal",
    }
    first = client.put("/api/agents/DEBATE", json=body, headers=auth())
    assert first.status_code == 200
    v1 = first.json()["versions"][-1]["n"]
    body["system_prompt"] = "versi-dua"
    body["note"] = "ubah"
    second = client.put("/api/agents/DEBATE", json=body, headers=auth())
    assert second.status_code == 200
    rolled = client.post("/api/agents/DEBATE/rollback", json={"version": v1}, headers=auth())
    assert rolled.status_code == 200
    assert rolled.json()["system_prompt"] == "versi-satu"


def test_min_lot_flags(client):
    rows = {row["name"]: row for row in client.get("/api/symbols").json()["symbols"]}
    assert rows["XAUUSDm"]["fit"]["fits"] is False
    assert rows["EURUSDm"]["fit"]["fits"] is True
    assert rows["DXYm"]["role"] == "context"


def test_kill_switch_readonly(client, tmp_path, monkeypatch):
    from risk_engine.kill_switch import KillSwitch
    from dashboard_api import paths
    lock = paths.LOGS / "KILL_SWITCH.lock"
    if lock.exists():
        lock.unlink()
    ks = KillSwitch(str(lock))
    ks.trigger("uji dashboard")
    snap = client.get("/api/risk/state").json()
    assert snap["kill_switch"]["active"] is True
    assert "uji dashboard" in snap["kill_switch"]["reason"]
    assert "reset" in snap["kill_switch"]["reset_hint"].lower()
    schema = client.get("/api/openapi.json").json()["paths"]
    assert not any("kill" in path for path in schema)
    lock.unlink()
