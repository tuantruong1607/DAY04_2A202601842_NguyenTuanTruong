export function SourceTag({ source, retrievedAt }: { source?: string; retrievedAt?: string }) {
  if (!source && !retrievedAt) return null;
  return (
    <div className="flex items-center gap-1.5 text-[11px] text-[var(--color-muted)]">
      <svg viewBox="0 0 20 20" fill="currentColor" className="h-3 w-3">
        <path
          fillRule="evenodd"
          d="M10 18a8 8 0 100-16 8 8 0 000 16zm.75-11.25a.75.75 0 00-1.5 0v3.5c0 .2.08.39.22.53l2.5 2.5a.75.75 0 101.06-1.06l-2.28-2.28V6.75z"
          clipRule="evenodd"
        />
      </svg>
      <span>
        {source ?? "local"}
        {retrievedAt ? ` · ${new Date(retrievedAt).toLocaleString()}` : ""}
      </span>
    </div>
  );
}
