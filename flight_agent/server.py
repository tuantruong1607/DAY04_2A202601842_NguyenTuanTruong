"""FastAPI backend for the React frontend.

Thin HTTP layer over the existing graph agent (agent.py) and tools
(tools.TOOL_FUNCTIONS) — no new business logic lives here. Two kinds of
endpoints:

- /api/chat            conversational access to the graph agent
- /api/tools/{name}     direct passthrough to any of the 10 tools, for
                        structured UI panels (flight tracking, airport
                        boards, watches) that shouldn't have to go through
                        an LLM round trip just to call one tool.

Per TOOL-SETUP.md's UI checklist (§10.A.4: "hiển thị request/response, từng
round với tool name + args + result/error, version/artifact, và lưu
transcript"): /api/chat also tags each turn with the current artifact
version (see versioning.py) and appends it to a per-session transcript file
under transcripts/, mirroring what chat.py already does for the CLI.
"""
from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path
from typing import Any

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
from env_loader import load_env  # noqa: E402

load_env(ROOT)

from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from pydantic import BaseModel  # noqa: E402

import store  # noqa: E402
from agent import load_system_prompt, run_turn  # noqa: E402
from check_watches import check_price_watch, check_status_watch  # noqa: E402
from providers import make_provider  # noqa: E402
from tools import TOOL_FUNCTIONS  # noqa: E402
from tools.schemas import TOOL_SCHEMAS  # noqa: E402
from versioning import artifact_version_dict, current_artifact_version

app = FastAPI(title="Flight Search & Tracking Agent API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # local dev tool, single user — fine to leave open
    allow_methods=["*"],
    allow_headers=["*"],
)

SYSTEM_PROMPT = load_system_prompt()
SESSIONS: dict[str, list[dict[str, Any]]] = {}
TRANSCRIPTS_DIR = ROOT / "transcripts"
_provider_cache: Any = None


def get_provider() -> Any:
    global _provider_cache
    if _provider_cache is None:
        _provider_cache = make_provider()
    return _provider_cache


def _transcript_path(session_id: str) -> Path:
    return TRANSCRIPTS_DIR / f"web_{session_id}.transcript.json"


def _append_transcript(session_id: str, turn_record: dict[str, Any]) -> None:
    path = _transcript_path(session_id)
    if path.exists():
        try:
            transcript = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            transcript = {"session_id": session_id, "created_at": store.now_iso(), "turns": []}
    else:
        transcript = {"session_id": session_id, "created_at": store.now_iso(), "turns": []}
    transcript["turns"].append(turn_record)
    transcript["updated_at"] = store.now_iso()
    TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(transcript, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"ok": True}


@app.get("/api/version")
def version() -> dict[str, Any]:
    return artifact_version_dict(current_artifact_version())


@app.get("/api/tools")
def list_tools() -> list[dict[str, Any]]:
    return TOOL_SCHEMAS


# --------------------------------------------------------------------- chat
class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str


class ChatResponse(BaseModel):
    session_id: str
    assistant_text: str
    status: str
    tool_events: list[dict[str, Any]]
    graph_trace: list[str]
    rounds: list[dict[str, Any]]
    artifact_version: str


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    session_id = req.session_id or uuid.uuid4().hex[:12]
    history = SESSIONS.get(session_id) or [{"role": "system", "content": SYSTEM_PROMPT}]
    history.append({"role": "user", "content": req.message})

    tool_events: list[dict[str, Any]] = []
    started_at = store.now_iso()
    try:
        result = run_turn(provider=get_provider(), messages=history, on_tool_call=tool_events.append)
    except Exception as exc:
        raise HTTPException(502, f"{type(exc).__name__}: {exc}") from exc

    SESSIONS[session_id] = result["messages"]
    version = artifact_version_dict(current_artifact_version())

    _append_transcript(session_id, {
        "started_at": started_at,
        "ended_at": store.now_iso(),
        "artifact_version": version,
        "user": req.message,
        "status": result["status"],
        "assistant_text": result["assistant_text"],
        "rounds": result["rounds"],
        "graph_trace": result["graph_trace"],
    })

    return ChatResponse(
        session_id=session_id,
        assistant_text=result["assistant_text"],
        status=result["status"],
        tool_events=tool_events,
        graph_trace=result["graph_trace"],
        rounds=result["rounds"],
        artifact_version=version["artifact_version"],
    )


@app.delete("/api/chat/{session_id}")
def reset_chat(session_id: str) -> dict[str, Any]:
    SESSIONS.pop(session_id, None)
    return {"ok": True}


# ------------------------------------------------------------- tool passthrough
class ToolRequest(BaseModel):
    args: dict[str, Any] = {}


@app.post("/api/tools/{tool_name}")
def call_tool(tool_name: str, req: ToolRequest) -> Any:
    func = TOOL_FUNCTIONS.get(tool_name)
    if not func:
        raise HTTPException(404, f"Unknown tool: {tool_name}")
    try:
        return func(**req.args)
    except TypeError as exc:
        raise HTTPException(400, str(exc)) from exc


# --------------------------------------------------------------------- watches
@app.get("/api/watches")
def list_watches(active_only: bool = True) -> list[dict[str, Any]]:
    return store.list_watches(active_only=active_only)


class CheckWatchesRequest(BaseModel):
    watch_id: str | None = None


@app.post("/api/watches/check")
def check_watches(req: CheckWatchesRequest) -> dict[str, Any]:
    watches = store.list_watches(active_only=True)
    if req.watch_id:
        watches = [w for w in watches if w["id"] == req.watch_id]
    alerts: list[str] = []
    for watch in watches:
        checker = check_price_watch if watch.get("type") == "price" else check_status_watch
        alerts.extend(checker(watch))
    return {"checked": len(watches), "alerts": alerts}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", host="127.0.0.1", port=8787, reload=True)
