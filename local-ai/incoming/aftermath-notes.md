# Aftermath: LA-8 notes (drafted 2026-10-18)

Steps are in `local-ai/incoming/aftermath.txt` (lint: 0 problems). 10 open items labelled `[local AI: after split]`.

## A list (relabel `[local AI: yes]`)
- R4-AFMO-6 (swipe a skill to the left to pin it): one block in `watchTree()` in `ui.js`, a one-line `touch-action: pan-y` rule and one browser test. Interpretation, stated in the step: the swipe works on the rows of the skill LIST (`#skill-tree .skill-row`), touch and pen only, never on the pannable skill map (a drag there already pans, `watchSkillMap()`), and it clicks the row's existing pin button, so pinning keeps its one code path. Mouse drags are ignored on purpose so a text selection never pins a skill.

## B list (chains)
- R4-AFPC-6 (6 steps): Past Runs table. The log entries have no calendar date, so "date" is the run number (order played). "Damage prevented" is the sum of `entry_prevented()` over the run's events, "severity" is `average_severity()`, "resilience reached" is `resilience_capacity`. The "event ribbon" is the same event lines the cards already show (`_render_event_breakdown_lines`). View state (table on, sort column, direction, opened run) is in memory only (four new `LIVE_NAMES`), nothing is saved. Engine in two steps, then drawing, then ribbon plus panel hook, then markup with clicks and one browser test, then CSS. Table view is an opt-in checkbox next to the existing sort and filter, so the card list is unchanged by default.

Notes for the audit: `index.html` is capped at 15,000 tokens by `tests/test_file_sizes.py` (about 57 KB now); step 5 adds roughly 300 bytes. The table needs no `pc-config.json` entry (it lives inside the existing Past Runs panel); the human still runs `scripts/generate-pc-pages.py` after step 5 because `index.html` changed.

## C list (not for the local AI)
| Item | Label | Reason |
|------|-------|--------|
| E-10 three named local profiles | `[Claude: shared]` | Every saved record (`aftermath_*_v1` keys in `aftermath_persist.py`, the meta, achievements) would need a per-profile key prefix, and it must keep working with the shared save widget and the progress export. The widget lives in `shared/` and a storage-key migration is the kind of change that loses saves if it is slightly wrong. |
| GE-3 Fog of War | `[Claude: design]` | The TODO itself flags a conflict with every surface that shows upcoming events (schedule strip E-17, "helps against" E-29, countdown pulse GE-26, expected-damage preview, mentor, plain-text schedule, run codes, ghost). The reveal arithmetic is unclear too: what Early Warning (1 ahead) and Mutual Aid (2 ahead) give when both are owned, and whether "the next 3" includes the event about to hit. Needs a decision and an audit of each surface before it can be cut into exact steps. |
| R4-PA-1 relief convoys | `[Claude: design]` | A computer-run neighbour, what you give, what comes back and when; new save data and balance. Related to the existing neighbour aid (R-31) so it must not break the "never a record" rule. |
| R4-PA-2 field clinic puzzle | `[Claude: design]` | A new puzzle with its own rules and cases; the result must feed recovery so the minigame counts, which touches the run economy. |
| R4-PA-5 Marathon mode (40 events) | `[Claude: design]` | `SCENARIOS` are all kept at 7 events with total damage tuned to the starting resources, and `resolve_next_event()` guards against farming knowledge points. A 40-event run needs its own damage/income/knowledge balance. Saving mid-run already works through the shared save widget, so the open part is the balance. |
| R4-AFPC-1 pannable, zoomable skill map | `[needs you]` | Mostly built already (E-2): drag to pan, +/- buttons and keys, Ctrl+wheel zoom, keyboard movement. What is left is decisions: should a plain wheel zoom (it takes over page scrolling), and what is "which runs used it" (the game keeps skill ranks by use, not a per-run list). The hover card would sit on the same `.skill-map-node` elements the map redraws. |
| R4-AFMO-1 swipeable event cards | `[Claude: design]` | A whole alternate phone layout with swipe gestures and a bottom sheet; gesture and bottom-sheet work failed in earlier audits. |
| R4-AFMO-3 three-height bottom sheet | `[Claude: design]` | Drag between snap heights is a bottom-sheet gesture, a task type that failed in earlier audits; it also has to keep the Invest buttons reachable on the Desktop page. |

| Item | Decision | Steps |
|------|----------|-------|
| E-10 | C | 0 |
| GE-3 | C | 0 |
| R4-PA-1 | C | 0 |
| R4-PA-2 | C | 0 |
| R4-PA-5 | C | 0 |
| R4-AFPC-1 | C | 0 |
| R4-AFPC-6 | B | 6 |
| R4-AFMO-1 | C | 0 |
| R4-AFMO-3 | C | 0 |
| R4-AFMO-6 | A | 1 |

Totals: A 1, B 1 item (6 steps), C 8.
