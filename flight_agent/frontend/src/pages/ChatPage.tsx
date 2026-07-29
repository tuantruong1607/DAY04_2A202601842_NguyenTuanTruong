import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { ChatTurn, ToolEvent, ToolRound, VersionInfo } from "../types";
import { Spinner } from "../components/Spinner";
import { JsonView } from "../components/JsonView";

const SUGGESTIONS = [
  "Tìm vé một chiều từ Hà Nội đến Sài Gòn ngày 15/08/2026, ngân sách 60 USD",
  "Chuyến bay VN7 hiện đang ở trạng thái nào?",
  "Sân bay Nội Bài có chuyến nào khởi hành trong 6 tiếng tới?",
  "Theo dõi giá vé HAN-SGN, báo khi dưới 50 USD",
];

const TOOL_META: Record<string, { icon: string; label: string }> = {
  get_current_time: { icon: "🕒", label: "Giờ hiện tại" },
  search_airports: { icon: "🛫", label: "Tra cứu sân bay" },
  search_flight_prices: { icon: "💰", label: "Tìm giá vé" },
  get_flight_status: { icon: "🛬", label: "Trạng thái chuyến bay" },
  get_airport_arrivals: { icon: "🛬", label: "Chuyến đến" },
  get_airport_departures: { icon: "🛫", label: "Chuyến đi" },
  compare_flight_offers: { icon: "⚖️", label: "So sánh chuyến bay" },
  analyze_price_history: { icon: "📈", label: "Phân tích giá" },
  create_price_watch: { icon: "🔔", label: "Tạo theo dõi giá" },
  create_flight_status_watch: { icon: "🔔", label: "Tạo theo dõi trạng thái" },
  cancel_watch: { icon: "❌", label: "Hủy theo dõi" },
};

const STEP_META: Record<string, { icon: string; label: string; tone: string }> = {
  plan: { icon: "🧠", label: "Suy nghĩ", tone: "bg-violet-400/10 text-violet-300 border-violet-400/20" },
  act: { icon: "🔧", label: "Gọi tool", tone: "bg-sky-400/10 text-sky-300 border-sky-400/20" },
  auto_recommend: { icon: "⚖️", label: "Tự động so sánh", tone: "bg-amber-400/10 text-amber-300 border-amber-400/20" },
  respond: { icon: "✅", label: "Trả lời", tone: "bg-emerald-400/10 text-emerald-300 border-emerald-400/20" },
};

function toolIsError(result: ToolEvent["result"]): boolean {
  return !!(result && typeof result === "object" && !Array.isArray(result) && "error" in result && (result as Record<string, unknown>).error);
}

function GraphTrace({ steps }: { steps: string[] }) {
  if (!steps.length) return null;
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {steps.map((step, i) => {
        const meta = STEP_META[step] ?? { icon: "•", label: step, tone: "bg-slate-400/10 text-slate-300 border-slate-400/20" };
        return (
          <span key={i} className="flex items-center gap-1.5">
            <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-medium ${meta.tone}`}>
              <span>{meta.icon}</span>
              {meta.label}
            </span>
            {i < steps.length - 1 && <span className="text-[10px] text-[var(--color-muted)]">→</span>}
          </span>
        );
      })}
    </div>
  );
}

function ToolCallCard({ event }: { event: ToolEvent }) {
  const [open, setOpen] = useState(false);
  const meta = TOOL_META[event.tool] ?? { icon: "🔧", label: event.tool };
  const isError = toolIsError(event.result);
  const argsPreview = Object.entries(event.args || {})
    .map(([k, v]) => `${k}=${typeof v === "string" ? v : JSON.stringify(v)}`)
    .join(", ");

  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-panel)]">
      <button onClick={() => setOpen((v) => !v)} className="flex w-full items-start gap-2.5 px-3 py-2 text-left">
        <span className="mt-0.5 text-sm">{meta.icon}</span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs font-semibold text-slate-200">{event.tool}</span>
            <span
              className={`inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 text-[10px] font-medium ${
                isError ? "bg-rose-400/10 text-rose-300" : "bg-emerald-400/10 text-emerald-300"
              }`}
            >
              {isError ? "lỗi" : "ok"}
            </span>
          </div>
          {argsPreview && <div className="mt-0.5 truncate font-mono text-[11px] text-[var(--color-muted)]">{argsPreview}</div>}
        </div>
        <span className="mt-0.5 text-[var(--color-muted)]">{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <div className="space-y-2 border-t border-[var(--color-border)] px-3 py-2">
          <div>
            <div className="mb-1 text-[10px] uppercase tracking-wide text-[var(--color-muted)]">Input</div>
            <JsonView data={event.args} collapsedByDefault />
          </div>
          <div>
            <div className="mb-1 text-[10px] uppercase tracking-wide text-[var(--color-muted)]">Output</div>
            <JsonView data={event.result} />
          </div>
        </div>
      )}
    </div>
  );
}

function AgentTrace({ turn }: { turn: ChatTurn }) {
  const [expanded, setExpanded] = useState(false);
  const rounds: ToolRound[] = turn.rounds?.length ? turn.rounds : turn.toolEvents?.length ? [{ round: 1, tool_calls: turn.toolEvents }] : [];
  const totalCalls = rounds.reduce((n, r) => n + r.tool_calls.length, 0);
  if (!totalCalls && !turn.graphTrace?.length) return null;

  return (
    <div className="mt-2 rounded-xl border border-[var(--color-border)] bg-black/20">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-xs text-[var(--color-muted)] hover:text-slate-200"
      >
        <span className="flex items-center gap-2">
          <span className="font-medium text-slate-300">🧭 Các bước agent</span>
          {totalCalls > 0 && <span className="text-[var(--color-muted)]">{totalCalls} tool call{totalCalls > 1 ? "s" : ""}</span>}
        </span>
        <span>{expanded ? "▲ thu gọn" : "▼ xem chi tiết"}</span>
      </button>

      {expanded && (
        <div className="space-y-3 border-t border-[var(--color-border)] px-3 py-3">
          {turn.graphTrace && turn.graphTrace.length > 0 && (
            <div>
              <div className="mb-1.5 text-[10px] uppercase tracking-wide text-[var(--color-muted)]">Luồng xử lý (graph trace)</div>
              <GraphTrace steps={turn.graphTrace} />
            </div>
          )}
          {rounds.map((round) => (
            <div key={round.round}>
              <div className="mb-1.5 text-[10px] uppercase tracking-wide text-[var(--color-muted)]">Round {round.round}</div>
              <div className="space-y-1.5">
                {round.tool_calls.map((event, i) => (
                  <ToolCallCard key={i} event={event} />
                ))}
              </div>
            </div>
          ))}
          {turn.artifactVersion && (
            <div className="border-t border-[var(--color-border)] pt-2 font-mono text-[10px] text-[var(--color-muted)]">
              agent {turn.artifactVersion}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function ChatPage() {
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState<VersionInfo | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns, loading]);

  useEffect(() => {
    api.getVersion().then(setVersion).catch(() => setVersion(null));
  }, []);

  async function send(text: string) {
    const message = text.trim();
    if (!message || loading) return;
    setInput("");
    setError(null);
    const now = () => new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    setTurns((prev) => [...prev, { role: "user", text: message, time: now() }]);
    setLoading(true);
    try {
      const res = await api.sendChat(sessionId, message);
      setSessionId(res.session_id);
      setTurns((prev) => [
        ...prev,
        {
          role: "assistant",
          text: res.assistant_text,
          time: now(),
          toolEvents: res.tool_events,
          rounds: res.rounds,
          graphTrace: res.graph_trace,
          status: res.status,
          artifactVersion: res.artifact_version,
        },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  async function newChat() {
    if (sessionId) {
      try {
        await api.resetChat(sessionId);
      } catch {
        // best-effort — the session will just age out server-side otherwise
      }
    }
    setSessionId(null);
    setTurns([]);
    setError(null);
  }

  return (
    <div className="mx-auto flex h-full max-w-3xl flex-col px-6 py-6">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-semibold text-slate-100">Chat với Flight Agent</h1>
            {version && (
              <span
                title={`prompt_hash: ${version.prompt_hash}\ntools_hash: ${version.tools_hash}`}
                className="rounded-full border border-[var(--color-border)] bg-black/20 px-2 py-0.5 font-mono text-[10px] text-[var(--color-muted)]"
              >
                {version.artifact_version}
              </span>
            )}
          </div>
          <p className="text-sm text-[var(--color-muted)]">
            Tìm chuyến bay, theo dõi trạng thái, hỏi về sân bay — mọi câu trả lời đều dựa trên dữ liệu tool gọi được, kèm nguồn.
          </p>
        </div>
        {turns.length > 0 && (
          <button
            onClick={newChat}
            className="shrink-0 rounded-xl border border-[var(--color-border)] px-3 py-2 text-xs font-medium text-[var(--color-muted)] hover:border-sky-400/40 hover:text-sky-200"
          >
            + Chat mới
          </button>
        )}
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto scrollbar-thin pr-1">
        {turns.length === 0 && (
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                onClick={() => send(s)}
                className="rounded-xl border border-[var(--color-border)] bg-[var(--color-card)] px-4 py-3 text-left text-sm text-slate-300 transition-colors hover:border-sky-400/40 hover:text-sky-200"
              >
                {s}
              </button>
            ))}
          </div>
        )}

        {turns.map((turn, i) => {
          const isUser = turn.role === "user";
          return (
            <div key={i} className={`flex items-start gap-2.5 ${isUser ? "flex-row-reverse" : ""}`}>
              <div
                className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-sm ${
                  isUser ? "bg-sky-500/20" : "bg-white/5"
                }`}
              >
                {isUser ? "🧑" : "✈️"}
              </div>
              <div className={`max-w-[85%] ${isUser ? "flex flex-col items-end" : "w-full"}`}>
                <div
                  className={`whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                    isUser ? "bg-sky-500 text-white" : "border border-[var(--color-border)] bg-[var(--color-card)] text-slate-100"
                  }`}
                >
                  {turn.text}
                </div>
                <div className="mt-1 flex items-center gap-2 px-1 text-[10px] text-[var(--color-muted)]">
                  {turn.time}
                  {turn.status === "max_tool_rounds" && (
                    <span className="text-amber-300">⚠ dừng do vượt số vòng gọi tool</span>
                  )}
                </div>
                {!isUser && <AgentTrace turn={turn} />}
              </div>
            </div>
          );
        })}

        {loading && (
          <div className="flex items-center gap-2 text-sm text-[var(--color-muted)]">
            <Spinner /> Agent đang xử lý…
          </div>
        )}
        {error && <div className="rounded-lg border border-rose-400/30 bg-rose-400/10 px-3 py-2 text-sm text-rose-300">{error}</div>}
        <div ref={bottomRef} />
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
        className="mt-4 flex items-center gap-2 rounded-2xl border border-[var(--color-border)] bg-[var(--color-card)] p-2"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Hỏi về chuyến bay, giá vé, sân bay…"
          className="flex-1 bg-transparent px-3 py-2 text-sm text-slate-100 outline-none placeholder:text-[var(--color-muted)]"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="rounded-xl bg-sky-500 px-4 py-2 text-sm font-medium text-white transition-opacity disabled:opacity-40"
        >
          Gửi
        </button>
      </form>
    </div>
  );
}
