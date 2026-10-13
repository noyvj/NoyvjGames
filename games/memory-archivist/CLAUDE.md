# Memory Archivist

Seed: `planning/memory-archivist-plan.md`. Personal project, no BCM tag, working title. Started 2026-10-13 with `scripts/new_game.py`.
Read the plan first: it holds the design every milestone follows. Then `BUILD-STATUS.md` here.

## One-line pitch
Source: the Quick ideas round (B6), owner-approved: "restore corrupted memories from a damaged AI by putting scraps back in order (dark, quiet, science fiction)." Checked against `PLAYER-PROFILE.md`: computers and AI, dark moody science fiction, a notebook being filled in (lore matters when it is a notebook), quiet tragic-but-gentle characters (the AI is flawed, not a hero), helper and healer role, short wins into one slow story, logic puzzles, no timers, nothing lost, no visual-novel structure (the story is the reward for a puzzle, never a choice tree). Personal project, no BCM tag, working title.

## Stack
- Pyodide Python, plain HTML/CSS, no build step. Engine modules are plain Python with no DOM (the Signal / Lexis
  pattern): `game.py` is the entry point (`handle(json) -> json`, plus `get_state()` / `load_state()` for the
  shared save widget); `app.js` is glue only.
- No audio files. Nothing timed, nothing lost, no luck needed for 100% (the site's standing rules).

## Milestones
| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Constraint engine and prover | Scrap tags, constraint derivation, permutation counter, propagation solver, bank 1 (8 memories) with proofs | Not started |
| 2 | Core UI | Scrap slabs, timeline slots, drag and keyboard reordering, Check, Notes pane, save contract. Playable slice | Not started |
| 3 | Banks 2-3 | 16 more memories, corruption levels and Clean, the Archive corridor | Not started |
| 4 | Banks 4-5, hints, goals | 16 more memories (40), the timeline view, hint ladder, three-goals strip. First complete game | Not started |
| 5 | Standard kit | Opening screen, tutorial, About with Sources, What's New, keyboard help, confirm dialogs, light theme, accessibility | Not started |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test | Not started |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog | Not started |

## Working conventions
- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag memory-archivist-milestone-0N`.
- Update the Status column as work happens, and `BUILD-STATUS.md` after every milestone.
- Hub registration is a separate step (`games/memory-archivist/register.json`, then `scripts/register_game.py memory-archivist`).
