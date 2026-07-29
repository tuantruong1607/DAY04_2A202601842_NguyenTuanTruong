from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Windows consoles often default to a non-UTF-8 codepage, which crashes on
# Vietnamese/accented output. Force UTF-8 stdout/stderr so chat responses
# never raise UnicodeEncodeError.
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from agent import load_system_prompt, run_turn
from env_loader import load_env

ROOT = Path(__file__).resolve().parent
load_env(ROOT)

from providers import make_provider  # noqa: E402  (after load_env so keys are present)


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def trim_history(history: list[dict[str, Any]], window: int) -> list[dict[str, Any]]:
    if window <= 0:
        return []
    return history[-window * 2:]


def print_tool_event(event: dict[str, Any]) -> None:
    result = event.get("result", {})
    status = "error" if isinstance(result, dict) and result.get("error") else "ok"
    print(f"  \U0001F527 {event['tool']}({json.dumps(event['args'], ensure_ascii=False)}) -> {status}")


def write_transcript(path: Path, transcript: dict[str, Any]) -> None:
    transcript["updated_at"] = now_iso()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(transcript, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Flight Search & Tracking Agent — interactive chat.")
    parser.add_argument("--provider", choices=["openai", "openrouter"], default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--max-tool-rounds", type=int, default=6)
    parser.add_argument("--history-window", type=int, default=6, help="Keep the last N user/assistant pairs in context.")
    args = parser.parse_args()

    provider = make_provider(args.provider)
    system_prompt = load_system_prompt()

    transcripts_dir = ROOT / "transcripts"
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    transcript_path = transcripts_dir / f"chat_{timestamp}.transcript.json"
    transcript: dict[str, Any] = {
        "provider": type(provider).__name__,
        "model": args.model or getattr(provider, "default_model", None),
        "created_at": now_iso(),
        "turns": [],
    }

    print("Flight Search & Tracking Agent. Type /exit to quit.")
    history: list[dict[str, Any]] = []

    while True:
        try:
            user_text = input("\nYou> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_text:
            continue
        if user_text in {"/exit", "/quit"}:
            break

        messages = [
            {"role": "system", "content": system_prompt},
            *trim_history(history, args.history_window),
            {"role": "user", "content": user_text},
        ]

        turn_record: dict[str, Any] = {"started_at": now_iso(), "user": user_text}
        try:
            result = run_turn(
                provider=provider,
                messages=messages,
                model=args.model,
                max_tool_rounds=args.max_tool_rounds,
                on_tool_call=print_tool_event,
            )
            assistant_text = result["assistant_text"]
            print(f"\nAgent> {assistant_text}")
            history.append({"role": "user", "content": user_text})
            history.append({"role": "assistant", "content": assistant_text})
            turn_record.update({
                "status": result["status"],
                "assistant_text": assistant_text,
                "rounds": result["rounds"],
                "graph_trace": result["graph_trace"],
            })
        except Exception as exc:
            error_text = f"{type(exc).__name__}: {exc}"
            print(f"\nERROR> {error_text}")
            turn_record.update({"status": "provider_error", "error": error_text})

        turn_record["ended_at"] = now_iso()
        transcript["turns"].append(turn_record)
        write_transcript(transcript_path, transcript)

    write_transcript(transcript_path, transcript)
    print(f"Transcript saved: {transcript_path}")


if __name__ == "__main__":
    main()
