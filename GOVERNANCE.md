# Governance

## Roles
- **Operator (human):** sets goals, reviews diffs, approves data sources,
  owns all external communication. Only humans may escalate a case lead.
- **Engineering agent (Claude Code):** implements within the boundaries in
  `LEGAL_AND_ETHICAL_BOUNDARIES.md`; must refuse out-of-scope requests.
- **Reviewer (human, future):** disposition of case leads (confirm-worthy /
  dismiss / needs-more-data) with written rationale.

## Decision rules
- New data source → requires a completed `docs/data-source-inventory-template.md`
  entry and operator sign-off before any ingestion code is written.
- New detector → requires a YAML spec in `detectors/` passing contract tests
  before implementation.
- Any output leaving the system (report, referral, FOIA request) → human-drafted
  or human-approved, and must use lead/signal language, never accusation language.

## Audit trail
- All ingestion runs, detector runs, and review actions are recorded with
  timestamps and actor identity (see `ReviewAction`, `EvidenceItem` models).
- Git history is part of the audit trail: no force-pushes to `main`,
  no history rewriting after data-affecting commits.

## Change control
- `main` is protected in spirit: tests + lint must pass before merge/push.
- Governance docs change only by explicit operator instruction, and the
  change rationale goes in the commit message.
