"""Flight agent as an explicit graph (see graph.py), not a flat while-loop.

Nodes:
  plan            LLM decides: call tool(s), or answer directly.
  act             Executes whatever tool calls `plan` returned.
  auto_recommend  Deterministic rule (not an LLM decision): if `act` just
                  ran search_flight_prices and got >=2 offers, and nothing
                  has called compare_flight_offers yet this turn, force that
                  call. This guarantees CLAUDE.md §5's 3-pick recommendation
                  logic actually runs instead of depending on the model
                  remembering to call it (it doesn't always).
  respond         Finalizes the assistant's answer. Terminal node.

Edges:
  plan -> act            if plan returned tool calls and rounds remain
  plan -> respond         if plan returned a final answer, or rounds are used up
  act -> auto_recommend   always
  auto_recommend -> plan  always (loop back so the model can see the
                          comparison results, or just answer if nothing new
                          happened)

This keeps the exact same external behavior/contract as the previous flat
loop (see git history) but expresses control flow as named nodes with
conditional edges instead of one homogeneous `for` loop, and adds one real
branch (auto_recommend) that a flat loop can't express cleanly.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from graph import END, StateGraph
from providers.base import ToolCall
from tools import TOOL_FUNCTIONS
from tools.schemas import TOOL_SCHEMAS
from tools.time_tool import get_current_time

ROOT = Path(__file__).resolve().parent
SYSTEM_PROMPT_PATH = ROOT / "artifacts" / "system_prompt.md"

# Tool name -> arg fields that must be a code already returned by a prior
# search_airports call this conversation. Enforced in code (not just prompt
# wording) because the model sometimes skips search_airports and guesses a
# plausible-looking code instead — see _collect_verified_codes / execute_tool_call.
AIRPORT_CODE_FIELDS: dict[str, tuple[str, ...]] = {
    "search_flight_prices": ("origin", "destination"),
    "get_airport_arrivals": ("airport_code",),
    "get_airport_departures": ("airport_code",),
    "create_price_watch": ("origin", "destination"),
}


def load_system_prompt() -> str:
    return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")


def _time_grounding_message() -> dict[str, Any]:
    """A fresh, deterministic system reminder of the real current time.

    Injected at the start of every turn (see run_turn) so the model never
    has to guess "today" for relative dates like "ngay mai" / "tuan sau" —
    computed straight from the system clock via get_current_time, not from
    the LLM's own (often stale or wrong) sense of the date.
    """
    now = get_current_time()
    utc, vn = now["utc"], now["vietnam"]
    return {
        "role": "system",
        "content": (
            "[time grounding — authoritative, not a guess] "
            f"UTC now: {utc['iso']} ({utc['weekday']}). "
            f"Vietnam now (Asia/Ho_Chi_Minh, UTC+7): {vn['iso']} ({vn['weekday']}). "
            "Resolve any relative date/time the user mentions against Vietnam time "
            "unless they specify otherwise. Never invent or calculate today's date "
            "yourself; call get_current_time again mid-turn if you need it re-checked "
            "or need another timezone."
        ),
    }


def _collect_verified_codes(messages: list[dict[str, Any]]) -> set[str]:
    """IATA/ICAO codes returned by any search_airports result so far this
    conversation (scanned from tool-result messages already in history)."""
    codes: set[str] = set()
    for msg in messages:
        if msg.get("role") != "tool":
            continue
        try:
            payload = json.loads(msg.get("content") or "{}")
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(payload, dict) or payload.get("tool") != "search_airports":
            continue
        for item in payload.get("items") or []:
            for key in ("iata", "icao"):
                code = item.get(key)
                if code:
                    codes.add(str(code).upper())
    return codes


def _unverified_code_result(tool: str, field: str, code: str) -> dict[str, Any]:
    return {
        "tool": tool,
        "error": "unverified_airport_code",
        "message": (
            f"'{code}' (field '{field}') has not been verified via search_airports "
            "in this conversation. Call search_airports for it first and use the "
            "exact iata/icao code it returns — do not guess or reuse a remembered code."
        ),
    }


def execute_tool_call(call: ToolCall, verified_codes: set[str] | None = None) -> dict[str, Any]:
    func = TOOL_FUNCTIONS.get(call.name)
    if not func:
        return {
            "tool": call.name,
            "args": call.args,
            "result": {"error": "unknown_tool", "message": f"No implementation for {call.name}"},
        }
    verified_codes = verified_codes if verified_codes is not None else set()
    for field in AIRPORT_CODE_FIELDS.get(call.name, ()):
        code = call.args.get(field)
        if code and str(code).upper() not in verified_codes:
            return {"tool": call.name, "args": call.args, "result": _unverified_code_result(call.name, field, str(code))}
    try:
        result = func(**call.args)
    except Exception as exc:
        result = {"error": type(exc).__name__, "message": str(exc)}
    return {"tool": call.name, "args": call.args, "result": result}


def _tool_call_message(calls: list[ToolCall], text: str | None) -> dict[str, Any]:
    return {
        "role": "assistant",
        "content": text or "",
        "tool_calls": [
            {"id": call.id, "type": "function", "function": {"name": call.name, "arguments": json.dumps(call.args, ensure_ascii=False)}}
            for call in calls
        ],
    }


def _tool_result_message(call: ToolCall, event: dict[str, Any]) -> dict[str, Any]:
    return {"role": "tool", "tool_call_id": call.id, "content": json.dumps(event["result"], ensure_ascii=False, default=str)}


def build_graph(
    *,
    provider: Any,
    model: str | None,
    max_tool_rounds: int,
    on_tool_call: Callable[[dict[str, Any]], None] | None = None,
) -> StateGraph:
    graph = StateGraph()

    def node_plan(state: dict[str, Any]) -> None:
        response = provider.complete(state["messages"], TOOL_SCHEMAS, model=model)
        state["response"] = response
        if response.tool_calls:
            state["messages"].append(_tool_call_message(response.tool_calls, response.text))

    def route_after_plan(state: dict[str, Any]) -> str:
        response = state["response"]
        if not response.tool_calls or state["round"] >= max_tool_rounds:
            return "respond"
        return "act"

    def node_act(state: dict[str, Any]) -> None:
        response = state["response"]
        state["round"] += 1
        round_record: dict[str, Any] = {"round": state["round"], "tool_calls": []}
        state["rounds"].append(round_record)
        events = []
        # Built from prior turns' history, then extended as search_airports
        # results come back within this same round (covers parallel tool
        # calls where the model looks up and uses a code in one batch).
        verified_codes = _collect_verified_codes(state["messages"])
        for call in response.tool_calls:
            event = execute_tool_call(call, verified_codes)
            events.append(event)
            round_record["tool_calls"].append(event)
            state["all_tool_events"].append(event)
            if on_tool_call:
                on_tool_call(event)
            state["messages"].append(_tool_result_message(call, event))
            if call.name == "search_airports":
                result = event.get("result") or {}
                for item in result.get("items") or []:
                    for key in ("iata", "icao"):
                        code = item.get(key)
                        if code:
                            verified_codes.add(str(code).upper())
        state["last_tool_events"] = events

    def node_auto_recommend(state: dict[str, Any]) -> None:
        if state.get("auto_recommended"):
            return
        search_event = next((e for e in state.get("last_tool_events", []) if e["tool"] == "search_flight_prices"), None)
        if not search_event:
            return
        items = (search_event.get("result") or {}).get("items") or []
        already_compared = any(e["tool"] == "compare_flight_offers" for e in state["all_tool_events"])
        if len(items) < 2 or already_compared:
            return

        call = ToolCall(id=f"auto-compare-{state['round']}", name="compare_flight_offers", args={"offers": items})
        event = execute_tool_call(call)
        state["all_tool_events"].append(event)
        state["rounds"][-1]["tool_calls"].append(event)
        if on_tool_call:
            on_tool_call(event)
        state["messages"].append(_tool_call_message([call], None))
        state["messages"].append(_tool_result_message(call, event))
        state["auto_recommended"] = True

    def node_respond(state: dict[str, Any]) -> None:
        response = state.get("response")
        answered = bool(response) and not response.tool_calls
        if answered:
            text = response.text or ""
        else:
            text = f"Stopped after {max_tool_rounds} tool rounds without a final answer."
            state["messages"].append({"role": "assistant", "content": text})
        state["assistant_text"] = text
        state["status"] = "answered" if answered else "max_tool_rounds"

    graph.add_node("plan", node_plan)
    graph.add_node("act", node_act)
    graph.add_node("auto_recommend", node_auto_recommend)
    graph.add_node("respond", node_respond)

    graph.add_conditional_edges("plan", route_after_plan, {"has_tool_calls": "act", "final_answer_or_out_of_rounds": "respond"})
    graph.add_edge("act", "auto_recommend")
    graph.add_edge("auto_recommend", "plan")
    graph.add_edge("respond", END)

    graph.set_entry("plan")
    return graph


def run_turn(
    *,
    provider: Any,
    messages: list[dict[str, Any]],
    model: str | None = None,
    max_tool_rounds: int = 6,
    on_tool_call: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    graph = build_graph(provider=provider, model=model, max_tool_rounds=max_tool_rounds, on_tool_call=on_tool_call)
    seeded_messages = list(messages)
    insert_at = 1 if seeded_messages and seeded_messages[0].get("role") == "system" else 0
    seeded_messages.insert(insert_at, _time_grounding_message())
    state: dict[str, Any] = {
        "messages": seeded_messages,
        "round": 0,
        "rounds": [],
        "all_tool_events": [],
        "last_tool_events": [],
        "auto_recommended": False,
    }
    state = graph.run(state, max_steps=max_tool_rounds * 4 + 4)
    return {
        "status": state["status"],
        "assistant_text": state["assistant_text"],
        "rounds": state["rounds"],
        "messages": state["messages"],
        "graph_trace": state["_trace"],
    }
