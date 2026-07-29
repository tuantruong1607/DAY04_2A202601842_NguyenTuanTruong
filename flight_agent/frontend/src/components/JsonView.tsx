import { useState } from "react";

function escapeHtml(raw: string): string {
  return raw.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// Regex-based JSON syntax highlighter: escape HTML first, then wrap tokens
// in <span>s. Safe because the regex runs on already-escaped text, so it
// can never reintroduce a raw "<"/">" from untrusted content (tool args or
// results can contain arbitrary user-supplied strings).
function highlight(json: string): string {
  const escaped = escapeHtml(json);
  return escaped.replace(
    /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false)\b|\bnull\b|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)/g,
    (match) => {
      let cls = "jv-number";
      if (/^"/.test(match)) {
        cls = /:$/.test(match) ? "jv-key" : "jv-string";
      } else if (/true|false/.test(match)) {
        cls = "jv-boolean";
      } else if (/null/.test(match)) {
        cls = "jv-null";
      }
      return `<span class="${cls}">${match}</span>`;
    },
  );
}

export function JsonView({ data, collapsedByDefault = false }: { data: unknown; collapsedByDefault?: boolean }) {
  const [open, setOpen] = useState(!collapsedByDefault);
  const [copied, setCopied] = useState(false);
  const text = JSON.stringify(data, null, 2) ?? "null";

  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1200);
    } catch {
      // clipboard permission denied — non-critical, just skip the feedback
    }
  }

  return (
    <div className="overflow-hidden rounded-lg border border-[var(--color-border)] bg-black/30">
      <div className="flex items-center justify-between border-b border-[var(--color-border)] bg-black/20 px-2.5 py-1">
        <button
          onClick={() => setOpen((v) => !v)}
          className="flex items-center gap-1.5 text-[11px] font-medium text-[var(--color-muted)] hover:text-slate-200"
        >
          <span className={`inline-block transition-transform ${open ? "rotate-90" : ""}`}>▸</span>
          raw JSON
        </button>
        <button onClick={copy} className="text-[11px] text-[var(--color-muted)] hover:text-sky-300">
          {copied ? "✓ copied" : "copy"}
        </button>
      </div>
      {open && (
        <pre className="jv-pre max-h-72 overflow-auto whitespace-pre-wrap break-all px-3 py-2 text-[11px] leading-relaxed">
          <code dangerouslySetInnerHTML={{ __html: highlight(text) }} />
        </pre>
      )}
    </div>
  );
}
