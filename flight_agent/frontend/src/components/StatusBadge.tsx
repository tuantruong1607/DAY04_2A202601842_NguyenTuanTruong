const TONE: Record<string, { bg: string; text: string; dot: string }> = {
  ok: { bg: "bg-emerald-400/10", text: "text-emerald-300", dot: "bg-emerald-400" },
  warn: { bg: "bg-amber-400/10", text: "text-amber-300", dot: "bg-amber-400" },
  danger: { bg: "bg-rose-400/10", text: "text-rose-300", dot: "bg-rose-400" },
  neutral: { bg: "bg-slate-400/10", text: "text-slate-300", dot: "bg-slate-400" },
  accent: { bg: "bg-sky-400/10", text: "text-sky-300", dot: "bg-sky-400" },
};

function toneForStatus(status: string | null | undefined): keyof typeof TONE {
  const s = (status || "").toLowerCase();
  if (["cancelled", "canceled", "diverted"].includes(s)) return "danger";
  if (["delayed", "late"].includes(s)) return "warn";
  if (["arrived", "landed", "departed", "en-route", "enroute", "active"].includes(s)) return "ok";
  if (["expected", "scheduled", "boarding", "gate closed", "gateclosed"].includes(s)) return "accent";
  return "neutral";
}

export function StatusBadge({ status }: { status: string | null | undefined }) {
  const tone = TONE[toneForStatus(status)];
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${tone.bg} ${tone.text}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${tone.dot}`} />
      {status || "Unknown"}
    </span>
  );
}
