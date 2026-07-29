import { useState } from "react";
import { api } from "../api";
import type { AirportScheduleFlight, AirportScheduleResult } from "../types";
import { Card, CardHeader } from "../components/Card";
import { StatusBadge } from "../components/StatusBadge";
import { SourceTag } from "../components/SourceTag";
import { Spinner, ErrorNote } from "../components/Spinner";

type Direction = "departures" | "arrivals";

function fmtLocal(value: string | null): string {
  if (!value) return "—";
  return value.replace(" ", " · ").replace("Z", "");
}

function FlightRow({ flight, direction }: { flight: AirportScheduleFlight; direction: Direction }) {
  return (
    <tr className="border-t border-[var(--color-border)] text-sm">
      <td className="px-4 py-3 font-medium text-slate-100">{flight.number}</td>
      <td className="px-4 py-3 text-slate-300">{flight.airline ?? "—"}</td>
      <td className="px-4 py-3 text-slate-300">
        {direction === "departures" ? "to " : "from "}
        <span className="font-medium text-slate-100">{flight.other_airport_iata ?? "—"}</span>
      </td>
      <td className="px-4 py-3 text-slate-300">{fmtLocal(flight.scheduled_local)}</td>
      <td className="px-4 py-3 text-slate-400">
        {flight.terminal ? `T${flight.terminal}` : "—"}
        {flight.gate ? ` / Gate ${flight.gate}` : ""}
      </td>
      <td className="px-4 py-3">
        <StatusBadge status={flight.status} />
      </td>
    </tr>
  );
}

export default function AirportBoardPage() {
  const [airport, setAirport] = useState("");
  const [hours, setHours] = useState(6);
  const [direction, setDirection] = useState<Direction>("departures");
  const [result, setResult] = useState<AirportScheduleResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function search(dir: Direction = direction) {
    if (!airport.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res =
        dir === "departures"
          ? await api.getAirportDepartures(airport.trim().toUpperCase(), hours)
          : await api.getAirportArrivals(airport.trim().toUpperCase(), hours);
      if (res.error) {
        setError(res.message || res.error);
        setResult(null);
        return;
      }
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  function switchDirection(dir: Direction) {
    setDirection(dir);
    if (airport.trim()) search(dir);
  }

  return (
    <div className="mx-auto max-w-4xl px-6 py-6">
      <h1 className="text-lg font-semibold text-slate-100">Airport Board</h1>
      <p className="mt-1 text-sm text-[var(--color-muted)]">Xem lịch khởi hành / hạ cánh của một sân bay trong một khung giờ.</p>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          search();
        }}
        className="mt-5 flex flex-wrap items-center gap-2"
      >
        <input
          value={airport}
          onChange={(e) => setAirport(e.target.value.toUpperCase())}
          placeholder="HAN"
          className="w-32 rounded-xl border border-[var(--color-border)] bg-[var(--color-card)] px-3 py-2.5 text-sm text-slate-100 outline-none focus:border-sky-400/50"
        />
        <select
          value={hours}
          onChange={(e) => setHours(Number(e.target.value))}
          className="rounded-xl border border-[var(--color-border)] bg-[var(--color-card)] px-3 py-2.5 text-sm text-slate-100 outline-none focus:border-sky-400/50"
        >
          {[2, 4, 6, 8, 12].map((h) => (
            <option key={h} value={h}>
              next {h}h
            </option>
          ))}
        </select>
        <button
          type="submit"
          disabled={loading || !airport.trim()}
          className="rounded-xl bg-sky-500 px-4 py-2.5 text-sm font-medium text-white disabled:opacity-40"
        >
          {loading ? <Spinner /> : "Load board"}
        </button>
      </form>

      <div className="mt-3 text-xs text-[var(--color-muted)]">
        Mặc định cửa sổ tính từ "bây giờ"; nếu API báo lỗi giới hạn plan cho khung real-time, hãy thử lại sau ít phút hoặc dùng chat để chỉ định khung giờ tương lai cụ thể.
      </div>

      <Card className="mt-5">
        <CardHeader
          title={airport ? `${airport} — ${direction}` : "Airport board"}
          subtitle={result ? `${result.flight_count} flight(s) in window` : undefined}
          right={
            <div className="flex overflow-hidden rounded-lg border border-[var(--color-border)] text-xs">
              <button
                onClick={() => switchDirection("departures")}
                className={`px-3 py-1.5 ${direction === "departures" ? "bg-sky-400/15 text-sky-300" : "text-slate-400 hover:text-slate-200"}`}
              >
                Departures
              </button>
              <button
                onClick={() => switchDirection("arrivals")}
                className={`px-3 py-1.5 ${direction === "arrivals" ? "bg-sky-400/15 text-sky-300" : "text-slate-400 hover:text-slate-200"}`}
              >
                Arrivals
              </button>
            </div>
          }
        />
        <div className="px-5 py-4">
          {error && <ErrorNote message={error} />}
          {!error && !result && <p className="text-sm text-[var(--color-muted)]">Nhập mã sân bay (IATA) rồi bấm "Load board".</p>}
          {!error && result && result.flights.length === 0 && (
            <p className="text-sm text-[var(--color-muted)]">Không có chuyến bay nào trong khung giờ này.</p>
          )}
          {!error && result && result.flights.length > 0 && (
            <div className="-mx-5 overflow-x-auto">
              <table className="w-full min-w-[640px]">
                <thead>
                  <tr className="text-left text-xs uppercase tracking-wide text-[var(--color-muted)]">
                    <th className="px-4 py-2">Flight</th>
                    <th className="px-4 py-2">Airline</th>
                    <th className="px-4 py-2">Route</th>
                    <th className="px-4 py-2">Scheduled (local)</th>
                    <th className="px-4 py-2">Gate</th>
                    <th className="px-4 py-2">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {result.flights.map((f, i) => (
                    <FlightRow key={i} flight={f} direction={direction} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </Card>
      {result && (
        <div className="mt-3">
          <SourceTag source={result.source} retrievedAt={result.retrieved_at} />
        </div>
      )}
    </div>
  );
}
