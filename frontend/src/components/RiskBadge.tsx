// Shows severity + confidence as separate values, on purpose:
// severity is impact, confidence is evidence fit (DETECTION_PRINCIPLES.md #3).
export default function RiskBadge({ severity, confidence }: { severity: number; confidence: number }) {
  return (
    <span style={{ fontSize: 13, background: "#f3f3f3", borderRadius: 4, padding: "2px 8px" }}>
      severity {severity.toFixed(2)} · confidence {confidence.toFixed(2)}
    </span>
  );
}
