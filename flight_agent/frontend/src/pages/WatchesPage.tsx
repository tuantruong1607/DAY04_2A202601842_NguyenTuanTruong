import { useEffect, useState } from "react";
import { api } from "../api";
import type { Watch } from "../types";
import { AirportInput } from "../components/AirportInput";
import { Card, CardHeader } from "../components/Card";
import { Spinner, ErrorNote } from "../components/Spinner";

function WatchRow({ watch, onCancel }: { watch: Watch; onCancel: (id: string) => void }) {
  const isPrice = watch.type === "price";
  return (
    <div className="flex items-center justify-between border-t border-[var(--color-border)] px-5 py-3 text-sm">
      <div>
        <div className="font-medium text-slate-100">
          {isPrice ? (
            <>
              {watch.origin} → {watch.destination} <span className="text-[var(--color-muted)]">· {watch.departure_date}</span>
            </>
          ) : (
            <>
              Flight {watch.flight_number}
              {watch.date ? <span className="text-[var(--color-muted)]"> · {watch.date}</span> : null}
            </>
          )}
        </div>
        <div className="mt-0.5 text-xs text-[var(--color-muted)]">
          {isPrice ? (
            <>
              max {watch.max_price ?? "—"} {watch.currency} · last seen {watch.last_price ?? "—"}{" "}
              {watch.last_checked_at ? `(${new Date(watch.last_checked_at).toLocaleString()})` : ""}
            </>
          ) : (
            <>
              notify on: {watch.notify_on?.join(", ")} · last status: {watch.last_status ?? "unchecked"}
            </>
          )}
        </div>
      </div>
      <div className="flex items-center gap-3">
        <span className="rounded-full bg-white/5 px-2 py-1 text-[10px] uppercase tracking-wide text-[var(--color-muted)]">
          {watch.id}
        </span>
        <button onClick={() => onCancel(watch.id)} className="text-xs text-rose-300 hover:text-rose-200">
          Cancel
        </button>
      </div>
    </div>
  );
}

export default function WatchesPage() {
  const [watches, setWatches] = useState<Watch[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [alerts, setAlerts] = useState<string[] | null>(null);
  const [checking, setChecking] = useState(false);

  const [tab, setTab] = useState<"price" | "status">("price");

  // price watch form
  const [pOrigin, setPOrigin] = useState("");
  const [pDestination, setPDestination] = useState("");
  const [pDate, setPDate] = useState("");
  const [pMaxPrice, setPMaxPrice] = useState("");
  const [pCurrency, setPCurrency] = useState("USD");

  // status watch form
  const [sFlightNumber, setSFlightNumber] = useState("");
  const [sDate, setSDate] = useState("");

  async function refresh() {
    setLoading(true);
    try {
      setWatches(await api.listWatches());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function createPriceWatch() {
    if (!pOrigin || !pDestination || !pDate) return;
    await api.createPriceWatch({
      origin: pOrigin,
      destination: pDestination,
      departure_date: pDate,
      currency: pCurrency,
      max_price: pMaxPrice ? Number(pMaxPrice) : null,
    });
    setPOrigin("");
    setPDestination("");
    setPDate("");
    setPMaxPrice("");
    refresh();
  }

  async function createStatusWatch() {
    if (!sFlightNumber) return;
    await api.createStatusWatch({ flight_number: sFlightNumber, date: sDate || null });
    setSFlightNumber("");
    setSDate("");
    refresh();
  }

  async function cancel(id: string) {
    await api.cancelWatch(id);
    refresh();
  }

  async function checkNow() {
    setChecking(true);
    setAlerts(null);
    try {
      const res = await api.checkWatches();
      setAlerts(res.alerts.length ? res.alerts : ["Không có cảnh báo mới (không thay đổi đáng kể)."]);
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setChecking(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-6 py-6">
      <h1 className="text-lg font-semibold text-slate-100">Watches</h1>
      <p className="mt-1 text-sm text-[var(--color-muted)]">
        Theo dõi giá vé hoặc trạng thái chuyến bay. Bấm "Check now" để đánh giá lại — chỉ báo khi có thay đổi thật, không lặp lại cảnh báo cũ.
      </p>

      <Card className="mt-5">
        <CardHeader
          title="Tạo watch mới"
          right={
            <div className="flex overflow-hidden rounded-lg border border-[var(--color-border)] text-xs">
              <button
                onClick={() => setTab("price")}
                className={`px-3 py-1.5 ${tab === "price" ? "bg-sky-400/15 text-sky-300" : "text-slate-400"}`}
              >
                Price
              </button>
              <button
                onClick={() => setTab("status")}
                className={`px-3 py-1.5 ${tab === "status" ? "bg-sky-400/15 text-sky-300" : "text-slate-400"}`}
              >
                Status
              </button>
            </div>
          }
        />
        <div className="p-4">
          {tab === "price" ? (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                createPriceWatch();
              }}
              className="space-y-3"
            >
              <div className="flex flex-wrap gap-3">
                <AirportInput label="From" value={pOrigin} onChange={setPOrigin} placeholder="HAN" />
                <AirportInput label="To" value={pDestination} onChange={setPDestination} placeholder="SGN" />
              </div>
              <div className="flex flex-wrap items-end gap-3">
                <div>
                  <label className="mb-1 block text-[11px] uppercase tracking-wide text-[var(--color-muted)]">Departure</label>
                  <input
                    type="date"
                    value={pDate}
                    onChange={(e) => setPDate(e.target.value)}
                    className="rounded-xl border border-[var(--color-border)] bg-[var(--color-panel)] px-3 py-2.5 text-sm text-slate-100 outline-none"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-[11px] uppercase tracking-wide text-[var(--color-muted)]">Alert below</label>
                  <input
                    type="number"
                    value={pMaxPrice}
                    onChange={(e) => setPMaxPrice(e.target.value)}
                    placeholder="60"
                    className="w-28 rounded-xl border border-[var(--color-border)] bg-[var(--color-panel)] px-3 py-2.5 text-sm text-slate-100 outline-none"
                  />
                </div>
                <select
                  value={pCurrency}
                  onChange={(e) => setPCurrency(e.target.value)}
                  className="rounded-xl border border-[var(--color-border)] bg-[var(--color-panel)] px-3 py-2.5 text-sm text-slate-100 outline-none"
                >
                  {["USD", "VND", "EUR"].map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
                <button
                  type="submit"
                  disabled={!pOrigin || !pDestination || !pDate}
                  className="ml-auto rounded-xl bg-sky-500 px-4 py-2.5 text-sm font-medium text-white disabled:opacity-40"
                >
                  Create watch
                </button>
              </div>
            </form>
          ) : (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                createStatusWatch();
              }}
              className="flex flex-wrap items-end gap-3"
            >
              <div>
                <label className="mb-1 block text-[11px] uppercase tracking-wide text-[var(--color-muted)]">Flight number</label>
                <input
                  value={sFlightNumber}
                  onChange={(e) => setSFlightNumber(e.target.value.toUpperCase())}
                  placeholder="VN7"
                  className="w-32 rounded-xl border border-[var(--color-border)] bg-[var(--color-panel)] px-3 py-2.5 text-sm text-slate-100 outline-none"
                />
              </div>
              <div>
                <label className="mb-1 block text-[11px] uppercase tracking-wide text-[var(--color-muted)]">Date (optional)</label>
                <input
                  type="date"
                  value={sDate}
                  onChange={(e) => setSDate(e.target.value)}
                  className="rounded-xl border border-[var(--color-border)] bg-[var(--color-panel)] px-3 py-2.5 text-sm text-slate-100 outline-none"
                />
              </div>
              <button
                type="submit"
                disabled={!sFlightNumber}
                className="ml-auto rounded-xl bg-sky-500 px-4 py-2.5 text-sm font-medium text-white disabled:opacity-40"
              >
                Create watch
              </button>
            </form>
          )}
        </div>
      </Card>

      <Card className="mt-5">
        <CardHeader
          title="Active watches"
          subtitle={`${watches.length} watch(es)`}
          right={
            <button
              onClick={checkNow}
              disabled={checking || watches.length === 0}
              className="flex items-center gap-1.5 rounded-lg bg-sky-400/15 px-3 py-1.5 text-xs font-medium text-sky-300 disabled:opacity-40"
            >
              {checking && <Spinner />} Check now
            </button>
          }
        />
        {error && (
          <div className="p-4">
            <ErrorNote message={error} />
          </div>
        )}
        {loading && <div className="p-4 text-sm text-[var(--color-muted)]">Loading…</div>}
        {!loading && watches.length === 0 && <div className="p-4 text-sm text-[var(--color-muted)]">Chưa có watch nào.</div>}
        {watches.map((w) => (
          <WatchRow key={w.id} watch={w} onCancel={cancel} />
        ))}
      </Card>

      {alerts && (
        <Card className="mt-5">
          <CardHeader title="Kết quả check" />
          <ul className="space-y-1 p-4 text-sm text-slate-200">
            {alerts.map((a, i) => (
              <li key={i}>• {a}</li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}
