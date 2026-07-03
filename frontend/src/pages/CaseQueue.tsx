import { useEffect, useState } from "react";
import { getJSON } from "../api/client";

interface CaseLead { id: number; title: string; summary?: string; status: string; }

export default function CaseQueue() {
  const [rows, setRows] = useState<CaseLead[]>([]);
  useEffect(() => { getJSON<CaseLead[]>("/cases").then(setRows).catch(() => {}); }, []);
  return (
    <section>
      <h2>Case queue</h2>
      <p>Leads awaiting human review. Dispositions require structured reasons (Phase 3).</p>
      <ul>
        {rows.map((c) => (
          <li key={c.id}><strong>[{c.status}]</strong> {c.title} — {c.summary}</li>
        ))}
      </ul>
    </section>
  );
}
