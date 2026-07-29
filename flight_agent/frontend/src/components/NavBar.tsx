import { NavLink } from "react-router-dom";

const LINKS = [
  { to: "/", label: "Chat", icon: "💬", end: true },
  { to: "/search", label: "Search & Compare", icon: "🔎" },
  { to: "/track", label: "Track Flight", icon: "✈️" },
  { to: "/board", label: "Airport Board", icon: "🛫" },
  { to: "/watches", label: "Watches", icon: "🔔" },
];

export function NavBar() {
  return (
    <aside className="flex w-60 shrink-0 flex-col border-r border-[var(--color-border)] bg-[var(--color-panel)]">
      <div className="flex items-center gap-2 px-5 py-5">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-sky-400/15 text-lg">✈️</div>
        <div>
          <div className="text-sm font-semibold text-slate-100">Flight Agent</div>
          <div className="text-[11px] text-[var(--color-muted)]">search &amp; tracking</div>
        </div>
      </div>
      <nav className="flex flex-col gap-1 px-3">
        {LINKS.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.end}
            className={({ isActive }) =>
              `flex items-center gap-2.5 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors ${
                isActive
                  ? "bg-sky-400/10 text-sky-300"
                  : "text-slate-300 hover:bg-white/5 hover:text-slate-100"
              }`
            }
          >
            <span className="text-base">{link.icon}</span>
            {link.label}
          </NavLink>
        ))}
      </nav>
      <div className="mt-auto space-y-1 px-5 py-4 text-[11px] text-[var(--color-muted)]">
        <p>Search &amp; monitor only — never books or pays.</p>
        <p>Data: FlightAPI.io + AeroDataBox</p>
      </div>
    </aside>
  );
}
