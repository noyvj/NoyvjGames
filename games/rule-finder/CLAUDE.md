# Rule Finder (working title)

Seed: `planning/rule-finder-plan.md` (Quick ideas round A5, TODO QI-5). Personal project, no BCM tag. Built 2026-10-11 by a background agent.

## One-line pitch
A signal-room sorting game: an old relay lets some items through its gate and stops others, and you work out and name the rule behind it by building your own test items.

## Stack
- Pyodide Python, plain HTML/CSS, no build step. `game.py` is the single engine entry point (`handle(json) -> json`, `get_state()` / `load_state()` for the shared save widget); `app.js` is glue only. Python 3.9 locally (Pyodide 3.12): no 3.10+ syntax in engine code.
- Runs from any static server. No audio files; the only sound would be shared/sfx.js, which this build does not use.

## Core constraints (do not violate without asking)
1. The engine is pure and deterministic: no clock, no randomness (a test scans every engine module). `tools/author.py` uses a seeded `random.Random` only to FIND starting examples; the result is frozen into `cases_*.py`.
2. No timers, energy, grinding or progress loss; no roguelike, deck or card mechanics; no mandatory leaderboard. Testing is free and unlimited; a wrong name only shows a counter-example; a fail always lets the player retry.
3. Every case is open from the start (owner taste: objectives with no strict order). The plan's "drawer n+1 opens at 5 of 8 cleared" is NOT built; the drawer order is a suggestion only.
4. Every authored case is proved fair by `tools/finder.py` and re-checked in `tests/test_cases.py` (see "How fairness is proved").
5. No colour-only encoding: shapes have their own glyph and a name, answers are words and marks as well as colour.

## The rule language (lang.py)
- Three domains, each a fixed ordered list of items: `num` (integers 0 to 99), `shape` (strings of 3 to 6 tiles from circle `c`, square `s`, triangle `t`, diamond `d`; sizes run c < s < t < d), `grid` (3 by 3 patterns, nine `#`/`.` marks row by row).
- A clause is one named property ("is even", "starts with a circle", ...); the libraries have 33 number, 36 shape and 24 pattern clauses, each with a family, a "yes" phrase and a "no" phrase. A rule is one to three clauses, each optionally negated, joined by and / or and read left to right: ((a OP b) OP c). Negating one clause is enough for every use of NOT.
- A rule's TABLE is an int with bit i set when item i of the domain is let through. Two rules agree when their tables are equal (extensional equality, exhaustive over the domain). Encoded form: `even&~ge:50|has:7` (`~` negates, `&` and `|` join).
- No two clauses (or a clause and another's complement) share a table, so the menu has no twins (tested).

## How fairness is proved (tools/finder.py)
- Rule size = number of clauses. The hidden rule's table must have no shorter formula (`min_size`).
- COMPETITORS: every other table of size <= the hidden size that still agrees with the starting examples (enumerated with pruning on the example masks). A case needs at least one, otherwise the examples already give the answer.
- PAR TEST SET (`shortest` in the case, the codex's "shortest path"): a smallest list of items whose answers separate the hidden rule from every competitor. It is a hitting set over the competitors' difference masks, reduced to the minimal differences and distinct item columns, found greedy then exact (`exact_cover`). Tests re-verify: sufficient, no redundant item, and no smaller set (search finished).
- MEDAL TARGET: `par` = shortest path + `PAR_ALLOWANCE` (2). This is a deliberate deviation from the plan, which says "at par"; a minimal separating set is what an oracle needs, not a person. Gold is within par, silver within 4 more, bronze otherwise.

## Authoring
`tools/specs.py` holds one entry per case (rule, example counts, operator log line). `python3 tools/build_cases.py [drawer]` draws examples, runs the proof and rewrites `cases_<drawer>.py` (frozen data; do not edit by hand). Then run the tests.

## Milestones
| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Rule language and prover | `lang.py`, `tools/finder.py`, drawer 1 (8 cases) with proofs and tests | Done |
| 2 | Sorter UI | Item builder, Send, gate animation, Rule Builder, near-miss counter-example, save contract. Playable slice | |
| 3 | Drawers 2-4 | 24 more cases, shape and Not clauses, Rule Codex | |
| 4 | Drawers 5-6, hints, goals | 16 more cases (48 in all), patterns, odd gate, hint ladder, goals strip, medals | |
| 5 | Standard kit | Opening screen, tutorial, About with Sources, What's New, keyboard help, confirm dialogs, light theme, accessibility | |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test | |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog | |

## Working conventions
- Commit only this folder with a pathspec commit, then tag `rule-finder-milestone-0N`. Hub registration (QI-5-R) is a separate later job.
- Tests: `python3 -m pytest -q games/rule-finder`; lint: `python3 -m flake8 --extend-ignore=E501 games/rule-finder`.
