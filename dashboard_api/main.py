import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from dashboard_api import mock_feeder
from dashboard_api.paths import ENV_FILE, ensure_dirs

load_dotenv(ENV_FILE, override=False)
from dashboard_api.routes import router
from dashboard_api.routes_tools import router as tools_router
from dashboard_api.services.agent_registry import ensure_files
from dashboard_api.security import TOKEN, WRITE_METHODS, host_ok
from dashboard_api.services import events


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_dirs()
    ensure_files()
    events.set_loop(__import__("asyncio").get_running_loop())
    if os.environ.get("DASHBOARD_DISABLE_TAIL") != "1":
        events.start_background()
    if os.environ.get("DASHBOARD_MODE", "mock") == "mock":
        mock_feeder.start()
    yield
    mock_feeder.stop()
    events.stop_background()


app = FastAPI(title="Dashboard 5 Agent", docs_url="/api/docs", openapi_url="/api/openapi.json", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "OPTIONS"],
    allow_headers=["Content-Type", "X-Dashboard-Token"],
)
app.include_router(router)
app.include_router(tools_router)


@app.middleware("http")
async def guard(request: Request, call_next):
    if not host_ok(request.headers.get("host", "")):
        return JSONResponse({"detail": "Host ditolak"}, status_code=400)
    if request.method in WRITE_METHODS and request.url.path.startswith("/api/"):
        if request.headers.get("x-dashboard-token") != TOKEN:
            return JSONResponse({"detail": "Token sesi tidak valid"}, status_code=401)
    return await call_next(request)


@app.exception_handler(RequestValidationError)
async def hide_invalid_input(request: Request, exc: RequestValidationError):
    # Jangan kirim field `input` — bisa berisi API key.
    clean = [{"loc": list(err.get("loc", [])), "msg": err.get("msg", ""), "type": err.get("type", "")} for err in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": clean})
