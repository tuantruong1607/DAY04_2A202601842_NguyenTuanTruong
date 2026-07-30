"use client";

import {
  ArrowSquareOut,
  CaretDown,
  CheckCircle,
  CircleNotch,
  Database,
  FacebookLogo,
  GearSix,
  InstagramLogo,
  MagnifyingGlass,
  NewspaperClipping,
  PaperPlaneTilt,
  Plus,
  ShieldCheck,
  SoccerBall,
  Wrench,
  XLogo,
} from "@phosphor-icons/react";
import { FormEvent, KeyboardEvent, useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import type { AppMeta, ChatResponse, ChatTurn, Evidence, ToolEvent } from "@/lib/types";

const QUICK_PROMPTS = [
  { label: "Tin mới hôm nay", prompt: "Tóm tắt các tin bóng đá đáng chú ý mới nhất hôm nay và kiểm chứng nguồn." },
  { label: "Chuyển nhượng Liverpool", prompt: "Cập nhật tin chuyển nhượng mới nhất của Liverpool, phân biệt tin xác nhận và tin đồn." },
  { label: "Kiểm tra tin đồn", prompt: "Hãy giúp tôi kiểm tra một tin đồn bóng đá. Trước tiên hỏi tôi tin đồn cụ thể nếu chưa đủ thông tin." },
  { label: "Mạng xã hội Real Madrid", prompt: "Kiểm tra cập nhật gần đây từ các kênh mạng xã hội của Real Madrid và đối chiếu với báo chí." },
] as const;

const TOOL_LABELS: Record<string, string> = {
  clarify: "Làm rõ yêu cầu",
  lookup: "Tìm kiếm web",
  fetch: "Đọc nội dung",
  timeline: "Dòng thời gian",
  social_search: "Tìm mạng xã hội",
  instagram_profile: "Instagram",
  facebook_page_transparency: "Facebook",
  format: "Định dạng",
  send: "Gửi kết quả",
  policy: "Tra chính sách",
  papers: "Tìm bài báo khoa học",
  paper_text: "Đọc bài báo khoa học",
};

function getEvalScore(run: { summary?: Record<string, number | string | boolean | null> } | null | undefined) {
  const summary = run?.summary;
  if (!summary) return "Chưa có dữ liệu";
  const measured = summary.measured_cases ?? summary.measured ?? summary.total_cases;
  const total = summary.total_cases ?? summary.total;
  if (measured !== undefined && total !== undefined) return `${measured}/${total} case`;
  const passed = summary.passed_cases ?? summary.passed;
  return passed !== undefined ? `${passed} case đạt` : "Đã hoàn tất";
}

function toolName(event: ToolEvent) {
  return String(event.tool ?? event.name ?? "").trim();
}

function ToolUsage({ events = [] }: { events?: ToolEvent[] }) {
  const usage = useMemo(() => {
    const counts = new Map<string, number>();
    for (const event of events) {
      const name = toolName(event);
      if (name) counts.set(name, (counts.get(name) ?? 0) + 1);
    }
    return [...counts.entries()];
  }, [events]);

  return (
    <section className="tool-usage" aria-label="Công cụ đã sử dụng">
      <span className="eyebrow tool-heading"><Wrench size={14} weight="bold" /> Công cụ đã sử dụng</span>
      <div className="tool-list">
        {usage.length ? usage.map(([name, count]) => (
          <span className="tool-chip" key={name}>
            {TOOL_LABELS[name] ?? name}<small>{name}{count > 1 ? ` ×${count}` : ""}</small>
          </span>
        )) : <span className="tool-chip tool-chip-muted">Không sử dụng công cụ</span>}
      </div>
    </section>
  );
}

function Sources({ evidence = [] }: { evidence?: Evidence[] }) {
  if (!evidence.length) return null;
  return (
    <details className="disclosure sources">
      <summary><NewspaperClipping size={17} /> {evidence.length} nguồn đã kiểm tra <CaretDown size={15} className="caret" /></summary>
      <div className="source-list">
        {evidence.slice(0, 12).map((item, index) => (
          <article className="source-item" key={`${item.url ?? item.title}-${index}`}>
            <div>
              {item.url ? (
                <a href={item.url} target="_blank" rel="noreferrer">
                  {item.title || item.url}<ArrowSquareOut size={14} />
                </a>
              ) : <strong>{item.title || "Nguồn dữ liệu"}</strong>}
              <p>{item.summary || item.snippet || "Nguồn được agent sử dụng trong quá trình kiểm chứng."}</p>
            </div>
            <span>{[item.source, item.published_date || item.published_at, item.backend].filter(Boolean).join(" · ")}</span>
          </article>
        ))}
      </div>
    </details>
  );
}

function TechnicalTrace({ turn }: { turn: ChatTurn }) {
  return (
    <details className="disclosure trace">
      <summary><Database size={17} /> Chi tiết kỹ thuật <CaretDown size={15} className="caret" /></summary>
      <div className="trace-content">
        <p>Trạng thái: <code>{turn.status ?? "unknown"}</code></p>
        {(turn.rounds ?? []).map((round, index) => (
          <section key={index}>
            <h4>Vòng {round.round_index ?? round.round ?? index + 1} <span>{round.stage ?? "agent"}</span></h4>
            {(round.tool_calls ?? []).map((call, callIndex) => (
              <div className="trace-block" key={callIndex}>
                <strong>{call.name ?? "tool"}</strong>
                <pre>{JSON.stringify(call.arguments ?? call.args ?? {}, null, 2)}</pre>
              </div>
            ))}
            {(round.tool_results ?? []).map((result, resultIndex) => (
              <div className="trace-block" key={`result-${resultIndex}`}>
                <strong>{result.name ?? result.tool ?? "result"}</strong>
                <pre>{JSON.stringify(result.result ?? result, null, 2)}</pre>
              </div>
            ))}
          </section>
        ))}
      </div>
    </details>
  );
}

function AssistantTurn({ turn, expertMode }: { turn: ChatTurn; expertMode: boolean }) {
  const providerError = turn.status === "provider_error";
  return (
    <div className="assistant-row">
      <div className="avatar"><SoccerBall size={19} weight="fill" /></div>
      <article className={`assistant-card${providerError ? " error-card" : ""}`}>
        <div className="message-meta"><span>Sân Cỏ Live</span><span>{providerError ? "Có lỗi kết nối" : "Đã kiểm chứng"}</span></div>
        <div className="markdown">
          <ReactMarkdown>{turn.assistant_text || "Không có nội dung trả lời."}</ReactMarkdown>
        </div>
        {providerError && turn.error ? <p className="error-detail">{turn.error}</p> : null}
        <ToolUsage events={turn.tool_events} />
        <Sources evidence={turn.evidence} />
        {expertMode ? <TechnicalTrace turn={turn} /> : null}
      </article>
    </div>
  );
}

function LoadingTurn() {
  return (
    <div className="assistant-row" aria-live="polite">
      <div className="avatar"><CircleNotch size={19} className="spinner" /></div>
      <article className="assistant-card loading-card">
        <div className="loading-title"><span className="live-dot" /> Agent đang nghiên cứu</div>
        <div className="loading-lines"><span /><span /><span /></div>
        <p>Đang chọn công cụ, tìm nguồn và tổng hợp câu trả lời tiếng Việt.</p>
      </article>
    </div>
  );
}

export function ChatShell() {
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expertMode, setExpertMode] = useState(false);
  const [meta, setMeta] = useState<AppMeta | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    fetch("/backend/meta")
      .then((response) => response.ok ? response.json() : Promise.reject(new Error("API chưa sẵn sàng")))
      .then(setMeta)
      .catch(() => setError("Chưa kết nối được Python API tại cổng 8000."));
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turns, loading]);

  async function submitText(text: string) {
    const cleanText = text.trim();
    if (!cleanText || loading) return;
    setMessage("");
    setError(null);
    setLoading(true);
    const pendingUser: ChatTurn = { user: cleanText, status: "pending" };
    setTurns((current) => [...current, pendingUser]);

    try {
      const response = await fetch("/backend/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: cleanText, session_id: sessionId, history_window: 5, max_tool_rounds: 4 }),
      });
      if (!response.ok) throw new Error(`API trả mã ${response.status}`);
      const payload = await response.json() as ChatResponse;
      setSessionId(payload.session_id);
      setTurns((current) => [...current.slice(0, -1), payload.turn]);
    } catch (cause) {
      const detail = cause instanceof Error ? cause.message : "Lỗi không xác định";
      setTurns((current) => [...current.slice(0, -1), {
        user: cleanText,
        status: "provider_error",
        assistant_text: "Mình chưa thể hoàn tất lượt này. Hãy kiểm tra FastAPI và thử lại.",
        error: detail,
        tool_events: [],
      }]);
      setError(detail);
    } finally {
      setLoading(false);
      textareaRef.current?.focus();
    }
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    void submitText(message);
  }

  function onTextareaKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void submitText(message);
    }
  }

  async function resetChat() {
    if (sessionId) {
      try { await fetch(`/backend/sessions/${encodeURIComponent(sessionId)}`, { method: "DELETE" }); } catch { /* Local reset still works. */ }
    }
    setSessionId(null);
    setTurns([]);
    setError(null);
    textareaRef.current?.focus();
  }

  const visibleTurns = turns.filter((turn) => turn.status !== "pending");
  const pendingTurn = turns.findLast((turn) => turn.status === "pending");

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark"><SoccerBall size={25} weight="fill" /></div>
          <div><strong>Sân Cỏ Live</strong><span>Football intelligence</span></div>
        </div>

        <button className="new-chat" type="button" onClick={() => void resetChat()}>
          <Plus size={18} weight="bold" /> Cuộc trò chuyện mới
        </button>

        <nav className="quick-nav" aria-label="Gợi ý nhanh">
          <span className="eyebrow">Bắt đầu nhanh</span>
          {QUICK_PROMPTS.map((item) => (
            <button type="button" key={item.label} onClick={() => void submitText(item.prompt)} disabled={loading}>
              <MagnifyingGlass size={17} /> <span>{item.label}</span>
            </button>
          ))}
        </nav>

        <section className="system-panel">
          <div className="system-title"><ShieldCheck size={18} weight="fill" /><strong>Hệ thống sẵn sàng</strong></div>
          <dl>
            <div><dt>Provider</dt><dd>{meta?.provider ?? "OpenRouter"}</dd></div>
            <div><dt>Base eval</dt><dd>{getEvalScore(meta?.evals?.base)}</dd></div>
            <div><dt>Group eval</dt><dd>{getEvalScore(meta?.evals?.group)}</dd></div>
          </dl>
        </section>

        <label className="expert-toggle">
          <span><GearSix size={17} /> Chế độ chuyên gia</span>
          <input type="checkbox" checked={expertMode} onChange={(event) => setExpertMode(event.target.checked)} />
          <i aria-hidden="true" />
        </label>
      </aside>

      <section className="chat-panel">
        <header className="topbar">
          <div><span className="live-dot" /><strong>Agent trực tuyến</strong><small>Tìm kiếm, đối chiếu, trả lời bằng tiếng Việt</small></div>
          <div className="network-icons" aria-label="Nguồn mạng xã hội hỗ trợ">
            <XLogo size={17} /><InstagramLogo size={18} /><FacebookLogo size={18} />
          </div>
        </header>

        <div className="conversation">
          {!visibleTurns.length && !loading ? (
            <section className="empty-state">
              <div className="empty-kicker"><CheckCircle size={17} weight="fill" /> Có nguồn, có kiểm chứng</div>
              <h1>Hỏi bất cứ điều gì<br />về bóng đá hôm nay.</h1>
              <p>Agent tự chọn công cụ phù hợp, tìm dữ liệu mới, đối chiếu nhiều nguồn và trình bày lại bằng tiếng Việt.</p>
              <div className="capabilities">
                <span><MagnifyingGlass size={17} /> Tin mới</span>
                <span><ShieldCheck size={17} /> Kiểm tra tin đồn</span>
                <span><Database size={17} /> Dòng thời gian</span>
              </div>
            </section>
          ) : null}

          {visibleTurns.map((turn, index) => (
            <section className="turn" key={`${turn.turn_index ?? index}-${turn.user}`}>
              <div className="user-row"><div className="user-bubble">{turn.user}</div></div>
              <AssistantTurn turn={turn} expertMode={expertMode} />
            </section>
          ))}
          {loading && pendingTurn ? (
            <section className="turn">
              <div className="user-row"><div className="user-bubble">{pendingTurn.user}</div></div>
              <LoadingTurn />
            </section>
          ) : null}
          <div ref={endRef} />
        </div>

        <footer className="composer-wrap">
          {error ? <div className="connection-error">{error}</div> : null}
          <form className="composer" onSubmit={onSubmit}>
            <label className="sr-only" htmlFor="football-question">Câu hỏi về bóng đá</label>
            <textarea
              id="football-question"
              ref={textareaRef}
              value={message}
              onChange={(event) => setMessage(event.target.value)}
              onKeyDown={onTextareaKeyDown}
              rows={1}
              placeholder="Hỏi về tin tức, trận đấu, chuyển nhượng..."
              disabled={loading}
            />
            <button type="submit" disabled={loading || !message.trim()} aria-label="Gửi câu hỏi">
              {loading ? <CircleNotch size={20} className="spinner" /> : <PaperPlaneTilt size={20} weight="fill" />}
            </button>
          </form>
          <p>Enter để gửi, Shift + Enter để xuống dòng. Kết quả có thể sai, hãy kiểm tra nguồn quan trọng.</p>
        </footer>
      </section>
    </main>
  );
}
