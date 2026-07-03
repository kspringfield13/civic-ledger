import { useEffect, useState } from "react";
import { getJSON } from "../api/client";

interface Source { id: number; name: string; tier: number; access_basis: string; }

export default function Sources() {
  const [rows, setRows] = useState<Source[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    getJSON<Source[]>("/sources").then(setRows).catch((e) => setError(String(e)));
  }, []);
  return (
    <section>
      <h2>Data sources</h2>
      {error && <p>Backend not reachable — start it with <code>make backend</code>.</p>}
      <ul>
        {rows.map((s) => (
          <li key={s.id}>{s.name} — tier {s.tier}, {s.access_basis}</li>
        ))}
      </ul>
    </section>
  );
}
