from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from chat import now_iso, run_model_tool_loop, write_transcript
from env_loader import load_lab_env
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools
from versioning import artifact_version_dict, build_artifact_version


VERSION = "v5"
SCENARIOS = [
    "Bernardo Silva đã ký hợp đồng với câu lạc bộ nào?",
    "Cho tôi các tin mới về Liverpool hôm nay.",
    "Tình trạng chấn thương mới nhất của Rodri hiện ra sao?",
]


def main() -> None:
    load_lab_env(ROOT)
    prompt_path = ROOT / "artifacts" / "system_prompt.md"
    tools_path = ROOT / "artifacts" / "tools.yaml"
    prompt = prompt_path.read_text(encoding="utf-8")
    declarations = to_openai_tools(load_tool_declarations(tools_path))
    provider = make_provider("openrouter")
    artifact = build_artifact_version(VERSION, prompt_path, tools_path)
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    output_path = ROOT / "transcripts" / f"{VERSION}_openrouter_freshness_{stamp}.transcript.json"
    transcript: dict[str, Any] = {
        "transcript_id": output_path.stem,
        **artifact_version_dict(artifact),
        "provider": "openrouter",
        "model": getattr(provider, "default_model", None),
        "created_at": now_iso(),
        "turns": [],
    }

    summary = []
    for index, user_text in enumerate(SCENARIOS, start=1):
        result = run_model_tool_loop(
            provider=provider,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_text},
            ],
            tools=declarations,
            model=None,
            max_tool_rounds=4,
        )
        turn = {
            "turn_index": index,
            "user": user_text,
            "started_at": now_iso(),
            **result,
            "ended_at": now_iso(),
        }
        transcript["turns"].append(turn)
        summary.append({
            "turn": index,
            "status": result.get("status"),
            "tool_calls": [
                {"name": event.get("tool"), "args": event.get("args")}
                for event in result.get("tool_events") or []
            ],
            "evidence_count": len(result.get("evidence") or []),
            "assistant_text": result.get("assistant_text"),
        })
        write_transcript(output_path, transcript)

    print(json.dumps({"transcript": str(output_path), "cases": summary}, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
