import { NavLink } from "react-router-dom";
import type { ReactNode } from "react";

const nav = [
  { to: "/", label: "Dashboard" },
  { to: "/sources", label: "Sources" },
  { to: "/entities", label: "Entities" },
  { to: "/risk-signals", label: "Risk signals" },
  { to: "/cases", label: "Case queue" },
];

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <div style={{ fontFamily: "system-ui, sans-serif", maxWidth: 960, margin: "0 auto", padding: 16 }}>
      <header style={{ marginBottom: 8 }}>
        <h1 style={{ margin: 0 }}>civic-ledger</h1>
        <p style={{ margin: "4px 0", color: "#555" }}>
          Risk signals for human review — not determinations of fraud.
        </p>
        <nav style={{ display: "flex", gap: 12, borderBottom: "1px solid #ddd", paddingBottom: 8 }}>
          {nav.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.to === "/"}>
              {n.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main>{children}</main>
    </div>
  );
}
