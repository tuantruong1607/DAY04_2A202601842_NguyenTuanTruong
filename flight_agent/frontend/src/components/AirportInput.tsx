import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { Airport } from "../types";

export function AirportInput({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (iata: string) => void;
  placeholder?: string;
}) {
  const [query, setQuery] = useState(value);
  const [options, setOptions] = useState<Airport[]>([]);
  const [open, setOpen] = useState(false);
  const timer = useRef<number | undefined>(undefined);

  useEffect(() => setQuery(value), [value]);

  function handleInput(text: string) {
    setQuery(text.toUpperCase());
    onChange(text.toUpperCase());
    window.clearTimeout(timer.current);
    if (text.trim().length < 2) {
      setOptions([]);
      return;
    }
    timer.current = window.setTimeout(async () => {
      try {
        const res = await api.searchAirports(text.trim());
        setOptions(res.items ?? []);
        setOpen(true);
      } catch {
        setOptions([]);
      }
    }, 300);
  }

  return (
    <div className="relative flex-1">
      <label className="mb-1 block text-[11px] uppercase tracking-wide text-[var(--color-muted)]">{label}</label>
      <input
        value={query}
        onChange={(e) => handleInput(e.target.value)}
        onFocus={() => options.length > 0 && setOpen(true)}
        onBlur={() => window.setTimeout(() => setOpen(false), 150)}
        placeholder={placeholder}
        className="w-full rounded-xl border border-[var(--color-border)] bg-[var(--color-card)] px-3 py-2.5 text-sm text-slate-100 outline-none focus:border-sky-400/50"
      />
      {open && options.length > 0 && (
        <div className="absolute z-10 mt-1 w-full overflow-hidden rounded-xl border border-[var(--color-border)] bg-[var(--color-card)] shadow-xl">
          {options.map((opt) => (
            <button
              type="button"
              key={`${opt.iata}-${opt.name}`}
              onMouseDown={() => {
                onChange(opt.iata ?? query);
                setQuery(opt.iata ?? query);
                setOpen(false);
              }}
              className="flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-white/5"
            >
              <span className="text-slate-200">
                {opt.name} <span className="text-[var(--color-muted)]">· {opt.city}</span>
              </span>
              <span className="font-mono text-sky-300">{opt.iata}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
