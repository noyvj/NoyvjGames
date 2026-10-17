---
name: audit-local-ai
description: Audit the personal AI's pushed work (local-ai/* branches) the default way: intake, prepare, code read, one live pass, finish. Use when asked to audit, review or merge the local AI's branches or its new ideas.
---

Read `local-ai/AUDIT.md` and follow it exactly. The short version:

1. `python3 scripts/audit_local_ai.py intake` (fetches; lists what is waiting per game).
2. Claim the folders on `planning/AI-COORDINATION.md`. For each game (one agent per game, two at a time) run
   `python3 scripts/audit_local_ai.py prepare <slug>`, review only what the report flags using
   `local-ai/audit-brief.md`, fix small / revert big, add wiring tests, commit on `audit/<slug>`.
3. `python3 scripts/audit_local_ai.py live <slug>` once, then
   `python3 scripts/audit_local_ai.py finish <slug> --accepted ... --partial ... --delete-remote`.
4. Put owner questions in `planning/FOR-YOU.md` (single questions), regenerate ideas data, report before/after
   counts for `planning/TODO-NEXT.md`.
Fetch again before starting any other large job; the Alienware keeps pushing.
