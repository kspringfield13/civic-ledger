# Data Source Policy

## Admission criteria — a source may be ingested only if ALL are true
1. **Lawful access:** public, openly licensed, or documented operator authorization.
2. **Terms respected:** rate limits, robots.txt, API terms, and license recorded.
3. **Provenance recorded:** every stored record keeps source URL/identifier,
   retrieval timestamp, and retrieval method (`SourceDocument` model).
4. **Registry entry:** completed `docs/data-source-inventory-template.md`
   entry committed before ingestion code merges.

## Source tiers
- **Tier 1 (authoritative):** official government systems — SAM.gov exclusions,
  USAspending, agency IG reports, court dockets. Usable for matching and signals.
- **Tier 2 (supporting):** corporate registries, official press releases.
  Usable as corroboration, weighted lower in confidence.
- **Tier 3 (contextual):** news, research. Context only — never the basis of a
  signal on its own.

## Handling rules
- Raw pulls land in `data/raw/` (git-ignored), normalized output in
  `data/processed/` (git-ignored). Only fictional samples live in `data/sample/`.
- No personal data beyond what the public record itself contains; no enrichment
  of private individuals.
- Retention: raw data may be deleted after normalization if the provenance
  pointer allows re-retrieval; evidence backing an open case lead is retained.

## Removal
If a source's terms change or authorization lapses, ingestion stops immediately
and dependent signals are flagged `source_revoked` for review.
