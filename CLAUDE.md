# CLAUDE.md — operating manual for Claude Code sessions

## Mission
Build and maintain civic-ledger: a lawful FWA risk-intelligence platform that
turns public/authorized data into evidence-linked risk signals for human review.

## Non-negotiable rules
1. **Lawful only.** Public records, open datasets, FOIA planning, and
   user-provided authorized data. Nothing else. No hacking, credential use,
   scraping of private/authenticated systems, impersonation, or evasion.
2. **No unauthorized access** — ever, including "just to test."
3. **No accusations.** Output is leads, signals, scores, and review queues.
   Language in code, UI, and docs must say "risk signal," never "fraud found."
4. **Evidence first.** Every signal must link to its source records
   (`EVIDENCE_STANDARD.md`). No orphan claims.
5. **Label uncertainty.** Every signal carries confidence + known
   false-positive modes from its detector spec.
6. **Test before commit.** `make test` and `make lint` must pass.
7. **Never commit secrets.** `.env` stays local; run `make secrets-scan`
   if in doubt. Never echo key values into chat or logs.

## Mobile workflow (primary control surface: iPhone → Claude Code)
- The human issues short `/goal` prompts and reviews diffs on the phone.
- Prefer `make` targets over multi-line terminal work.
- Commit small and often with descriptive messages; the human reviews before push.
- If blocked (missing dependency, ambiguous requirement with real consequences),
  state the blocker and the smallest question — otherwise proceed with
  reasonable defaults and record assumptions in the commit message.

## Expected commands
`make setup | test | lint | fmt | backend | frontend | db-up | secrets-scan`

## Continuing from future /goal prompts
1. Read this file, `ROADMAP.md`, and the relevant governance doc first.
2. Restate the goal in one line; list assumptions.
3. Implement, test, and report: created/changed files, commands to run,
   errors, assumptions, and a recommended next /goal.
