"""The Night Market's service — one process, one port.

    /                the page (site/out, built once by valley.sh)
    /ws              the line: PCM up, PCM down, json captions and events
    /api/progress    which lanterns are lit — read from your code + the last call
    /api/code        read / write one symbol of one file (the in-page editor)
    /api/env         the AGENT_ENGINE line in .env (chapter 5)
    /workbench       adk web, mounted here: same stage/ folder, same stage.db

Every 📞 Call re-imports `stage.*` and builds a fresh Runner, so an edit lands
on the next call and nothing is ever restarted. `.env` is re-read on every call
too: naming the tower is a line in a file, not a restart.

    uvicorn stage.service:app --port 3450
"""

from __future__ import annotations

import contextlib
import importlib
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import forge  # noqa: F401,E402 — settles Vertex-vs-key for every surface
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect  # noqa: E402
from fastapi.responses import HTMLResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from google.adk.memory.base_memory_service import BaseMemoryService  # noqa: E402
from google.adk.sessions.sqlite_session_service import SqliteSessionService  # noqa: E402

from stage import codefile, memory, progress  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")
logging.getLogger("google_adk").setLevel(logging.WARNING)
log = logging.getLogger("nightmarket")
ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site" / "out"
DB = str(ROOT / "stage.db")
APP = "stage"
USER = "user"           # every visitor shares one name — self-study: make it come from the page
ENV_FILE = ROOT / ".env"

_sessions = SqliteSessionService(DB)
_memory: BaseMemoryService = memory.tower_service("")
_memory_engine = ""
_counters: dict[str, Any] = {"last_call": {}, "calls_filed": 0, "facts_recalled": 0}


def _refresh_memory() -> None:
    """Swap the memory service when `.env` starts (or stops) naming a tower."""
    global _memory, _memory_engine
    engine = memory.engine_named_in_env()
    if engine != _memory_engine:
        _memory = memory.tower_service(engine)
        _memory_engine = engine


def _reload():
    """The learner's code, as it is on disk right now — see progress.fresh."""
    return progress.fresh("stage.wire")


# ── the workbench: adk web, mounted ──────────────────────────────────────────
_workbench_server = None      # the ADK server object, kept so a save can evict its caches


def build_workbench() -> FastAPI:
    """adk web as a sub-application. Not with its own file watcher: that runs on
    a thread of its own and evicts `stage.*` from sys.modules whenever a file
    changes, racing this process's own imports. A save evicts the workbench's
    caches here instead, on the request that made the save."""
    from google.adk.cli import fast_api as adk_fast_api

    try:
        from google.adk.cli import dev_server as _home
        base = _home.DevServer
    except (ImportError, AttributeError):
        _home = adk_fast_api
        base = getattr(adk_fast_api, "ApiServer", None) or adk_fast_api.DevServer
    name = base.__name__

    class _Capturing(base):  # type: ignore[misc, valid-type]
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            global _workbench_server
            _workbench_server = self

    setattr(_home, name, _Capturing)
    return adk_fast_api.get_fast_api_app(
        agents_dir=str(ROOT), session_service_uri=f"sqlite:///{DB}",
        allow_origins=["*"], web=True, url_prefix="/workbench", reload_agents=False)


async def _workbench_forget() -> None:
    """After a save: the workbench's next run imports the file as it is now."""
    srv = _workbench_server
    if srv is None:
        return
    runner = getattr(srv, "runner_dict", {}).pop(APP, None)
    if runner is not None:
        with contextlib.suppress(Exception):
            from google.adk.cli.utils import cleanup
            await cleanup.close_runners([runner])
    with contextlib.suppress(Exception):
        srv.agent_loader.remove_agent_from_cache(APP)


workbench = build_workbench()


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # Starlette does not run a mounted app's lifespan; run the workbench's so
    # its own startup and shutdown hooks fire.
    async with workbench.router.lifespan_context(workbench):
        yield


app = FastAPI(title="Agent 101 · W5 The Night Market", lifespan=lifespan)


@app.middleware("http")
async def _no_cache_api(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api"):
        response.headers["Cache-Control"] = "no-store"
    return response


# ── plain reads ──────────────────────────────────────────────────────────────
async def _workbench_calls() -> int:
    """Calls made from the workbench: sessions in stage.db this page did not
    open (its own are `call-…`) that hold at least one transcription."""
    listed = await _sessions.list_sessions(app_name=APP, user_id=USER)
    n = 0
    for s in listed.sessions:
        if s.id.startswith("call-"):
            continue
        full = await _sessions.get_session(app_name=APP, user_id=USER, session_id=s.id)
        if full and any(e.input_transcription or e.output_transcription for e in full.events):
            n += 1
    return n


async def _probe() -> dict:
    _refresh_memory()
    c = dict(_counters)
    c["workbench_calls"] = await _workbench_calls()
    c["store"] = type(_memory).__name__
    return progress.read(c)


@app.get("/api/health")
async def health() -> dict:
    return {"ok": True, "store": type(_memory).__name__}


@app.get("/api/progress")
async def get_progress() -> dict:
    return await _probe()


# ── the editor ───────────────────────────────────────────────────────────────
@app.get("/api/code")
async def read_code(path: str, symbol: str | None = None) -> dict:
    try:
        return codefile.read(path, symbol)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.post("/api/code")
async def write_code(req: Request) -> dict:
    body = await req.json()
    try:
        out = codefile.write(body["path"], body["content"], body.get("symbol"))
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    if out.get("validation", {}).get("valid"):
        await _workbench_forget()
    return out


@app.get("/api/env")
async def read_env() -> dict:
    return {"AGENT_ENGINE": memory.engine_named_in_env(), "store": type(_memory).__name__}


def _set_engine(value: str) -> None:
    """The one line chapter 5 adds. Written into .env; picked up on the next call."""
    text = ENV_FILE.read_text() if ENV_FILE.exists() else ""
    m = re.search(r"^(#?)\s*AGENT_ENGINE=(.*)$", text, flags=re.M)
    if value:
        line = f"AGENT_ENGINE={value}"
    else:
        # un-naming keeps the old value behind a "# ", so it can be named again
        old = m.group(2).strip() if m else ""
        line = f"# AGENT_ENGINE={old}" if old and old != "local" else "# AGENT_ENGINE="
    if m:
        text = text[:m.start()] + line + text[m.end():]
    else:
        text = text.rstrip("\n") + f"\n\n# the tower — chapter 5\n{line}\n"
    ENV_FILE.write_text(text)
    _refresh_memory()


@app.post("/api/env")
async def write_env(req: Request) -> dict:
    body = await req.json()
    _set_engine(str(body.get("AGENT_ENGINE", "")).strip())
    return await read_env()


# ── the tower: three buttons ─────────────────────────────────────────────────
_build: dict[str, Any] = {"state": "idle", "log": ""}


def _week4_engine() -> str:
    """Week four's AGENT_ENGINE, if the Archive is checked out on this machine."""
    for p in (Path.home() / "agent-valley-archive" / ".env",
              Path.home() / "Documents" / "agent-valley-archive" / ".env"):
        if p.exists():
            m = re.search(r"^\s*AGENT_ENGINE=(projects/\S+)", p.read_text(), flags=re.M)
            if m:
                return m.group(1).strip()
    return ""


async def _build_tower() -> None:
    """scripts/make_tower.py, in the background; the page follows the log."""
    import asyncio

    _build.update(state="building", log="")
    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-u", str(ROOT / "scripts" / "make_tower.py"), cwd=str(ROOT),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
        assert proc.stdout is not None
        async for raw in proc.stdout:
            line = raw.decode(errors="replace")
            if "Warning" in line or "warnings.warn" in line:
                continue
            _build["log"] += line
        code = await proc.wait()
        _build["state"] = "done" if code == 0 and memory.engine_named_in_env() else "error"
    except Exception as exc:                                # noqa: BLE001
        _build["log"] += f"\n{type(exc).__name__}: {exc}"
        _build["state"] = "error"
    _refresh_memory()


async def _tower() -> dict:
    _refresh_memory()
    return {"engine": memory.engine_named_in_env(), "store": type(_memory).__name__,
            "week4": _week4_engine(), "build": dict(_build)}


@app.get("/api/tower")
async def get_tower() -> dict:
    return await _tower()


@app.post("/api/tower")
async def post_tower(req: Request) -> dict:
    import asyncio

    body = await req.json()
    action, value = body.get("action"), str(body.get("value") or "").strip()
    if action == "week4":
        _set_engine(_week4_engine())
    elif action == "local":
        _set_engine("local")
    elif action == "clear":
        _set_engine("")
    elif action == "paste" and value.startswith("projects/"):
        _set_engine(value)
    elif action == "build" and _build["state"] != "building":
        asyncio.create_task(_build_tower())
    return await _tower()


# ── the line ─────────────────────────────────────────────────────────────────
class _CountingSocket:
    """The websocket, counting the one message chapter 3 is about."""

    def __init__(self, ws: WebSocket) -> None:
        self._ws = ws
        self.interrupts = 0

    async def send_json(self, data: dict) -> None:
        if data.get("type") == "interrupted":
            self.interrupts += 1
        await self._ws.send_json(data)

    def __getattr__(self, name):
        return getattr(self._ws, name)


@app.websocket("/ws")
async def line(ws: WebSocket, sid: str = "call-1", user: str = USER):
    await ws.accept()
    _refresh_memory()
    sock = _CountingSocket(ws)
    clocks: dict[str, Any] = {}
    try:
        wire = _reload()
        clocks = await wire.open_line(sock, _sessions, _memory, user, sid)
    except WebSocketDisconnect:
        pass
    except Exception as exc:                                # noqa: BLE001
        log.exception("the line dropped")
        with contextlib.suppress(Exception):
            await ws.send_json({"type": "error", "message": f"{type(exc).__name__}: {exc}"[:300]})
    finally:
        clocks = {k: v for k, v in clocks.items() if not k.startswith("_")}
        clocks["interrupts"] = sock.interrupts
        clocks["store"] = type(_memory).__name__
        _counters["last_call"] = clocks
        # only the tower counts: the in-process store also files and recalls,
        # and forgets with the process — that is chapter 5's "before"
        if _memory_engine and clocks.get("filed"):
            _counters["calls_filed"] += 1
        if _memory_engine and clocks.get("recalled"):
            _counters["facts_recalled"] += clocks["recalled"]
        with contextlib.suppress(Exception):
            await ws.send_json({"type": "progress", **(await _probe())})
        with contextlib.suppress(Exception):
            await ws.close()


# ── the page and the workbench ───────────────────────────────────────────────
@app.get("/workbench/dev-ui/assets/config/runtime-config.json", include_in_schema=False)
async def runtime_config(request: Request):
    """The dev UI reads `backendUrl` from this file and builds its live
    websocket as `ws://<backendUrl>/run_live`. With the relative prefix ADK
    writes ("/workbench") that becomes `ws://workbench/run_live` — a host that
    does not exist, and a mic button that silently does nothing. Give it the
    absolute origin the page was served from, proxies included."""
    from fastapi.responses import JSONResponse

    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.headers.get("host", "localhost:3450"))
    return JSONResponse({"backendUrl": f"{proto}://{host}/workbench", "telemetry": False},
                        headers={"Cache-Control": "no-store"})


app.mount("/workbench", workbench)

if (SITE / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(SITE), html=True), name="site")
else:
    @app.get("/{path:path}", response_class=HTMLResponse, include_in_schema=False)
    async def _no_site(path: str) -> str:
        return ("<pre style='font:14px/1.6 monospace;padding:2rem'>The page is not built yet.\n\n"
                "    bash valley.sh\n\nbuilds site/ once and starts this server.</pre>")
