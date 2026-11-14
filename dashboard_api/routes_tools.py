"""Rute baru. Semua method butuh token, termasuk GET."""
from fastapi import APIRouter, Depends, Header, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from dashboard_api.security import TOKEN
from dashboard_api.services import connections, costs, decisions, knowledge, machines, promotion, research
from dashboard_api.services.lab import discover, get_run, list_runs, save_history_csv, start_run
from dashboard_api.services.state import SYMBOL_SPECS, read_account


def require_token(x_dashboard_token: str = Header(default="")):
    if x_dashboard_token != TOKEN:
        raise HTTPException(401, "Token sesi tidak valid")


router = APIRouter(prefix="/api", dependencies=[Depends(require_token)])


class IngestBody(BaseModel):
    kind: str
    value: str = Field(min_length=4, max_length=20000)


class CardVerdict(BaseModel):
    verdict: str
    note: str = ""


class LabRunBody(BaseModel):
    symbol: str
    timeframe: str
    strategy: str = "reference_atr_breakout"
    date_from: str = ""
    date_to: str = ""
    params: dict = Field(default_factory=dict)


class HistoryBody(BaseModel):
    symbol: str
    timeframe: str
    csv: str = Field(min_length=20, max_length=5_000_000)


@router.get("/connections")
def get_connections():
    return connections.all_cards()


@router.post("/connections/{cid}/check")
async def post_connection(cid: str):
    try:
        return await connections.check_one(cid)
    except KeyError:
        raise HTTPException(404, "Koneksi tidak dikenal")


@router.get("/costs")
def get_costs():
    return costs.summary()


@router.get("/machines")
def get_machines():
    return machines.snapshot()


@router.get("/lab/strategies")
def lab_strategies():
    return {"strategies": discover()}


@router.get("/lab/runs")
def lab_runs():
    return {"runs": list_runs()}


@router.get("/lab/runs/{run_id}")
def lab_run(run_id: str):
    if not run_id.isalnum():
        raise HTTPException(404, "Run tidak ada")
    try:
        return get_run(run_id)
    except KeyError:
        raise HTTPException(404, "Run tidak ada")


@router.post("/lab/runs")
def lab_start(body: LabRunBody):
    if body.symbol not in SYMBOL_SPECS:
        raise HTTPException(404, "Simbol tidak dikenal")
    if body.timeframe not in {"M1", "M5", "M15"}:
        raise HTTPException(422, "Timeframe tidak dikenal")
    account = read_account()
    profile = dict(account["profile"])
    profile["equity"] = account["virtual_capital"]
    try:
        return start_run(body.symbol, body.timeframe, body.params, SYMBOL_SPECS[body.symbol], profile, body.strategy, body.date_from, body.date_to)
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc))
    except KeyError:
        raise HTTPException(404, "Strategi tidak dikenal")


@router.post("/lab/history")
def lab_history(body: HistoryBody):
    try:
        return save_history_csv(body.symbol, body.timeframe, body.csv.encode("utf-8"))
    except ValueError as exc:
        raise HTTPException(422, str(exc))


@router.post("/research/ingest")
def research_ingest(body: IngestBody):
    try:
        return research.ingest(body.kind, body.value)
    except ValueError as exc:
        raise HTTPException(422, str(exc))


@router.get("/research/items")
def research_items():
    return {"items": research.items(), "source": "real"}


@router.get("/research/clusters")
def research_clusters():
    return research.clusters()


@router.get("/knowledge/cards")
def knowledge_cards():
    return {"cards": knowledge.cards()}


@router.post("/knowledge/cards/{card_id}/verdict")
def knowledge_verdict(card_id: str, body: CardVerdict):
    if not card_id.replace("_", "").isalnum():
        raise HTTPException(404, "Kartu tidak ada")
    try:
        return knowledge.verdict(card_id, body.verdict, body.note)
    except KeyError:
        raise HTTPException(404, "Kartu tidak ada")
    except ValueError as exc:
        raise HTTPException(422, str(exc))


@router.get("/knowledge/review")
def knowledge_review():
    return {"cards": knowledge.review()}


@router.get("/agentroom/state")
def agentroom_state():
    from dashboard_api.services.agentroom import state
    return state()


@router.get("/decisions")
def decision_list(symbol: str = "", strategy: str = "", outcome: str = "", since: str = "", until: str = "", limit: int = Query(50, ge=1, le=200)):
    return {"decisions": decisions.query(symbol, strategy, outcome, since, until, limit=limit)}


@router.get("/decisions/{decision_id}")
def decision_one(decision_id: str):
    try:
        return decisions.get_one(decision_id)
    except KeyError:
        raise HTTPException(404, "Keputusan tidak ada")


@router.get("/promotion")
def promotion_ladder():
    return promotion.ladder()


@router.post("/connections/telegram/test")
def telegram_test():
    from dashboard_api.services.connections import send_telegram_test
    return send_telegram_test()


@router.websocket("/ws/handoff")
async def ws_handoff(ws: WebSocket, token: str = ""):
    if token != TOKEN:
        await ws.close(code=1008)
        return
    await ws.accept()
    import asyncio
    from dashboard_api.services import events
    seen = set()
    try:
        while True:
            for event in events.query_events(limit=40):
                if event.get("type") not in {"handoff", "signal"}:
                    continue
                key = f"{event.get('ts')}|{event.get('agent')}|{event.get('summary')}"
                if key in seen:
                    continue
                seen.add(key)
                await ws.send_json(event)
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        return


@router.websocket("/ws/machine")
async def ws_machine(ws: WebSocket, token: str = ""):
    if token != TOKEN:
        await ws.close(code=1008)
        return
    await ws.accept()
    try:
        while True:
            await ws.send_json(machines.snapshot())
            await __import__("asyncio").sleep(2)
    except WebSocketDisconnect:
        return
