# Drift: LA-8 notes (drafted 2026-10-18)

`local-ai/incoming/drift.txt` holds no steps (header only; lint: 0 problems). 17 open items labelled `[local AI: after split]`. I read the Drift code (`drift_visuals.py`, `drift_rules.py`, `drift_calendar.py`, `ui.js`, `pc-config.json`, `index.html`) before deciding; five of the "small" R4 items describe things that do not exist in Drift today, which is the main finding.

## A list (relabel `[local AI: yes]`)
None.

## B list (chains)
None.

## C list (not for the local AI)
| Item | Label | Reason |
|------|-------|--------|
| GI-4 Region Atlas | `[Claude: design]` | Its dependency W-1 is done (`shared/level-select.js`), but four region profiles (capacity and income numbers), unlock thresholds and a starting-profile hook in `RegionState` plus a save key are balance and design work across `drift_model_region.py`, `drift_rules.py` and `drift_savestate.py`. |
| GI-6 Rival Regions | `[Claude: design]` | Three AI-managed regions need decision rules (Frugal, Builder, Reactive), a second simulation per round, extra trend lines and a comparison card. |
| GI-10 Timeline Scrubber | `[Claude: design]` | Replay needs a full per-round decision log and a deterministic forward replay; only undo snapshots exist today. |
| GI-27 Legacy Map | `[on hold]` | The item itself says it overlaps GI-9 (Legacy Points tree) and needs the owner to confirm one meta-progression; W-3 (skill-tree component) is built but unwired. |
| I-7 rich district view | `[Claude: design]` | Pan/zoom, day/night lighting and arrival dots travelling along roads: an animation and canvas project, with Reduce Motion handling. |
| R4-DR-1 arrival mix | `[needs you]` | Changes the arrival model (families, singles, older people, children with different needs), the balance numbers and the save; needs your numbers. |
| R4-DR-5 modular vs permanent housing | `[needs you]` | A new build choice with running-cost and price numbers that change the baseline economy. |
| R4-PD-1 neighbour book | `[needs you]` | CONTRADICTS Drift's standing constraint in CLAUDE.md ("Institutions, not individuals ... never individual migrant stories or named people"): a card per household with an invented note is exactly that. Needs your decision before any work. |
| R4-PD-4 Arkship mode | `[needs you]` | A retelling of the whole game in a space setting: new text, labels and probably new art. |
| R4-PD-5 Region charter | `[needs you]` | Says "every five-round council goal you clear", but Drift has no five-round council goal: the Mayor's Council offers one pick every 10 rounds (`COUNCIL_INTERVAL = 10`) and the Crisis Calendar and star goals work differently. Suggested reading to confirm: one charter clause per council program adopted (9 at most). Tell me and it becomes a 4-step chain. |
| R4-DRPC-1 pan and zoom district view | `[Claude: design]` | No district map with clickable buildings exists: the "region picture" is six decorative, `aria-hidden` skyline blocks (`region-visual-building-a` to `f`) with no residents or strain per building. Pan/zoom plus building data is a new feature. |
| R4-DRPC-4 resize and tile windows | `[Claude: shared]` | Window resizing and tiling is the shared Desktop shell (`shared/pc-shell.js`). |
| R4-DRPC-5 Ctrl+F building search | `[needs you]` | Buildings have no names or types to search (see DRPC-1), and hijacking Ctrl+F replaces the browser's own find on the page. |
| R4-DRPC-6 sticky bar | `[Claude: shared]` | The Desktop page already shows strain and wellbeing as readout chips from `pc-config.json` `readouts` (built by the shared shell) and the phone page has a sticky bar from `shared/mobile-hud.js`; there is no pannable map for it to stay put over. Adding the band and a mini trend line to those chips is a shell change. |
| R4-DRMO-1 portrait map with bottom sheet | `[Claude: design]` | Depends on the non-existent clickable map; bottom sheets failed in earlier audits (a term sheet exists in `ui.js`, which is not to be edited unless the task is about the phone view). |
| R4-DRMO-5 swipe a gauge between three views | `[Claude: design]` | Gesture work on re-rendered gauges; failed in earlier audits. |
| R4-DRMO-7 swipe to buy | `[Claude: design]` | Gesture work; `ui.js` already owns a panel-swipe handler for phones and is off limits for ordinary tasks. |

| Item | Decision | Steps |
|------|----------|-------|
| GI-4 | C | 0 |
| GI-6 | C | 0 |
| GI-10 | C | 0 |
| GI-27 | C | 0 |
| I-7 | C | 0 |
| R4-DR-1 | C | 0 |
| R4-DR-5 | C | 0 |
| R4-PD-1 | C | 0 |
| R4-PD-4 | C | 0 |
| R4-PD-5 | C | 0 |
| R4-DRPC-1 | C | 0 |
| R4-DRPC-4 | C | 0 |
| R4-DRPC-5 | C | 0 |
| R4-DRPC-6 | C | 0 |
| R4-DRMO-1 | C | 0 |
| R4-DRMO-5 | C | 0 |
| R4-DRMO-7 | C | 0 |

Totals: A 0, B 0, C 17.
