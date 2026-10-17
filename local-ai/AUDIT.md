# How to audit the local AI's work (the default way, cheapest checks first)

Written 2026-10-17 from the first four audit rounds (about 130 ideas). What those rounds taught: roughly
half of the model's features were dead as pushed (never wired, wrong ids, missing HTML, no tests), so the
audit's job is mostly rebuilding or reverting, and the expensive part (a model reading diffs and driving a
browser) should only be spent on what the free checks cannot decide.

## The order (every step is cheaper than the next)
1. **Intake, free.** `python3 scripts/audit_local_ai.py intake` fetches, prunes, lists the idea commits waiting
   per game (stacked branches are de-duplicated by commit), flags ids already ticked in `planning/TODO-NEXT.md`,
   commits outside the game folder, and tooling commits that touch more than `local-ai/` and the dev logs.
   Fetch again right before starting any other big job: the Alienware keeps pushing.
2. **Prepare, free.** `python3 scripts/audit_local_ai.py prepare <slug>` makes the worktree
   `.claude/worktrees/audit-<slug>` on branch `audit/<slug>` from `main`, cherry-picks the game's commits one at a
   time and after each one runs `local-ai/static_check.py` (only NEW findings count), the scope check and the
   test-added check; then the game's pytest, flake8, the Desktop-page check and the precache check. The printed
   report is the reviewer's to-do list. Conflicts with `main` are reported, not forced.
3. **Code read, tokens.** The reviewer reads ONLY the commits the report flags (static findings, no tests,
   outside the folder, failing gates) plus a quick look at the rest against the checklist in `RULES.md`
   ("Mistakes the reviewer keeps fixing"). Fix small things on `audit/<slug>` with one commit per idea; revert
   what is not small; never edit `planning/`, `shared/`, `sw.js` or other games. Add `tests/test_ai_*.py` that
   check wiring (the id in the HTML equals the id in the JS, a setting reads back on load, a save round-trips).
4. **Live pass, cheap, once per game, last.** `python3 scripts/audit_local_ai.py live <slug>` opens index.html and
   pc.html at 1440x900 and 360x740 on the audit worktree AND on `main`, and reports only what is NEW: page errors,
   console errors, horizontal overflow, ids added by the diff that are missing, buttons under 40px tall on a
   phone. Drive a feature by hand only when the report or the idea needs it (gestures, drag, hold).
5. **Finish, free.** `python3 scripts/audit_local_ai.py finish <slug> --accepted R4-XX-1,R4-XX-2 --partial R4-XX-3 --delete-remote`
   merges the branch, adds missing `games/<slug>/` files to the `sw.js` precache, regenerates the offline
   manifest, ticks the accepted ids, commits, removes the worktree and branch, and deletes the remote
   `local-ai/*` branches whose idea commits are all handled. Questions for the owner go in `planning/FOR-YOU.md`
   (one question each), then `python3 scripts/generate-ideas-data.py`.

## What counts as accepted, partial, rejected
- **Accepted:** the owner's item works in the browser, follows the standing rules, has a wiring test.
- **Partial:** works but a stated part is missing; tick it only if the missing part is minor and the reviewer
  says so in the commit message, otherwise leave the item open.
- **Rejected:** reverted (own commit with the reason). Needs a new engine action, a zoom/pan/transform of the SVG
  board, or a redesign: say so, so it can be queued as Claude work.

## Rules of thumb that saved time
- Run the static checker before reading anything; it found the same classes of bug the human audits did.
- Never open the browser per commit; one scripted pass per game.
- Compare against `main` before calling a layout problem new (the live pass does this).
- One agent per game; never two on the same folder; two agents at a time; log the claim on the coordination board.
- Duplicates happen (a second commit of an idea `main` already has): drop them and say so.
