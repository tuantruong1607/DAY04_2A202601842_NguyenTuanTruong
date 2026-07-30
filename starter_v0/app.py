from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import streamlit as st

from chat import now_iso, run_model_tool_loop, tool_usage_counts, trim_history, write_transcript
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

TOOL_LABELS = {
    "clarify": "Làm rõ yêu cầu",
    "lookup": "Tìm tin trên web",
    "fetch": "Đọc nguồn gốc",
    "timeline": "Đọc timeline X",
    "social_search": "Tìm thảo luận trên X",
    "instagram_profile": "Kiểm tra Instagram",
    "facebook_page_transparency": "Kiểm tra Facebook Page",
    "format": "Định dạng bản tin",
    "send": "Gửi nội dung",
    "policy": "Tra cứu chính sách",
    "papers": "Tìm bài nghiên cứu",
    "paper_text": "Đọc bài nghiên cứu",
}

QUICK_PROMPTS = [
    ("Tin mới hôm nay", "Tóm tắt những tin bóng đá đáng chú ý nhất hôm nay, ưu tiên nguồn uy tín."),
    ("Chuyển nhượng Liverpool", "Tìm tin chuyển nhượng mới nhất về Liverpool hôm nay và đánh giá độ tin cậy."),
    ("Kiểm tra một tin đồn", "Tôi muốn kiểm tra một tin đồn chuyển nhượng nhưng chưa biết cần cung cấp gì."),
    ("Instagram Real Madrid", "Kiểm tra số liệu công khai của tài khoản Instagram @realmadrid."),
]

load_lab_env(ROOT)

st.set_page_config(
    page_title="Football News VAR",
    page_icon=":material/sports_soccer:",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root {
        --page: #0d100e;
        --sidebar: #111512;
        --surface: #151a16;
        --surface-strong: #1b211c;
        --line: #303832;
        --line-soft: #242b26;
        --text: #f5f7f2;
        --muted: #c5cbc4;
        --faint: #9da59e;
        --accent: #b7d65a;
        --accent-ink: #172006;
        --radius-surface: 14px;
        --radius-control: 10px;
    }
    html, body, [class*="css"] {
        font-family: "Aptos", "Segoe UI", Arial, sans-serif;
        color-scheme: dark;
    }
    .stApp { background: var(--page); color: var(--text); }
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"] {
        background: var(--page);
        color: var(--text);
    }
    [data-testid="stMarkdownContainer"] h1,
    [data-testid="stMarkdownContainer"] h2,
    [data-testid="stMarkdownContainer"] h3,
    [data-testid="stMarkdownContainer"] h4,
    [data-testid="stMarkdownContainer"] h5,
    [data-testid="stMarkdownContainer"] h6,
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] li,
    [data-testid="stMarkdownContainer"] strong,
    [data-testid="stMarkdownContainer"] blockquote {
        color: var(--text);
    }
    [data-testid="stCaptionContainer"],
    [data-testid="stCaptionContainer"] p,
    .stCaptionContainer,
    .stCaptionContainer p {
        color: var(--muted) !important;
        opacity: 1 !important;
    }
    [data-testid="stWidgetLabel"] p,
    [data-testid="stWidgetLabel"] span,
    label,
    legend {
        color: var(--text) !important;
        opacity: 1 !important;
    }
    [data-testid="stHeader"] { background: rgba(13, 16, 14, .94); }
    [data-testid="stSidebar"] {
        background: var(--sidebar);
        border-right: 1px solid var(--line-soft);
        color: var(--text);
    }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] li,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] span:not([data-baseweb="icon"]) {
        color: var(--text);
    }
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"],
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
        color: var(--muted) !important;
    }
    [data-testid="stSidebar"] .block-container { padding-top: 1.4rem; }
    .block-container {
        max-width: 1020px;
        padding-top: 1.25rem;
        padding-bottom: 8rem;
    }
    .fn-brand {
        display: grid;
        grid-template-columns: 42px 1fr auto;
        align-items: center;
        gap: .8rem;
        padding: .45rem 0 1rem;
        border-bottom: 1px solid var(--line-soft);
        margin-bottom: 1.35rem;
    }
    .fn-mark {
        width: 42px;
        height: 42px;
        display: grid;
        place-items: center;
        border-radius: 12px;
        background: var(--accent);
        color: var(--accent-ink);
        font-weight: 900;
        letter-spacing: -.05em;
    }
    .fn-brand-name {
        color: var(--text);
        font-size: 1.02rem;
        font-weight: 780;
        line-height: 1.15;
    }
    .fn-brand-sub {
        color: var(--muted);
        font-size: .78rem;
        margin-top: .18rem;
    }
    .fn-live {
        color: var(--accent);
        border: 1px solid #52602c;
        border-radius: 999px;
        padding: .3rem .58rem;
        font-size: .72rem;
        font-weight: 750;
        white-space: nowrap;
    }
    .fn-welcome {
        min-height: 310px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        padding: 1.5rem 0 1rem;
        max-width: 740px;
    }
    .fn-welcome h1 {
        margin: 0;
        color: var(--text);
        font-size: clamp(2.4rem, 6vw, 4.6rem);
        letter-spacing: -.065em;
        line-height: .95;
        font-weight: 820;
    }
    .fn-welcome p {
        margin: 1rem 0 0;
        color: var(--muted);
        font-size: 1.08rem;
        line-height: 1.55;
        max-width: 560px;
    }
    .fn-section-title {
        color: var(--text);
        font-size: .95rem;
        font-weight: 760;
        margin: .3rem 0 .65rem;
    }
    .fn-source {
        padding: .78rem 0;
        border-bottom: 1px solid var(--line-soft);
    }
    .fn-source:last-child { border-bottom: 0; }
    .fn-source a {
        color: var(--text);
        font-weight: 700;
        text-decoration: none;
        line-height: 1.35;
    }
    .fn-source a:hover { color: var(--accent); text-decoration: underline; }
    .fn-source-meta {
        color: var(--muted);
        font-size: .75rem;
        margin-top: .28rem;
    }
    .fn-tool-usage {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: .4rem;
        margin: .8rem 0 .6rem;
        color: var(--muted);
        font-size: .78rem;
    }
    .fn-tool-usage-label {
        color: var(--faint);
        font-weight: 700;
    }
    .fn-tool-chip {
        display: inline-flex;
        align-items: center;
        padding: .24rem .5rem;
        border: 1px solid var(--line);
        border-radius: 999px;
        background: var(--surface-strong);
        color: var(--text);
        font-family: Consolas, "Courier New", monospace;
        font-size: .72rem;
    }
    .fn-session {
        color: var(--faint);
        font-family: Consolas, "Courier New", monospace;
        font-size: .7rem;
        overflow-wrap: anywhere;
    }
    .fn-empty-note {
        color: var(--muted);
        border-left: 3px solid var(--accent);
        padding: .15rem 0 .15rem .85rem;
        margin-top: 1.25rem;
        max-width: 560px;
        line-height: 1.5;
    }
    [data-testid="stChatMessage"] {
        background: transparent;
        border-bottom: 1px solid var(--line-soft);
        padding: 1.35rem .25rem;
        gap: .9rem;
    }
    [data-testid="stChatMessage"] p,
    [data-testid="stChatMessage"] li { line-height: 1.68; }
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] {
        color: var(--text);
        font-size: 1.01rem;
    }
    [data-testid="stChatInput"] {
        border: 1px solid #465045;
        border-radius: var(--radius-surface);
        background: var(--surface-strong);
        box-shadow: 0 16px 44px rgba(6, 10, 7, .38);
    }
    [data-testid="stChatInput"] textarea {
        color: var(--text) !important;
        caret-color: var(--accent) !important;
        opacity: 1 !important;
    }
    [data-testid="stChatInput"] textarea::placeholder {
        color: var(--muted) !important;
        opacity: 1 !important;
    }
    [data-testid="stChatInput"] button,
    [data-testid="stChatInput"] button span {
        color: var(--text) !important;
    }
    [data-testid="stBottomBlockContainer"] {
        background: var(--page);
        padding-top: 2rem;
    }
    div[data-testid="stExpander"] {
        background: var(--surface);
        border: 1px solid var(--line-soft);
        border-radius: var(--radius-control);
    }
    div[data-testid="stExpander"] summary,
    div[data-testid="stExpander"] summary p,
    div[data-testid="stExpander"] summary span {
        color: var(--text) !important;
        opacity: 1 !important;
    }
    div[data-testid="stStatusWidget"] {
        border: 1px solid var(--line);
        border-radius: var(--radius-surface);
        background: var(--surface);
    }
    div[data-testid="stStatusWidget"] p,
    div[data-testid="stStatusWidget"] span {
        color: var(--text);
    }
    div[data-testid="stMetric"] {
        background: transparent;
        border: 0;
        padding: .2rem 0;
    }
    div[data-testid="stMetricValue"] { color: var(--accent); }
    .stButton > button {
        min-height: 42px;
        border-radius: var(--radius-control);
        border: 1px solid var(--line);
        color: var(--text);
        background: var(--surface);
        font-weight: 700;
        transition: transform .16s ease, border-color .16s ease, background .16s ease;
    }
    .stButton > button p,
    .stButton > button span {
        color: inherit !important;
        opacity: 1 !important;
    }
    .stButton > button:hover {
        border-color: #71823f;
        color: var(--text);
        background: var(--surface-strong);
    }
    .stButton > button:active { transform: translateY(1px); }
    .stButton > button[kind="primary"] {
        color: var(--accent-ink);
        background: var(--accent);
        border-color: var(--accent);
    }
    .stButton > button p { white-space: nowrap; }
    .stTextInput input, .stTextArea textarea {
        color: var(--text) !important;
        background: var(--surface) !important;
        border-color: var(--line) !important;
    }
    .stTextInput input::placeholder, .stTextArea textarea::placeholder {
        color: var(--muted) !important;
        opacity: 1;
    }
    [data-baseweb="select"] > div,
    [data-baseweb="base-input"] {
        background: var(--surface) !important;
        color: var(--text) !important;
        border-color: var(--line) !important;
    }
    [data-baseweb="select"] span,
    [data-baseweb="popover"] li,
    [role="option"] {
        color: var(--text) !important;
    }
    [data-testid="stSlider"] p,
    [data-testid="stSlider"] span,
    [data-testid="stToggle"] p,
    [data-testid="stToggle"] span {
        color: var(--text) !important;
        opacity: 1 !important;
    }
    a { color: var(--accent); }
    code { color: #d9eba8 !important; }
    @media (max-width: 760px) {
        .block-container { padding: .7rem 1rem 7rem; }
        .fn-brand { grid-template-columns: 38px 1fr; }
        .fn-mark { width: 38px; height: 38px; }
        .fn-live { display: none; }
        .fn-welcome { min-height: 245px; padding-top: .6rem; }
        .fn-welcome h1 { font-size: 2.8rem; }
    }
    @media (prefers-reduced-motion: reduce) {
        * { animation: none !important; transition: none !important; scroll-behavior: auto !important; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def make_transcript_id() -> str:
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    return f"{VERSION}_{PROVIDER}_chat_{timestamp}"


@st.cache_data(show_spinner=False)
def load_artifacts() -> tuple[str, list[dict[str, Any]]]:
    prompt = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    declarations = load_tool_declarations(TOOLS_PATH)
    return prompt, to_openai_tools(declarations)


def latest_eval_summaries() -> tuple[dict[str, Any], dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for path in sorted(RUNS_DIR.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        suite = payload.get("suite")
        if suite in {"base", "group"}:
            latest[suite] = payload
    return latest.get("base", {}), latest.get("group", {})


def initialize_session() -> None:
    artifact = build_artifact_version(VERSION, SYSTEM_PROMPT_PATH, TOOLS_PATH)
    defaults = {
        "history": [],
        "turns": [],
        "transcript_id": make_transcript_id(),
        "artifact": artifact_version_dict(artifact),
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_session() -> None:
    for key in ["history", "turns", "transcript_id", "artifact", "created_at", "queued_prompt"]:
        st.session_state.pop(key, None)


def queue_prompt(prompt: str) -> None:
    st.session_state.queued_prompt = prompt


def transcript_path() -> Path:
    return TRANSCRIPTS_DIR / f"{st.session_state.transcript_id}.transcript.json"


def persist_transcript(model: str | None, history_window: int, max_rounds: int) -> None:
    transcript = {
        "transcript_id": st.session_state.transcript_id,
        **st.session_state.artifact,
        "provider": PROVIDER,
        "model": model,
        "system_prompt": str(SYSTEM_PROMPT_PATH.relative_to(ROOT)),
        "tools": str(TOOLS_PATH.relative_to(ROOT)),
        "history_window": history_window,
        "max_tool_rounds": max_rounds,
        "created_at": st.session_state.get("created_at", now_iso()),
        "turns": st.session_state.turns,
    }
    st.session_state.created_at = transcript["created_at"]
    write_transcript(transcript_path(), transcript)


def run_request(
    user_text: str,
    model: str | None,
    history_window: int,
    max_rounds: int,
    on_progress: Callable[[str, dict[str, Any]], None] | None,
) -> dict[str, Any]:
    system_prompt, openai_tools = load_artifacts()
    messages = [
        {"role": "system", "content": system_prompt},
        *trim_history(st.session_state.history, history_window),
        {"role": "user", "content": user_text},
    ]
    turn: dict[str, Any] = {
        "turn_index": len(st.session_state.turns) + 1,
        "started_at": now_iso(),
        "user": user_text,
        "status": "started",
        "assistant_text": None,
        "rounds": [],
        "tool_events": [],
        "evidence": [],
    }
    try:
        provider = make_provider(PROVIDER)
        result = run_model_tool_loop(
            provider=provider,
            messages=messages,
            tools=openai_tools,
            model=model or None,
            max_tool_rounds=max_rounds,
            on_progress=on_progress,
        )
        turn.update(result)
        answer = result.get("assistant_text") or "Không có nội dung trả lời."
        st.session_state.history.extend([
            {"role": "user", "content": user_text},
            {"role": "assistant", "content": answer},
        ])
    except Exception as exc:
        turn.update({
            "status": "provider_error",
            "error": f"{type(exc).__name__}: {exc}",
            "assistant_text": "Mình chưa thể hoàn tất lượt này. Hãy thử lại sau khi kiểm tra provider.",
        })
    turn["ended_at"] = now_iso()
    st.session_state.turns.append(turn)
    persist_transcript(model, history_window, max_rounds)
    return turn


def render_sources(evidence: list[dict[str, Any]]) -> None:
    if not evidence:
        return
    with st.expander(f"{len(evidence)} nguồn đã kiểm tra", expanded=False):
        for item in evidence[:10]:
            title = html.escape(str(item.get("title") or "Nguồn dữ liệu"))
            url = html.escape(str(item.get("url") or ""), quote=True)
            source = html.escape(str(item.get("source") or "Nguồn công khai"))
            tool = html.escape(TOOL_LABELS.get(str(item.get("tool")), str(item.get("tool") or "Tool")))
            published_date = html.escape(str(item.get("published_date") or ""))
            backend = html.escape(str(item.get("backend") or ""))
            metadata = [source, tool]
            if published_date:
                metadata.append(published_date)
            if backend:
                metadata.append(backend)
            title_html = f'<a href="{url}" target="_blank" rel="noopener noreferrer">{title}</a>' if url else title
            st.markdown(
                f'<div class="fn-source">{title_html}<div class="fn-source-meta">{" | ".join(metadata)}</div></div>',
                unsafe_allow_html=True,
            )


def render_tool_usage(events: list[dict[str, Any]]) -> None:
    usage = tool_usage_counts(events)
    if usage:
        chips = []
        for name, count in usage:
            safe_name = html.escape(name)
            safe_label = html.escape(TOOL_LABELS.get(name, name))
            count_text = f" ×{count}" if count > 1 else ""
            chips.append(f'<span class="fn-tool-chip">{safe_label} · {safe_name}{count_text}</span>')
    else:
        chips = ['<span class="fn-tool-chip">Không sử dụng công cụ</span>']
    st.markdown(
        '<div class="fn-tool-usage"><span class="fn-tool-usage-label">Công cụ đã sử dụng</span>'
        + "".join(chips)
        + "</div>",
        unsafe_allow_html=True,
    )


def render_debug(turn: dict[str, Any]) -> None:
    with st.expander("Chi tiết kỹ thuật", expanded=False):
        st.caption(f"Trạng thái: {turn.get('status', 'unknown')}")
        for round_item in turn.get("rounds", []):
            stage = round_item.get("stage", "planning")
            st.markdown(f"**Vòng {round_item.get('round')} | {stage}**")
            for call in round_item.get("tool_calls", []):
                st.markdown(f"`{call.get('name')}`")
                st.json(call.get("args", {}), expanded=False)
            for event in round_item.get("tool_results", []):
                result = event.get("result", {})
                if isinstance(result, dict) and result.get("error"):
                    st.error(f"{event.get('tool')}: {result.get('error')}")
                st.json(result, expanded=False)


def render_turn(turn: dict[str, Any], show_debug: bool) -> None:
    with st.chat_message("user", avatar=":material/person:"):
        st.markdown(turn.get("user", ""))
    with st.chat_message("assistant", avatar=":material/sports_soccer:"):
        status = turn.get("status", "unknown")
        if status == "waiting_for_user":
            st.caption("Cần bạn bổ sung thông tin")
        elif status == "provider_error":
            st.error(turn.get("assistant_text", "Lỗi provider"))
            render_tool_usage(turn.get("tool_events") or [])
            if show_debug:
                render_debug(turn)
            return
        st.markdown(turn.get("assistant_text") or "Không có phản hồi.")
        render_tool_usage(turn.get("tool_events") or [])
        render_sources(turn.get("evidence") or [])
        if show_debug:
            render_debug(turn)


initialize_session()
artifact = st.session_state.artifact

with st.sidebar:
    st.markdown("### Football News VAR")
    st.caption("Chatbot thông tin bóng đá có kiểm chứng")
    st.button(
        "Cuộc trò chuyện mới",
        type="primary",
        use_container_width=True,
        on_click=reset_session,
    )
    st.divider()
    st.markdown("**Gợi ý nhanh**")
    for label, prompt_text in QUICK_PROMPTS:
        st.button(
            label,
            key=f"side_{label}",
            use_container_width=True,
            on_click=queue_prompt,
            args=(prompt_text,),
        )
    st.divider()
    show_debug = st.toggle("Chế độ chuyên gia", value=False)
    with st.expander("Cài đặt hội thoại", expanded=False):
        model_input = st.text_input("Model override", value="", placeholder="Model mặc định")
        history_window = st.slider("Ngữ cảnh hội thoại", 1, 10, 5)
        max_rounds = st.slider("Vòng tool tối đa", 2, 6, 4)
    base_run, group_run = latest_eval_summaries()
    with st.expander("Chất lượng và phiên", expanded=False):
        if base_run:
            summary = base_run.get("summary", {})
            st.caption(f"Base eval gần nhất: {summary.get('passed_cases')}/{summary.get('total_cases')}")
        if group_run:
            summary = group_run.get("summary", {})
            st.caption(f"Group eval gần nhất: {summary.get('passed_cases')}/{summary.get('total_cases')}")
        st.markdown("**Artifact**")
        st.markdown(f'<div class="fn-session">{html.escape(artifact["artifact_version"])}</div>', unsafe_allow_html=True)
        st.markdown("**Transcript**")
        st.markdown(f'<div class="fn-session">{html.escape(st.session_state.transcript_id)}</div>', unsafe_allow_html=True)

st.markdown(
    """
    <header class="fn-brand">
      <div class="fn-mark">FV</div>
      <div>
        <div class="fn-brand-name">Football News VAR</div>
        <div class="fn-brand-sub">Tìm nguồn, kiểm tra chéo, trả lời bằng tiếng Việt</div>
      </div>
      <div class="fn-live">OpenRouter đang hoạt động</div>
    </header>
    """,
    unsafe_allow_html=True,
)

if not st.session_state.turns:
    st.markdown(
        """
        <section class="fn-welcome">
          <h1>Hỏi gì về<br>bóng đá?</h1>
          <p>Tin mới, chuyển nhượng, cầu thủ và nguồn tin. Mỗi câu trả lời đều cho biết đã kiểm tra những gì.</p>
          <div class="fn-empty-note">Bạn có thể hỏi trực tiếp, dán URL bài báo hoặc cung cấp tài khoản mạng xã hội cần kiểm tra.</div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="fn-section-title">Bắt đầu nhanh</div>', unsafe_allow_html=True)
    quick_columns = st.columns(2, gap="small")
    for index, (label, prompt_text) in enumerate(QUICK_PROMPTS):
        with quick_columns[index % 2]:
            st.button(
                label,
                key=f"main_{label}",
                use_container_width=True,
                on_click=queue_prompt,
                args=(prompt_text,),
            )
else:
    for chat_turn in st.session_state.turns:
        render_turn(chat_turn, show_debug)

typed_prompt = st.chat_input("Hỏi về tin mới, cầu thủ, CLB hoặc dán một đường link...")
queued_prompt = st.session_state.pop("queued_prompt", None)
request_text = typed_prompt or queued_prompt

if request_text:
    with st.status("Đang hiểu câu hỏi...", expanded=True) as pipeline_status:
        def update_progress(stage: str, payload: dict[str, Any]) -> None:
            if stage == "planning":
                pipeline_status.update(label="Đang chọn nguồn phù hợp...", state="running")
            elif stage == "tool_started":
                tool_name = str(payload.get("tool") or "tool")
                pipeline_status.update(label=f"{TOOL_LABELS.get(tool_name, tool_name)}...", state="running")
            elif stage == "tool_finished":
                tool_name = str(payload.get("tool") or "tool")
                count = payload.get("item_count", 0)
                if payload.get("ok"):
                    st.write(f"{TOOL_LABELS.get(tool_name, tool_name)}: nhận {count} kết quả")
                else:
                    st.write(f"{TOOL_LABELS.get(tool_name, tool_name)}: có lỗi, đang đánh giá phương án tiếp theo")
            elif stage == "synthesis":
                pipeline_status.update(label="Đang kiểm tra chéo và tổng hợp tiếng Việt...", state="running")
            elif stage == "waiting_for_user":
                pipeline_status.update(label="Cần thêm thông tin từ bạn", state="complete")
            elif stage == "complete":
                pipeline_status.update(label="Đã kiểm tra và tổng hợp", state="complete")

        completed_turn = run_request(
            request_text,
            model_input.strip() or None,
            history_window,
            max_rounds,
            update_progress,
        )
        if completed_turn.get("status") == "provider_error":
            pipeline_status.update(label="Không thể hoàn tất lượt này", state="error")
    st.rerun()
