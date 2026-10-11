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
| 2 | Sorter UI | Item builder, Send, gate animation, Rule Builder, near-miss counter-example, save contract. Playable slice | Done |
| 3 | Drawers 2-4 | 24 more cases, shape and Not clauses, Rule Codex | Done |
| 4 | Drawers 5-6, hints, goals | 16 more cases (48 in all), patterns, odd gate, hint ladder, goals strip, medals | Done |
| 5 | Standard kit | Opening screen, tutorial, About with Sources, What's New, keyboard help, confirm dialogs, light theme, accessibility | Done |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test | |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog | |

## Engine and page notes (milestone 2)
- `game.handle(json)` returns the whole view; the clause `menu` is sent only when the case changes (`menu_due`). Actions: `open`, `pick`, `next`, `test {item}`, `preview {rule}`, `name {rule}`, `restart`, `reset`. A rule is `{"lits": [[clause id, negated], ...], "ops": ["and"|"or", ...]}`.
- A TEST is a new item sent to the gate: it counts once per case attempt; an item already seen (starting examples, earlier tests, free counter-examples) answers again for free. Starting examples are shown in the log as "given".
- NAMING: first the draft is checked against everything already seen; a rule that contradicts a seen item is a "conflict" (told, never counted). Otherwise equal on every domain item (`lang.agree`) names the case; else a NEAR MISS: the first item (domain order) where the draft and the hidden rule differ is added to the log as a free counter-example (`f`), the near-miss tally goes up, and the hidden rule is never shown. The Rule Builder is capped at the drawer's `max_clauses`.
- Naming a case again only ever improves the best test count (`restart` clears the test log of a named case so a better count can be tried); `m` remembers a near miss before naming (for the Counter-Example achievement).
- Save (`get_state`): `cur`, `named {case: {t: best tests, r: rule, m}}` (each rule re-judged against the hidden one on every load), `log {case: {t: [...], f: [...]}}` (items re-normalised, deduplicated, never an example), `tally {tests, near, hints}`; only non-default keys; the gate's last answer and the verdict are not saved.
- Items are drawn by `app.js` (`itemSvg`: a number tile, a string of sized tiles, a 3x3 grid) from the engine's item keys; the view never decides an answer (a test checks it).
- The page uses the `ConfirmDialog` for the full reset; all other buttons act at once and nothing is lost by any of them.

## Milestone 3 notes
- Drawers: Number Gates (1 clause, numbers), Shape Strings (1, shapes), Two Clauses (2, four numbers and four shapes, and/or), Not (up to 3, every case needs a NOT: a test shows no positive-only rule of the same size or shorter has its table). Builder cap per drawer is `max_clauses` (1, 1, 2, 3, 3, 3). Names are relay parts that never hint at the rule; each case has one dry operator log line.
- NO DRAWER GATING (deviation from plan section 3): every drawer and case is open from the start; progress.drawer_open/case_open exist so there is one place to ask.
- Rule Codex (`codex.py`): one page per case, filled when named, READ when opened (`page {case}`); `read` is saved (only named cases) and is what the Full Codex achievement will count, so "All Forty-Eight" (named) and "Full Codex" (read) differ. A page shows the rule in words, the family labels, the shortest path (the par set with each answer) and the player's best, par and medal.
- Wall map (`render.wall_svg`): six rows of eight cubbies drawn in Python; empty = dashed outline, named = solid with a tick and 3/2/1 pips for gold/silver/bronze, current = heavy outline; each cubby is a keyboard-reachable button.

## Milestone 4 notes
- Drawers 5 (Patterns, 3x3 grids, sizes 1 to 3) and 6 (The Odd Gate: eight size-2 rules whose table differs from the first clause by exactly ONE item; a test checks that item is on the shortest path and never among the starting examples). 48 cases, six drawers of eight.
- Hint ladder (`hints.py`, action `hint`): rung 1 nudge = the kind of property (family phrase), never the clause or the joins; rung 2 hint = the first shortest-path item not yet seen, shown as a ghost tile with a button that loads it into the item builder (the player still presses Send); rung 3 answer = the rule in words with a button that loads it into the Rule Builder (the player still presses Name it). Free, on request only, saved per case in `rungs`, counted in the `hints` tally, never touching a medal. Deviation worth an owner glance: because the Answer rung does not name the case, a player can name it with 0 tests and earn Quick Eye / a gold medal; the plan says hints never touch the medal, so this is as specified.
- Goals strip (`achievements.goals`): the next three unearned achievements in manifest order with counts and bars. `achievements.py` already holds all 14 (the manifest, panel and toast arrive in milestone 6).
- Medals: gold within par (shortest path + 2), silver within 4 more, bronze otherwise; the wall map shows 3, 2, 1 pips.

## Milestone 5 notes
- Standard kit as in Hull Repair: opening screen (`shared/opening-screen.js`), 10-step tutorial (`TUTORIAL_STEPS`, replaceable on the Desktop boot through `window.RULE_FINDER_PC_TUTORIAL_STEPS`), About from `info.py` (fiction, no real-world facts, so nothing to date; it links the shared Sources page), `sources.json` (only Wason's 2-4-6 task and Eleusis, as the plan records, plus Pyodide), What's New + banner, keyboard help (`?`, with the builders' number keys), reset confirm dialog, story toggle on `.story-text` (operator log lines in the verdict card and Codex), light theme (contrast tested for both themes), `tests/test_pledge.py`.
- Builder keys (`onBuilderKey`): 1 to 4 add a tile in the shape builder, Backspace takes one back, 1 to 9 toggle squares in the pattern builder, Enter sends.

## Working conventions
- Commit only this folder with a pathspec commit, then tag `rule-finder-milestone-0N`. Hub registration (QI-5-R) is a separate later job.
- Tests: `python3 -m pytest -q games/rule-finder`; lint: `python3 -m flake8 --extend-ignore=E501 games/rule-finder`.
