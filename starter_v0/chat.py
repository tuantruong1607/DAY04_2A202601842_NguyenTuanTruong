from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from env_loader import load_lab_env
from providers import make_provider
from providers.base import ToolCall
from tools import TOOL_FUNCTIONS, load_tool_declarations, to_openai_tools
from tools._shared import fold_text
from versioning import artifact_version_dict, build_artifact_version


ROOT = Path(__file__).parent
ARTIFACTS_DIR = ROOT / "artifacts"
load_lab_env(ROOT)


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return slug.strip("_") or "run"


def json_text(value: Any, *, max_chars: int | None = None) -> str:
    text = json.dumps(value, ensure_ascii=False, indent=2, default=str)
    if max_chars is not None and len(text) > max_chars:
        return text[:max_chars] + "\n...<truncated>"
    return text


def trim_history(history: list[dict[str, str]], window: int) -> list[dict[str, str]]:
    if window <= 0:
        return []
    return history[-window * 2:]


def explicit_timeframe(user_text: str) -> str | None:
    """Return a user-stated relative window; never infer one from 'latest'."""
    folded = fold_text(user_text)
    markers = {
        "day": ("hom nay", "today", "last 24 hours", "24 gio", "trong ngay"),
        "week": ("tuan nay", "this week", "last 7 days", "7 ngay", "tuan qua"),
        "month": ("thang nay", "this month", "last 30 days", "30 ngay"),
        "year": ("nam nay", "this year"),
    }
    for timeframe, values in markers.items():
        if any(value in folded for value in values):
            return timeframe
    if re.search(r"\b20\d{2}\b", folded):
        return "year"
    return None


def normalize_runtime_tool_call(call: ToolCall, user_text: str) -> ToolCall:
    """Correct unsafe freshness defaults before a live lookup executes.

    Tool routing remains model-driven. This guard only prevents an unstated
    one-day window from hiding valid evidence and ensures the full intent is
    available to the relevance filter.
    """
    if call.name == "clarify":
        folded_request = fold_text(user_text)
        action_markers = ("gui", "dang", "post", "publish", "send", "telegram", "upload")
        if any(marker in folded_request for marker in action_markers):
            args = dict(call.args)
            args["response_type"] = "yes_no"
            return ToolCall(name=call.name, args=args)
        return call

    if call.name != "lookup":
        return call

    args = dict(call.args)
    stated_timeframe = explicit_timeframe(user_text)
    if stated_timeframe:
        args["timeframe"] = stated_timeframe
        args["strict_timeframe"] = True
    else:
        args["strict_timeframe"] = False
        current_timeframe = args.get("timeframe")
        if current_timeframe == "day":
            folded = fold_text(f"{user_text} {args.get('intent') or ''}")
            completed_transfer = any(marker in folded for marker in (
                "da ky", "da ki", "signed", "joined", "gia nhap", "clb nao", "club did",
            ))
            args["timeframe"] = "year" if completed_transfer else "week"

    if not str(args.get("intent") or "").strip():
        args["intent"] = user_text.strip()
    return ToolCall(name=call.name, args=args)


def latest_user_request(messages: list[dict[str, str]]) -> str:
    for message in reversed(messages):
        content = str(message.get("content") or "")
        if message.get("role") == "user" and not content.startswith("TOOL_RESULTS_JSON:"):
            return content
    return ""


def localize_confidence_label(text: str) -> str:
    """Guarantee Vietnamese confidence labels in researched answers."""
    replacements = {
        "High": "Cao",
        "Medium": "Trung bình",
        "Low": "Thấp",
    }
    for english, vietnamese in replacements.items():
        pattern = rf"(?im)(Mức tin cậy\s*(?:\n|:\s*))\s*{english}\b"
        text = re.sub(pattern, rf"\1{vietnamese}", text)
    return text


def execute_tool_call(call: ToolCall) -> dict[str, Any]:
    func = TOOL_FUNCTIONS.get(call.name)
    if not func:
        return {
            "tool": call.name,
            "args": call.args,
            "result": {"error": "unknown_tool", "message": f"No local implementation for {call.name}"},
        }
    try:
        result = func(**call.args)
    except Exception as exc:
        result = {"error": type(exc).__name__, "message": str(exc)}
    return {"tool": call.name, "args": call.args, "result": result}


def tool_usage_counts(events: list[dict[str, Any]]) -> list[tuple[str, int]]:
    """Return tool names and call counts in first-use order."""
    counts: dict[str, int] = {}
    for event in events:
        name = str(event.get("tool") or "").strip()
        if name:
            counts[name] = counts.get(name, 0) + 1
    return list(counts.items())


def evidence_items(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build a compact, deduplicated evidence index for UI and transcripts."""
    evidence: list[dict[str, Any]] = []
    seen: set[str] = set()
    for event in events:
        result = event.get("result", {})
        if not isinstance(result, dict):
            continue
        for item in result.get("items") or []:
            if not isinstance(item, dict):
                continue
            url = str(item.get("url") or "").strip()
            title = str(item.get("title") or url or event.get("tool") or "Nguồn dữ liệu").strip()
            identity = url.lower() or f"{event.get('tool')}:{title.lower()}"
            if identity in seen:
                continue
            seen.add(identity)
            evidence.append({
                "tool": event.get("tool"),
                "title": title,
                "url": url,
                "source": item.get("source") or "",
                "summary": str(item.get("summary") or "")[:900],
                "score": item.get("score"),
                "published_date": item.get("published_date") or item.get("date"),
                "modified_date": item.get("modified_date"),
                "retrieved_at": result.get("retrieved_at"),
                "backend": result.get("backend"),
            })
    return evidence


def tool_results_message(events: list[dict[str, Any]]) -> dict[str, str]:
    return {
        "role": "user",
        "content": (
            "TOOL_RESULTS_JSON:\n"
            f"{json_text(events, max_chars=24000)}\n\n"
            "PIPELINE_STAGE: VERIFY_AND_SYNTHESIZE\n"
            "Treat search items as candidate evidence, not facts. Check that each item actually matches the subject and intent. "
            "Use published_date/date to assess freshness. A low score, unrelated result, empty item list, or "
            "quality.status=no_relevant_results is inconclusive and must never be turned into a claim that an event did not happen. "
            "If quality.timeframe_broadened=true, distinguish older evidence from an update inside the requested window. "
            "If backend=tavily_x_index_fallback, state that the social evidence is indexed and may be delayed. "
            "Dùng duy nhất dữ liệu trong TOOL_RESULTS_JSON và hội thoại hiện tại. "
            "Kiểm tra tool error trước. Đối chiếu các nguồn độc lập khi có thể, ưu tiên nguồn chính thức "
            "và báo chí uy tín; social/profile metadata chỉ là bằng chứng hỗ trợ. Nếu một khoảng trống quan trọng "
            "có thể được giải quyết bằng tool khác, hãy gọi tool đó trước khi kết luận. Nếu bằng chứng đã đủ, "
            "trả lời tự nhiên bằng tiếng Việt: nêu kết luận trực tiếp, các điểm chính, điều đã kiểm chứng hoặc còn "
            "mâu thuẫn, mức tin cậy và danh sách nguồn dạng Markdown. Dịch ý từ nguồn nước ngoài sang tiếng Việt "
            "nhưng giữ nguyên tên riêng. Không tạo URL, ngày tháng, trích dẫn hoặc sự kiện không có trong dữ liệu. "
            "Nếu user chỉ yêu cầu câu trả lời ngắn, vẫn trả lời gọn nhưng phải giữ nguồn và mức tin cậy."
        ),
    }


def assistant_tool_message(response_text: str | None, calls: list[ToolCall]) -> dict[str, str]:
    call_summary = [{"name": call.name, "args": call.args} for call in calls]
    content = response_text or "I will call the selected tool(s)."
    return {
        "role": "assistant",
        "content": f"{content}\n\nTOOL_CALLS_JSON:\n{json_text(call_summary)}",
    }


def run_model_tool_loop(
    *,
    provider: Any,
    messages: list[dict[str, str]],
    tools: list[dict[str, Any]],
    model: str | None,
    max_tool_rounds: int,
    on_progress: Callable[[str, dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    working_messages = list(messages)
    user_request = latest_user_request(messages)
    rounds: list[dict[str, Any]] = []
    all_tool_events: list[dict[str, Any]] = []

    def emit(stage: str, **payload: Any) -> None:
        if on_progress:
            on_progress(stage, payload)

    for round_index in range(1, max_tool_rounds + 1):
        model_stage = "synthesis" if all_tool_events else "planning"
        emit(model_stage, round=round_index)
        response = provider.complete(working_messages, tools, model=model, temperature=0.0)
        raw_calls = response.tool_calls
        calls = [normalize_runtime_tool_call(call, user_request) for call in raw_calls]
        round_record: dict[str, Any] = {
            "round": round_index,
            "stage": model_stage,
            "assistant_text": response.text,
            "model_tool_calls": [{"name": call.name, "args": call.args} for call in raw_calls],
            "tool_calls": [{"name": call.name, "args": call.args} for call in calls],
            "tool_results": [],
        }

        if not calls:
            rounds.append(round_record)
            emit("complete", round=round_index, evidence_count=len(evidence_items(all_tool_events)))
            assistant_text = response.text or ""
            if all_tool_events:
                assistant_text = localize_confidence_label(assistant_text)
            return {
                "status": "answered",
                "assistant_text": assistant_text,
                "rounds": rounds,
                "tool_events": all_tool_events,
                "evidence": evidence_items(all_tool_events),
            }

        working_messages.append(assistant_tool_message(response.text, calls))
        non_clarification_events: list[dict[str, Any]] = []

        for call in calls:
            # Keep console logging ASCII-safe on Windows code pages. Tool args
            # remain Unicode in the transcript JSON.
            print(f"[tool] {call.name}({json.dumps(call.args, ensure_ascii=True, sort_keys=True)})")
            emit("tool_started", round=round_index, tool=call.name, args=call.args)
            event = execute_tool_call(call)
            round_record["tool_results"].append(event)
            all_tool_events.append(event)

            # Detect the clarification/pause tool by its output flag (rename-proof),
            # not by a hard-coded tool name.
            result = event.get("result", {})
            emit(
                "tool_finished",
                round=round_index,
                tool=call.name,
                ok=not (isinstance(result, dict) and result.get("error")),
                item_count=len(result.get("items") or []) if isinstance(result, dict) else 0,
            )
            if isinstance(result, dict) and result.get("awaiting_user"):
                question = result.get("question") or call.args.get("question") or "Bạn vui lòng bổ sung thông tin còn thiếu."
                rounds.append(round_record)
                emit("waiting_for_user", round=round_index, tool=call.name)
                return {
                    "status": "waiting_for_user",
                    "assistant_text": question,
                    "rounds": rounds,
                    "tool_events": all_tool_events,
                    "evidence": evidence_items(all_tool_events),
                }

            non_clarification_events.append(event)

        rounds.append(round_record)
        working_messages.append(tool_results_message(non_clarification_events))

    return {
        "status": "max_tool_rounds",
        "assistant_text": f"Đã dừng sau {max_tool_rounds} vòng tool. Vui lòng mở chi tiết phiên để kiểm tra.",
        "rounds": rounds,
        "tool_events": all_tool_events,
        "evidence": evidence_items(all_tool_events),
    }


def write_transcript(path: Path, transcript: dict[str, Any]) -> None:
    transcript["updated_at"] = now_iso()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(transcript, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Interactive Research Agent chat with transcript logging.")
    parser.add_argument("--provider", choices=["openrouter", "openai", "anthropic", "gemini"], required=True)
    parser.add_argument("--model", default=None)
    parser.add_argument("--version", required=True, help="Student-chosen artifact version label, e.g. v0, v1, v2.")
    parser.add_argument("--system-prompt", type=Path, default=ARTIFACTS_DIR / "system_prompt.md")
    parser.add_argument("--tools", type=Path, default=ARTIFACTS_DIR / "tools.yaml")
    parser.add_argument("--transcripts-dir", type=Path, default=ROOT / "transcripts")
    parser.add_argument("--history-window", type=int, default=5, help="Keep the last N user/assistant pairs in context.")
    parser.add_argument("--max-tool-rounds", type=int, default=4)
    args = parser.parse_args()

    system_prompt = args.system_prompt.read_text(encoding="utf-8")
    tool_declarations = load_tool_declarations(args.tools)
    openai_tools = to_openai_tools(tool_declarations)
    provider = make_provider(args.provider)
    selected_model = args.model or getattr(provider, "default_model", None)
    artifact_version = build_artifact_version(args.version, args.system_prompt, args.tools)

    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    transcript_id = "_".join([
        safe_slug(args.version),
        safe_slug(args.provider),
        timestamp,
    ])
    transcript_path = args.transcripts_dir / f"{transcript_id}.transcript.json"
    transcript: dict[str, Any] = {
        "transcript_id": transcript_id,
        **artifact_version_dict(artifact_version),
        "provider": args.provider,
        "model": selected_model,
        "system_prompt": str(args.system_prompt),
        "tools": str(args.tools),
        "history_window": args.history_window,
        "max_tool_rounds": args.max_tool_rounds,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "turns": [],
    }

    print(f"Research Agent chat. artifact_version={artifact_version.artifact_version}")
    print("Type /exit to stop.")

    history: list[dict[str, str]] = []
    turn_index = 0
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

        turn_index += 1
        messages = [
            {"role": "system", "content": system_prompt},
            *trim_history(history, args.history_window),
            {"role": "user", "content": user_text},
        ]

        turn_record: dict[str, Any] = {
            "turn_index": turn_index,
            "started_at": now_iso(),
            "user": user_text,
            "status": "started",
            "assistant_text": None,
            "rounds": [],
            "tool_events": [],
        }

        try:
            result = run_model_tool_loop(
                provider=provider,
                messages=messages,
                tools=openai_tools,
                model=args.model,
                max_tool_rounds=args.max_tool_rounds,
            )
            turn_record.update(result)
            assistant_text = result["assistant_text"]
            print(f"\nAgent> {assistant_text}")
            usage = tool_usage_counts(result.get("tool_events") or [])
            usage_text = ", ".join(
                f"{name} x{count}" if count > 1 else name
                for name, count in usage
            ) or "không sử dụng công cụ"
            print(f"Tools> {usage_text}")
            history.append({"role": "user", "content": user_text})
            history.append({"role": "assistant", "content": assistant_text})
        except Exception as exc:
            turn_record.update({
                "status": "provider_error",
                "error": f"{type(exc).__name__}: {str(exc)}",
            })
            print(f"\nERROR> {turn_record['error']}")
            print("Tools> không sử dụng công cụ")

        turn_record["ended_at"] = now_iso()
        transcript["turns"].append(turn_record)
        write_transcript(transcript_path, transcript)
        print(f"Transcript saved: {transcript_path}")

    write_transcript(transcript_path, transcript)
    print(f"Final transcript: {transcript_path}")


if __name__ == "__main__":
    main()
