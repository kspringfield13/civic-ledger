// Every signal in the UI must expose its evidence trail (EVIDENCE_STANDARD.md).
export default function EvidenceLink({ count = 0 }: { count?: number }) {
  return (
    <a href="#" onClick={(e) => e.preventDefault()} style={{ fontSize: 13 }}>
      {count} evidence item{count === 1 ? "" : "s"}
    </a>
  );
}
