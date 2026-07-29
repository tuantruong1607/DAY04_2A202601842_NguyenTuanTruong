import { useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api";
import type { AnalyzePriceHistoryResult, ComparePick, PriceOffer } from "../types";
import { AirportInput } from "../components/AirportInput";
import { Card, CardHeader } from "../components/Card";
import { SourceTag } from "../components/SourceTag";
import { Spinner, ErrorNote } from "../components/Spinner";

const PICK_LABEL: Record<string, { title: string; emoji: string; tone: string }> = {
  cheapest: { title: "Rẻ nhất", emoji: "💰", tone: "border-emerald-400/30" },
  most_convenient: { title: "Thuận tiện nhất", emoji: "⚡", tone: "border-sky-400/30" },
  balanced: { title: "Cân bằng", emoji: "⚖️", tone: "border-amber-400/30" },
};

function PickCard({ pick }: { pick: ComparePick }) {
  const meta = PICK_LABEL[pick.label] ?? { title: pick.label, emoji: "✈️", tone: "border-[var(--color-border)]" };
  const leg = pick.legs[0];
  return (
    <Card className={`border-2 ${meta.tone}`}>
      <div className="p-4">
        <div className="flex items-center justify-between">
          <span className="text-sm font-semibold text-slate-100">
            {meta.emoji} {meta.title}
          </span>
          <span className="text-lg font-bold text-slate-100">
            {pick.price} <span className="text-xs font-normal text-[var(--color-muted)]">{pick.currency}</span>
          </span>
        </div>
        <p className="mt-2 text-xs text-[var(--color-muted)]">{pick.reason}</p>
        {leg && (
          <div className="mt-3 flex items-center justify-between text-xs text-slate-300">
            <span>
              {leg.origin} → {leg.destination}
            </span>
            <span>{pick.total_duration_minutes ? `${pick.total_duration_minutes} min` : "—"}</span>
            <span>{pick.total_stops === 0 ? "Direct" : `${pick.total_stops} stop(s)`}</span>
          </div>
        )}
        {pick.carriers.length > 0 && <div className="mt-2 text-xs text-[var(--color-muted)]">{pick.carriers.join(", ")}</div>}
        {pick.flight_numbers.length > 0 && (
          <div className="mt-1 text-xs font-medium text-slate-300">{pick.flight_numbers.join(" · ")}</div>
        )}
      </div>
    </Card>
  );
}

export default function SearchComparePage() {
  const [tripType, setTripType] = useState<"ONE_WAY" | "ROUND_TRIP">("ONE_WAY");
  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");
  const [departureDate, setDepartureDate] = useState("");
  const [returnDate, setReturnDate] = useState("");
  const [maxPrice, setMaxPrice] = useState("");
  const [currency, setCurrency] = useState("USD");

  const [offers, setOffers] = useState<PriceOffer[] | null>(null);
  const [picks, setPicks] = useState<ComparePick[]>([]);
  const [history, setHistory] = useState<AnalyzePriceHistoryResult | null>(null);
  const [meta, setMeta] = useState<{ source?: string; retrieved_at?: string; unparsed?: number }>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAll, setShowAll] = useState(false);

  async function search() {
    if (!origin || !destination || !departureDate) return;
    setLoading(true);
    setError(null);
    setOffers(null);
    setPicks([]);
    setHistory(null);
    try {
      const res = await api.searchFlightPrices({
        trip_type: tripType,
        origin,
        destination,
        departure_date: departureDate,
        return_date: tripType === "ROUND_TRIP" ? returnDate || null : null,
        currency,
        max_price: maxPrice ? Number(maxPrice) : null,
      });
      if (res.error) {
        setError(res.message || res.error);
        return;
      }
      setOffers(res.items);
      setMeta({ source: res.source, retrieved_at: res.retrieved_at, unparsed: res.unparsed_count });

      if (res.items.length >= 2) {
        const cmp = await api.compareFlightOffers(res.items);
        if (!cmp.error) setPicks(cmp.picks);
      }

      const hist = await api.analyzePriceHistory({
        origin,
        destination,
        departure_date: departureDate,
        return_date: tripType === "ROUND_TRIP" ? returnDate || null : null,
        currency,
      });
      if (!hist.error) setHistory(hist);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  const chartData =
    history?.has_history && history.stats.count
      ? // We only have aggregate stats from this endpoint; show min/avg/max as a simple 3-point reference.
        [
          { label: "min", price: history.stats.min_price },
          { label: "avg", price: history.stats.avg_price },
          { label: "max", price: history.stats.max_price },
        ]
      : [];

  const visibleOffers = showAll ? offers ?? [] : (offers ?? []).slice(0, 5);

  return (
    <div className="mx-auto max-w-4xl px-6 py-6">
      <h1 className="text-lg font-semibold text-slate-100">Search &amp; Compare</h1>
      <p className="mt-1 text-sm text-[var(--color-muted)]">Tìm giá vé thật và nhận gợi ý rẻ nhất / thuận tiện nhất / cân bằng.</p>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          search();
        }}
        className="mt-5 space-y-3 rounded-2xl border border-[var(--color-border)] bg-[var(--color-card)] p-4"
      >
        <div className="flex gap-2 text-xs">
          {(["ONE_WAY", "ROUND_TRIP"] as const).map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setTripType(t)}
              className={`rounded-lg px-3 py-1.5 ${
                tripType === t ? "bg-sky-400/15 text-sky-300" : "text-slate-400 hover:text-slate-200"
              }`}
            >
              {t === "ONE_WAY" ? "One-way" : "Round-trip"}
            </button>
          ))}
        </div>

        <div className="flex flex-wrap gap-3">
          <AirportInput label="From" value={origin} onChange={setOrigin} placeholder="HAN" />
          <AirportInput label="To" value={destination} onChange={setDestination} placeholder="SGN" />
        </div>

        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label className="mb-1 block text-[11px] uppercase tracking-wide text-[var(--color-muted)]">Departure</label>
            <input
              type="date"
              value={departureDate}
              onChange={(e) => setDepartureDate(e.target.value)}
              className="rounded-xl border border-[var(--color-border)] bg-[var(--color-panel)] px-3 py-2.5 text-sm text-slate-100 outline-none focus:border-sky-400/50"
            />
          </div>
          {tripType === "ROUND_TRIP" && (
            <div>
              <label className="mb-1 block text-[11px] uppercase tracking-wide text-[var(--color-muted)]">Return</label>
              <input
                type="date"
                value={returnDate}
                onChange={(e) => setReturnDate(e.target.value)}
                className="rounded-xl border border-[var(--color-border)] bg-[var(--color-panel)] px-3 py-2.5 text-sm text-slate-100 outline-none focus:border-sky-400/50"
              />
            </div>
          )}
          <div>
            <label className="mb-1 block text-[11px] uppercase tracking-wide text-[var(--color-muted)]">Budget (optional)</label>
            <input
              type="number"
              value={maxPrice}
              onChange={(e) => setMaxPrice(e.target.value)}
              placeholder="60"
              className="w-28 rounded-xl border border-[var(--color-border)] bg-[var(--color-panel)] px-3 py-2.5 text-sm text-slate-100 outline-none focus:border-sky-400/50"
            />
          </div>
          <div>
            <label className="mb-1 block text-[11px] uppercase tracking-wide text-[var(--color-muted)]">Currency</label>
            <select
              value={currency}
              onChange={(e) => setCurrency(e.target.value)}
              className="rounded-xl border border-[var(--color-border)] bg-[var(--color-panel)] px-3 py-2.5 text-sm text-slate-100 outline-none focus:border-sky-400/50"
            >
              {["USD", "VND", "EUR"].map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>
          <button
            type="submit"
            disabled={loading || !origin || !destination || !departureDate}
            className="ml-auto rounded-xl bg-sky-500 px-5 py-2.5 text-sm font-medium text-white disabled:opacity-40"
          >
            {loading ? <Spinner /> : "Search flights"}
          </button>
        </div>
      </form>

      <div className="mt-6 space-y-5">
        {error && <ErrorNote message={error} />}

        {picks.length > 0 && (
          <div>
            <h2 className="mb-2 text-sm font-semibold text-slate-200">Gợi ý</h2>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              {picks.map((p) => (
                <PickCard key={p.label} pick={p} />
              ))}
            </div>
          </div>
        )}

        {offers && offers.length > 0 && (
          <Card>
            <CardHeader title="Tất cả kết quả" subtitle={`${offers.length} offer(s)${meta.unparsed ? `, ${meta.unparsed} không parse được` : ""}`} />
            <div className="divide-y divide-[var(--color-border)]">
              {visibleOffers.map((offer) => {
                const leg = offer.legs[0];
                return (
                  <div key={offer.itinerary_id} className="flex items-center justify-between px-5 py-3 text-sm">
                    <div className="text-slate-300">
                      {leg ? `${leg.origin} → ${leg.destination}` : "—"}{" "}
                      <span className="text-[var(--color-muted)]">
                        {leg?.carriers.join(", ")} · {leg?.duration_minutes ? `${leg.duration_minutes} min` : "—"} ·{" "}
                        {offer.total_stops === 0 ? "direct" : `${offer.total_stops} stop(s)`}
                        {offer.flight_numbers.length > 0 ? ` · ${offer.flight_numbers.join(" / ")}` : ""}
                      </span>
                    </div>
                    <div className="font-semibold text-slate-100">
                      {offer.price} {offer.currency}
                    </div>
                  </div>
                );
              })}
            </div>
            {offers.length > 5 && (
              <button onClick={() => setShowAll((v) => !v)} className="w-full border-t border-[var(--color-border)] py-2 text-xs text-sky-300 hover:text-sky-200">
                {showAll ? "Show less" : `Show all ${offers.length}`}
              </button>
            )}
          </Card>
        )}

        {offers && offers.length === 0 && <p className="text-sm text-[var(--color-muted)]">Không tìm thấy chuyến bay phù hợp.</p>}

        {history?.has_history && (
          <Card>
            <CardHeader title="Price history" subtitle={`${history.stats.count} lần kiểm tra đã ghi nhận`} />
            <div className="h-48 px-3 py-3">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData}>
                  <CartesianGrid stroke="#232b3a" strokeDasharray="3 3" />
                  <XAxis dataKey="label" stroke="#7c8aa3" fontSize={12} />
                  <YAxis stroke="#7c8aa3" fontSize={12} width={50} />
                  <Tooltip contentStyle={{ background: "#141a26", border: "1px solid #232b3a", borderRadius: 8, fontSize: 12 }} />
                  <Line type="monotone" dataKey="price" stroke="#38bdf8" strokeWidth={2} dot={{ r: 4 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <div className="flex flex-wrap gap-4 border-t border-[var(--color-border)] px-5 py-3 text-xs text-slate-300">
              <span>Min: {history.stats.min_price}</span>
              <span>Avg: {history.stats.avg_price}</span>
              <span>Max: {history.stats.max_price}</span>
              <span>Median: {history.stats.median_price}</span>
              {history.stats.pct_change_first_to_last !== null && (
                <span>Δ first→last: {history.stats.pct_change_first_to_last}%</span>
              )}
            </div>
          </Card>
        )}

        {offers && offers.length > 0 && <SourceTag source={meta.source} retrievedAt={meta.retrieved_at} />}
      </div>
    </div>
  );
}
