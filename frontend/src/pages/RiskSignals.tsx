import { useEffect, useState } from "react";
import { getJSON, type RiskSignal } from "../api/client";
import EvidenceLink from "../components/EvidenceLink";
import RiskBadge from "../components/RiskBadge";

export default function RiskSignals() {
  const [rows, setRows] = useState<RiskSignal[]>([]);
  useEffect(() => { getJSON<RiskSignal[]>("/risk-signals").then(setRows).catch(() => {}); }, []);
  return (
    <section>
      <h2>Risk signals</h2>
      <p>Hypotheses for review with severity and confidence — never findings.</p>
      <ul>
        {rows.map((s) => (
          <li key={s.id} style={{ marginBottom: 8 }}>
            <strong>{s.detector_id}</strong> — {s.hypothesis}{" "}
            <RiskBadge severity={s.severity} confidence={s.confidence} /> <EvidenceLink count={1} />
          </li>
        ))}
      </ul>
    </section>
  );
}
