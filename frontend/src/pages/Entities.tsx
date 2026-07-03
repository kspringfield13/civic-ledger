import { useEffect, useState } from "react";
import { getJSON } from "../api/client";

interface Vendor { id: number; name: string; uei?: string; }

export default function Entities() {
  const [rows, setRows] = useState<Vendor[]>([]);
  useEffect(() => { getJSON<Vendor[]>("/entities").then(setRows).catch(() => {}); }, []);
  return (
    <section>
      <h2>Entities</h2>
      <p>Fictional sample vendors only.</p>
      <ul>{rows.map((v) => <li key={v.id}>{v.name} {v.uei ? `(${v.uei})` : ""}</li>)}</ul>
    </section>
  );
}
