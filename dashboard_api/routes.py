import subprocess

from fastapi import APIRouter, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from dashboard_api.paths import ROOT
from dashboard_api.security import TOKEN, origin_ok
from dashboard_api.services import agents, config_store, env_io, events, grok_client, state

router = APIRouter(prefix="/api")

APP_VERSION = "1.0.0"


class SymbolBody(BaseModel):
    enabled: bool


class KeyBody(BaseModel):
    value: str = Field(min_length=8, max_length=256)


class AgentBody(BaseModel):
    enabled: bool
    model: str = Field(default="", max_length=80)
    temperature: float = Field(ge=0, le=1.5)
    max_tokens: int = Field(ge=64, le=4000)
    timeout_sec: int = Field(ge=5, le=120)
    system_prompt: str = Field(max_length=20000)
    output_schema: dict
    note: str = Field(default="", max_length=200)


class RollbackBody(BaseModel):
    version: int = Field(ge=1)


class SettingsBody(BaseModel):
    theme: str
    timezone: str
    refresh_ms: int = Field(ge=500, le=30000)
    log_retention_days: int = Field(ge=1, le=90)
    token_usd_per_million: float = Field(ge=0, le=100)
    language: str = "id"
    app_title: str = Field(default="JARVIS // TRADE-BREIN", max_length=80)
    calendar_provider: str = "csv"
    net_check_url: str = "https://example.com"
    grok_price_in_per_million: float | None = None
    grok_price_out_per_million: float | None = None
    grok_daily_token_budget: int = Field(default=100000, ge=1000, le=2_000_000)
    grok_daily_usd_budget: float | None = Field(default=None, ge=0, le=100)


class ConfigBody(BaseModel):
    virtual_capital: float
    active_profile: str
    commission_confirmed: bool = False
    profiles: dict
    confirm: bool = False


def _git_hash():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


@router.get("/bootstrap")
def bootstrap(request: Request):
    origin = request.headers.get("origin", "")
    host = request.headers.get("host", "")
    site = request.headers.get("sec-fetch-site", "")
    if not origin_ok(origin, host, site):
        raise HTTPException(403, "Origin ditolak")
    return {"token": TOKEN, "mode": __import__("os").environ.get("DASHBOARD_MODE", "mock")}


@router.get("/health")
def health():
    return {"ok": True, "version": APP_VERSION}


@router.get("/meta")
def meta():
    account = state.read_account()
    settings = state.read_settings()
    tokens = float(account.get("grok_tokens_today") or 0)
    rate = float(settings["token_usd_per_million"])
    return {
        "version": APP_VERSION,
        "git": _git_hash(),
        "corrupt_lines": events.corrupt_total(),
        "grok_last_ok": account.get("grok_last_ok"),
        "grok_last_message": account.get("grok_last_message"),
        "grok_tokens_today": tokens,
        "estimated_cost_today": round(tokens / 1_000_000 * rate, 4),
        "token_usd_per_million": rate,
        "server_offset_hours": account.get("server_offset_hours"),
        "mt5_connected": account.get("mt5_connected"),
        "mt5_message": account.get("mt5_message"),
        "gitignore_missing": env_io.gitignore_missing(),
    }


@router.get("/status")
def status(symbol: str = ""):
    if symbol and symbol not in state.SYMBOL_SPECS:
        raise HTTPException(404, "Simbol tidak dikenal")
    return state.build_status(symbol)


@router.get("/events")
def list_events(
    agent: str = "",
    symbol: str = "",
    level: str = "",
    text: str = "",
    since: str = "",
    until: str = "",
    limit: int = Query(100, ge=1, le=500),
):
    return {"events": events.query_events(agent, symbol, level, text, limit, since, until)}


@router.websocket("/ws/events")
async def ws_events(
    ws: WebSocket,
    agent: str = "",
    symbol: str = "",
    level: str = "",
):
    from dashboard_api.security import host_ok
    if not host_ok(ws.headers.get("host", "")):
        await ws.close(code=1008)
        return
    await ws.accept()
    queue = events.subscribe()
    try:
        while True:
            event = await queue.get()
            if agent and event.get("agent") != agent:
                continue
            if symbol and event.get("symbol") != symbol:
                continue
            if level and event.get("level") != level:
                continue
            await ws.send_json(event)
    except WebSocketDisconnect:
        pass
    finally:
        events.unsubscribe(queue)


@router.get("/symbols")
def get_symbols():
    status_doc = state.build_status()
    return {"symbols": status_doc["symbols"], "correlation": state.correlation_matrix()}


@router.put("/symbols/{name}")
def put_symbol(name: str, body: SymbolBody):
    if name not in state.SYMBOL_SPECS:
        raise HTTPException(404, "Simbol tidak dikenal")
    state.write_symbol_enabled(name, body.enabled)
    return {"ok": True, "name": name, "enabled": body.enabled}


@router.get("/risk/state")
def risk_state():
    return state.risk_snapshot()


@router.get("/risk/decisions")
def risk_decisions(limit: int = Query(40, ge=1, le=200)):
    return {"decisions": state.risk_decisions(limit)}


@router.get("/paper/positions")
def paper_positions():
    return {"positions": state.read_account().get("positions", [])}


@router.get("/paper/journal")
def paper_journal():
    return state.paper_stats()


@router.get("/paper/equity")
def paper_equity():
    stats = state.paper_stats()
    return {"equity_curve": stats["equity_curve"], "disclaimer": stats["disclaimer"]}


@router.get("/keys")
def get_keys():
    return {"slots": env_io.public_slots()}


@router.put("/keys/{slot}")
def put_key(slot: str, body: KeyBody):
    try:
        env_io.write_slot(slot, body.value.strip())
    except KeyError:
        raise HTTPException(404, "Slot tidak dikenal")
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    return {"ok": True, "slot": slot, "filled": True}


@router.post("/keys/{slot}/test")
async def test_key(slot: str):
    if slot not in env_io.SLOTS:
        raise HTTPException(404, "Slot tidak dikenal")
    return await grok_client.test_slot(slot)


@router.get("/agents")
def get_agents():
    return {"agents": agents.list_agents(), "variables": agents.VARIABLES}


@router.get("/agents/status")
def agents_status():
    from dashboard_api.services.agentroom import state as room_state
    return room_state()


@router.get("/agents/{name}")
def get_agent(name: str):
    try:
        return agents.read_agent(name)
    except KeyError:
        raise HTTPException(404, "Agent tidak dikenal")


@router.put("/agents/{name}")
def put_agent(name: str, body: AgentBody):
    try:
        return agents.save_agent(name, body.model_dump(), body.note)
    except PermissionError as exc:
        raise HTTPException(403, str(exc))
    except KeyError:
        raise HTTPException(404, "Agent tidak dikenal")
    except ValueError as exc:
        raise HTTPException(422, str(exc))


@router.get("/agents/{name}/versions")
def agent_versions(name: str):
    doc = get_agent(name)
    return {"versions": doc.get("versions", [])}


@router.get("/agents/{name}/versions/{number}")
def agent_version(name: str, number: int):
    try:
        return agents.version_detail(name, number)
    except KeyError:
        raise HTTPException(404, "Versi tidak ada")
    except PermissionError as exc:
        raise HTTPException(403, str(exc))


@router.post("/agents/{name}/rollback")
def agent_rollback(name: str, body: RollbackBody):
    try:
        return agents.rollback(name, body.version)
    except PermissionError as exc:
        raise HTTPException(403, str(exc))
    except KeyError:
        raise HTTPException(404, "Versi tidak ada")


@router.get("/agents/{name}/presets/{preset}")
def agent_preset(name: str, preset: str):
    try:
        return {"text": agents.preset_text(name, preset)}
    except KeyError:
        raise HTTPException(404, "Preset tidak ada")


@router.post("/agents/{name}/test")
async def agent_test(name: str):
    try:
        doc = agents.read_agent(name)
    except KeyError:
        raise HTTPException(404, "Agent tidak dikenal")
    if doc.get("locked"):
        raise HTTPException(403, doc.get("reason"))
    if not doc.get("model"):
        raise HTTPException(422, "Isi nama model dari dokumentasi xAI dulu")
    return await grok_client.test_prompt(
        doc["model"],
        float(doc["temperature"]),
        int(doc["max_tokens"]),
        int(doc["timeout_sec"]),
        doc["system_prompt"],
        doc["output_schema"],
    )


@router.get("/config")
def get_config():
    return config_store.public_view()


@router.put("/config")
def put_config(body: ConfigBody):
    result = config_store.save_config(body.model_dump(), body.confirm)
    if result.get("errors"):
        raise HTTPException(422, {"errors": result["errors"], "diff": result.get("diff", [])})
    return result


@router.get("/audit")
def get_audit(limit: int = Query(200, ge=1, le=500)):
    return {"rows": events.read_audit(limit)}


@router.get("/settings")
def get_settings():
    return state.read_settings()


@router.put("/settings")
def put_settings(body: SettingsBody):
    if body.theme not in {"dark", "light"}:
        raise HTTPException(422, "Tema tidak dikenal")
    if body.timezone not in state.TIMEZONES:
        raise HTTPException(422, "Zona waktu tidak dikenal")
    if body.language not in {"id", "en"}:
        raise HTTPException(422, "Bahasa tidak dikenal")
    if body.calendar_provider not in {"csv", "http"}:
        raise HTTPException(422, "Penyedia kalender tidak dikenal")
    return state.write_settings(body.model_dump())


@router.post("/security/fix-gitignore")
def fix_gitignore():
    added = env_io.ensure_gitignore_lines()
    return {"added": added, "missing": env_io.gitignore_missing()}
