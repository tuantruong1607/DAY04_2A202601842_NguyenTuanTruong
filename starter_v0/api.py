from __future__ import annotations

import os
import re
import secrets
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from chat import now_iso, run_model_tool_loop, trim_history, write_transcript
from env_loader import load_lab_env
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools
from versioning import artifact_version_dict, build_artifact_version


ROOT = Path(__file__).parent
ARTIFACTS_DIR = ROOT / "artifacts"
RUNS_DIR = ROOT / "runs"
TRANSCRIPTS_DIR = ROOT / "transcripts"
SYSTEM_PROMPT_PATH = ARTIFACTS_DIR / "system_prompt.md"
TOOLS_PATH = ARTIFACTS_DIR / "tools.yaml"
VERSION = "v5"
PROVIDER = "openrouter"

load_lab_env(ROOT)

app = FastAPI(
    title="Football News VAR API",
    version=VERSION,
    description="HTTP bridge for the existing Python research-agent loop.",
)

default_origins = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001"
allowed_origins = [
    origin.strip()
    for origin in os.getenv("FOOTBALL_UI_ORIGINS", default_origins).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    session_id: str | None = None
    model: str | None = None
    history_window: int = Field(default=5, ge=1, le=10)
    max_tool_rounds: int = Field(default=4, ge=2, le=6)


class SessionState:
    def __init__(self, session_id: str) -> None:
        artifact = build_artifact_version(VERSION, SYSTEM_PROMPT_PATH, TOOLS_PATH)
        self.session_id = session_id
        self.history: list[dict[str, str]] = []
        self.transcript: dict[str, Any] = {
            "transcript_id": session_id,
            **artifact_version_dict(artifact),
            "provider": PROVIDER,
            "model": None,
            "system_prompt": str(SYSTEM_PROMPT_PATH.relative_to(ROOT)),
            "tools": str(TOOLS_PATH.relative_to(ROOT)),
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "turns": [],
            "frontend": "nextjs",
        }


sessions: dict[str, SessionState] = {}
sessions_lock = Lock()


def safe_session_id(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return cleaned[:120].strip("_")


def new_session_id() -> str:
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    return f"{VERSION}_{PROVIDER}_next_{stamp}_{secrets.token_hex(3)}"


def get_or_create_session(requested_id: str | None) -> SessionState:
    session_id = safe_session_id(requested_id or "") or new_session_id()
    with sessions_lock:
        state = sessions.get(session_id)
        if state is None:
            state = SessionState(session_id)
            sessions[session_id] = state
        return state


def latest_eval_summary(suite: str) -> dict[str, Any] | None:
    latest: tuple[float, dict[str, Any]] | None = None
    for path in RUNS_DIR.glob("*.json"):
        try:
            import json

            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if payload.get("suite") != suite:
            continue
        candidate = (path.stat().st_mtime, payload)
        if latest is None or candidate[0] > latest[0]:
            latest = candidate
    if latest is None:
        return None
    payload = latest[1]
    return {
        "run_id": payload.get("run_id"),
        "artifact_version": payload.get("artifact_version"),
        "summary": payload.get("summary", {}),
    }


def public_meta() -> dict[str, Any]:
    artifact = build_artifact_version(VERSION, SYSTEM_PROMPT_PATH, TOOLS_PATH)
    provider = make_provider(PROVIDER)
    return {
        "name": "Football News VAR",
        "version": VERSION,
        "provider": PROVIDER,
        "model": getattr(provider, "default_model", None),
        "artifact": artifact_version_dict(artifact),
        "evals": {
            "base": latest_eval_summary("base"),
            "group": latest_eval_summary("group"),
        },
    }


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "football-news-var"}


@app.get("/api/meta")
def meta() -> dict[str, Any]:
    return public_meta()


@app.post("/api/sessions")
def create_session() -> dict[str, Any]:
    state = get_or_create_session(None)
    return {"session_id": state.session_id, "meta": public_meta()}


@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: str) -> dict[str, Any]:
    safe_id = safe_session_id(session_id)
    if not safe_id:
        raise HTTPException(status_code=400, detail="Invalid session ID")
    with sessions_lock:
        existed = sessions.pop(safe_id, None) is not None
    return {"deleted": existed, "session_id": safe_id}


@app.post("/api/chat")
def chat(request: ChatRequest) -> dict[str, Any]:
    user_text = request.message.strip()
    if not user_text:
        raise HTTPException(status_code=422, detail="Message cannot be empty")

    state = get_or_create_session(request.session_id)
    prompt = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    openai_tools = to_openai_tools(load_tool_declarations(TOOLS_PATH))
    provider = make_provider(PROVIDER)
    selected_model = request.model or getattr(provider, "default_model", None)
    messages = [
        {"role": "system", "content": prompt},
        *trim_history(state.history, request.history_window),
        {"role": "user", "content": user_text},
    ]
    turn: dict[str, Any] = {
        "turn_index": len(state.transcript["turns"]) + 1,
        "started_at": now_iso(),
        "user": user_text,
        "status": "started",
        "assistant_text": None,
        "rounds": [],
        "tool_events": [],
        "evidence": [],
    }

    try:
        result = run_model_tool_loop(
            provider=provider,
            messages=messages,
            tools=openai_tools,
            model=request.model,
            max_tool_rounds=request.max_tool_rounds,
        )
        turn.update(result)
        answer = str(result.get("assistant_text") or "Không có nội dung trả lời.")
        state.history.extend([
            {"role": "user", "content": user_text},
            {"role": "assistant", "content": answer},
        ])
    except Exception as exc:
        turn.update({
            "status": "provider_error",
            "error": f"{type(exc).__name__}: {exc}",
            "assistant_text": "Mình chưa thể hoàn tất lượt này. Hãy kiểm tra provider và thử lại.",
        })

    turn["ended_at"] = now_iso()
    state.transcript["model"] = selected_model
    state.transcript["history_window"] = request.history_window
    state.transcript["max_tool_rounds"] = request.max_tool_rounds
    state.transcript["turns"].append(turn)
    write_transcript(TRANSCRIPTS_DIR / f"{state.session_id}.transcript.json", state.transcript)

    return {
        "session_id": state.session_id,
        "turn": turn,
        "artifact": {
            key: state.transcript.get(key)
            for key in ("version", "artifact_version", "prompt_hash", "tools_hash")
        },
    }
