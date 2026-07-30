from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from chat import now_iso, run_model_tool_loop, trim_history, write_transcript
from env_loader import load_lab_env
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools
from versioning import artifact_version_dict, build_artifact_version


ARTIFACTS_DIR = ROOT / "artifacts"
SYSTEM_PROMPT_PATH = ARTIFACTS_DIR / "system_prompt.md"
TOOLS_PATH = ARTIFACTS_DIR / "tools.yaml"
TRANSCRIPTS_DIR = ROOT / "transcripts"

load_lab_env(ROOT)


SCENARIOS = [
    "Kiểm tra tin chuyển nhượng này giúp tôi.",
    "Tin cần kiểm tra là Arsenal đang đàm phán mua một tiền đạo mới hôm nay.",
    "Tìm tin mới nhất về Liverpool hôm nay.",
    "Kiểm tra thông tin minh bạch của Facebook Page ID 20531316728.",
    "Đăng bản tin vừa tổng hợp lên Telegram giúp tôi.",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run repeatable Football News VAR demo scenarios.")
    parser.add_argument("--provider", default="openrouter", choices=["openrouter"])
    parser.add_argument("--version", default="v4")
    parser.add_argument("--model", default=None)
    parser.add_argument("--history-window", type=int, default=5)
    parser.add_argument("--max-tool-rounds", type=int, default=4)
    args = parser.parse_args()

    prompt = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    tools = to_openai_tools(load_tool_declarations(TOOLS_PATH))
    provider = make_provider(args.provider)
    selected_model = args.model or getattr(provider, "default_model", None)
    artifact = build_artifact_version(args.version, SYSTEM_PROMPT_PATH, TOOLS_PATH)

    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    transcript_id = f"{args.version}_{args.provider}_football_demo_{timestamp}"
    output_path = TRANSCRIPTS_DIR / f"{transcript_id}.transcript.json"
    transcript: dict[str, Any] = {
        "transcript_id": transcript_id,
        **artifact_version_dict(artifact),
        "provider": args.provider,
        "model": selected_model,
        "system_prompt": str(SYSTEM_PROMPT_PATH.relative_to(ROOT)),
        "tools": str(TOOLS_PATH.relative_to(ROOT)),
        "history_window": args.history_window,
        "max_tool_rounds": args.max_tool_rounds,
        "created_at": now_iso(),
        "turns": [],
    }

    history: list[dict[str, str]] = []
    for turn_index, user_text in enumerate(SCENARIOS, start=1):
        print(f"Running demo turn {turn_index}/{len(SCENARIOS)}", flush=True)
        turn: dict[str, Any] = {
            "turn_index": turn_index,
            "started_at": now_iso(),
            "user": user_text,
            "status": "started",
            "assistant_text": None,
            "rounds": [],
            "tool_events": [],
        }
        messages = [
            {"role": "system", "content": prompt},
            *trim_history(history, args.history_window),
            {"role": "user", "content": user_text},
        ]
        try:
            result = run_model_tool_loop(
                provider=provider,
                messages=messages,
                tools=tools,
                model=args.model,
                max_tool_rounds=args.max_tool_rounds,
            )
            turn.update(result)
            assistant_text = result.get("assistant_text") or ""
            history.extend([
                {"role": "user", "content": user_text},
                {"role": "assistant", "content": assistant_text},
            ])
        except Exception as exc:
            turn.update({
                "status": "provider_error",
                "error": f"{type(exc).__name__}: {exc}",
            })
        turn["ended_at"] = now_iso()
        transcript["turns"].append(turn)
        write_transcript(output_path, transcript)

    print(f"Saved transcript: {output_path}")


if __name__ == "__main__":
    main()
