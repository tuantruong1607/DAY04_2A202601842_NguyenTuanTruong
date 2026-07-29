"""Minimal, dependency-free graph-agent engine.

A `StateGraph` is a set of named nodes (state -> state-updates) connected by
either a fixed edge or a conditional router (state -> next node name). This
is the same shape as LangGraph's `StateGraph` (nodes/edges/conditional
routing over a shared mutable state) implemented from scratch so the agent
has no framework dependency — the point here is the architecture, not the
library.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

END = "__end__"

NodeFn = Callable[[dict[str, Any]], dict[str, Any] | None]
RouterFn = Callable[[dict[str, Any]], str]


@dataclass
class _ConditionalEdge:
    router: RouterFn
    targets: dict[str, str]  # label -> node name, for diagramming only


@dataclass
class StateGraph:
    nodes: dict[str, NodeFn] = field(default_factory=dict)
    edges: dict[str, str | _ConditionalEdge] = field(default_factory=dict)
    entry: str | None = None

    def add_node(self, name: str, fn: NodeFn) -> "StateGraph":
        self.nodes[name] = fn
        return self

    def add_edge(self, from_node: str, to_node: str) -> "StateGraph":
        self.edges[from_node] = to_node
        return self

    def add_conditional_edges(self, from_node: str, router: RouterFn, targets: dict[str, str]) -> "StateGraph":
        self.edges[from_node] = _ConditionalEdge(router=router, targets=targets)
        return self

    def set_entry(self, name: str) -> "StateGraph":
        self.entry = name
        return self

    def run(self, state: dict[str, Any], *, max_steps: int = 50) -> dict[str, Any]:
        if not self.entry:
            raise ValueError("Graph has no entry node")
        if self.entry not in self.nodes:
            raise ValueError(f"Unknown entry node: {self.entry}")

        current = self.entry
        trace: list[str] = []
        for _ in range(max_steps):
            trace.append(current)
            fn = self.nodes.get(current)
            if fn is None:
                raise ValueError(f"Unknown node: {current}")
            updates = fn(state)
            if updates:
                state.update(updates)

            edge = self.edges.get(current)
            if edge is None:
                break
            if isinstance(edge, _ConditionalEdge):
                next_node = edge.router(state)
            else:
                next_node = edge
            if next_node == END:
                break
            current = next_node
        else:
            raise RuntimeError(f"Graph exceeded max_steps={max_steps} (possible cycle without exit)")

        state["_trace"] = trace
        return state

    def mermaid(self) -> str:
        lines = ["graph TD"]
        for name in self.nodes:
            lines.append(f"    {name}([{name}])")
        for src, edge in self.edges.items():
            if isinstance(edge, _ConditionalEdge):
                for label, target in edge.targets.items():
                    target_name = "END" if target == END else target
                    lines.append(f"    {src} -- {label} --> {target_name}")
            else:
                target_name = "END" if edge == END else edge
                lines.append(f"    {src} --> {target_name}")
        return "\n".join(lines)
