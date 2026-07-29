import { useState } from "react";
import { api } from "../api";
import type { FlightStatusMatch, FlightStatusLegSide } from "../types";
import { Card, CardHeader } from "../components/Card";
import { StatusBadge } from "../components/StatusBadge";
import { SourceTag } from "../components/SourceTag";
import { Spinner, ErrorNote } from "../components/Spinner";

function fmtUtc(value: string | null): string {
  if (!value) return "—";
  const d = new Date(value.replace(" ", "T").replace("Z", "") + "Z");
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) + " UTC";
}

function LegSide({ label, side }: { label: string; side: FlightStatusLegSide }) {
  const delayed = (side.delay_minutes ?? 0) > 0;
  return (
    <div className="flex-1">
      <div className="text-[11px] uppercase tracking-wide text-[var(--color-muted)]">{label}</div>
      <div className="mt-1 text-2xl font-semibold text-slate-100">{side.airport_iata ?? "—"}</div>
      <div className="mt-2 space-y-1 text-sm">
        <div className="text-slate-300">
          Scheduled: <span className="text-slate-100">{fmtUtc(side.scheduled_utc)}</span>
        </div>
        {side.revised_utc && side.revised_utc !== side.scheduled_utc && (
          <div className={delayed ? "text-amber-300" : "text-slate-300"}>
            Revised: <span className="font-medium">{fmtUtc(side.revised_utc)}</span>
          </div>
        )}
        {delayed && <div className="text-amber-300">Delay: {side.delay_minutes} min</div>}
        <div className="text-[var(--color-muted)]">
          {side.terminal ? `Terminal ${side.terminal}` : "Terminal —"}
          {side.gate ? ` · Gate ${side.gate}` : ""}
        </div>
      </div>
    </div>
  );
}

function FlightCard({ match }: { match: FlightStatusMatch }) {
  return (
    <Card>
      <CardHeader
        title={`${match.number}${match.airline ? ` · ${match.airline}` : ""}`}
        right={<StatusBadge status={match.status} />}
      />
      <div className="flex items-center gap-4 px-5 py-5">
        <LegSide label="Departure" side={match.departure} />
        <div className="flex flex-col items-center px-2 text-[var(--color-muted)]">
          <div className="text-lg">✈️</div>
          <div className="mt-1 h-px w-16 bg-[var(--color-border)]" />
        </div>
        <LegSide label="Arrival" side={match.arrival} />
      </div>
    </Card>
  );
}

export default function TrackFlightPage() {
  const [flightNumber, setFlightNumber] = useState("");
  const [date, setDate] = useState("");
  const [matches, setMatches] = useState<FlightStatusMatch[] | null>(null);
  const [meta, setMeta] = useState<{ source?: string; retrieved_at?: string }>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function search() {
    if (!flightNumber.trim()) return;
    setLoading(true);
    setError(null);
    setMatches(null);
    try {
      const res = await api.getFlightStatus(flightNumber.trim(), date || undefined);
      if (res.error) {
        setError(res.message || res.error);
        return;
      }
      setMatches(res.matches);
      setMeta({ source: res.source, retrieved_at: res.retrieved_at });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-6 py-6">
      <h1 className="text-lg font-semibold text-slate-100">Track Flight</h1>
      <p className="mt-1 text-sm text-[var(--color-muted)]">Nhập số hiệu chuyến bay để xem trạng thái real-time.</p>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          search();
        }}
        className="mt-5 flex flex-wrap items-center gap-2"
      >
        <input
          value={flightNumber}
          onChange={(e) => setFlightNumber(e.target.value.toUpperCase())}
          placeholder="VN7"
          className="w-40 rounded-xl border border-[var(--color-border)] bg-[var(--color-card)] px-3 py-2.5 text-sm text-slate-100 outline-none focus:border-sky-400/50"
        />
        <input
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          className="rounded-xl border border-[var(--color-border)] bg-[var(--color-card)] px-3 py-2.5 text-sm text-slate-100 outline-none focus:border-sky-400/50"
        />
        <button
          type="submit"
          disabled={loading || !flightNumber.trim()}
          className="rounded-xl bg-sky-500 px-4 py-2.5 text-sm font-medium text-white disabled:opacity-40"
        >
          {loading ? <Spinner /> : "Track"}
        </button>
      </form>

      <div className="mt-6 space-y-4">
        {error && <ErrorNote message={error} />}
        {matches && matches.length === 0 && (
          <p className="text-sm text-[var(--color-muted)]">Không tìm thấy chuyến bay khớp.</p>
        )}
        {matches?.map((m, i) => <FlightCard key={i} match={m} />)}
        {matches && matches.length > 0 && <SourceTag source={meta.source} retrievedAt={meta.retrieved_at} />}
      </div>
    </div>
  );
}
