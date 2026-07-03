# Mobile / Claude Code workflow

The phone is the control surface; execution happens in Claude Code Web,
Codespaces, a cloud VM, or a local machine.

## Principles
- **Issue goals, not keystrokes.** Send `/goal` prompts; review the diff and
  the agent's report on the phone. Don't hand-type multi-line terminal work.
- **Everything scriptable.** If an operation needs more than one short
  command, it becomes a `make` target first.
- **Commit small and often.** Each goal ends in one or more reviewed commits
  with descriptive messages; nothing pushes without human review of the diff.
- **Secrets never touch chat.** Real keys go into `.env` in the execution
  environment only (or a cloud secret manager). Never paste a key into a
  Claude conversation, an issue, or a commit.
- **Review before push.** On the phone: read the report, skim the diff,
  then instruct push. If anything is unclear, ask the agent to explain the
  diff before approving.

## Typical loop
1. Phone → `/goal <next objective>` to Claude Code.
2. Agent works: implements, runs `make test` + `make lint`, commits.
3. Agent reports: files changed, commands to run, assumptions, next goal.
4. Phone → review, request fixes or approve push.

## Handy one-liners the agent should use
`make setup` · `make test` · `make lint` · `make backend` · `make frontend`
· `make secrets-scan` · `git log --oneline -10` · `git diff --stat`
