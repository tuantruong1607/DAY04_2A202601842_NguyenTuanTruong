import type { ReactNode } from "react";

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-2xl border border-[var(--color-border)] bg-[var(--color-card)] shadow-lg shadow-black/20 ${className}`}>
      {children}
    </div>
  );
}

export function CardHeader({ title, subtitle, right }: { title: string; subtitle?: string; right?: ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-3 border-b border-[var(--color-border)] px-5 py-4">
      <div>
        <h2 className="text-sm font-semibold tracking-wide text-slate-100">{title}</h2>
        {subtitle && <p className="mt-0.5 text-xs text-[var(--color-muted)]">{subtitle}</p>}
      </div>
      {right}
    </div>
  );
}
