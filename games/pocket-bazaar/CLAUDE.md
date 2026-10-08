# Pocket Bazaar (working title)

Personal project, no BCM tag. Plan: `planning/pocket-bazaar-plan.md` (the pledge in section 1 is binding).

## One-line pitch
A tiny market stall: customers ask for goods, you merge basic goods on a small board into better ones, hand them over before customers lose patience, and chain fulfilments into combos, in a 3-5 minute market day.

## The pledge (binding, tested in Milestone 6)
No energy, lives or stamina. No microtransactions or premium currency (one currency, coins, earned only by play). No timers that gate play: customer patience counts in **beats** (player actions), so nothing expires while the player is away. No daily-login rewards, no fake scarcity, no guilt dialogs, no in-game ads (only the hub's labelled footer bar). Progress is saved on every action. Every day is solvable: Sell and Broom always work, so the board cannot soft-lock.

## Stack
Python via Pyodide (the Lexis/Signal pattern): DOM-free engine modules, `game.py` with `handle(json)`, `get_state()` and `load_state()`, and a thin JS view (`app.js`). Plain HTML/CSS, no build step. Rendering is a DOM grid of buttons, with pointer-event drag plus a tap-then-tap path that is also the keyboard path. No audio, no real-time clock.

## Engine modules
| File | Job |
|---|---|
| `goods.py` | five families x five tiers, wildcard, prices, codes |
| `rng.py` | seeded integer PRNG stored as `{seed, draws}` |
| `board.py` | the merge board: merge, three-way bonus, cascade, move/swap, sell, broom, legal-move check, solver (`plan_build`), text form, save form |
| `textplay.py` | text harness: play a board from a script of commands |
| `orders.py` | customers: archetypes (Regular, Haggler, Critic, Bulk buyer), order matching, payment, patience from build cost, the order generator and its reachability check |
| `days.py` | the day recipes: first ten days hand-tuned, then Free Stall curve (capped at 16 customers, tier 5) |
| `day.py` | one market day: counter, queue (three at the stall, the rest waiting), beats, patience, hand-over, leaving, serving, summary |
| `game.py` | the one entry point: `handle(json)`, `get_state()`, `load_state()`; state is saved with only non-default keys |

View files: `index.html`, `style.css`, `settings.js` (display settings in localStorage, never in the save), `app.js` (thin view: draws what `handle` returns, drag via pointer events, tap-then-tap, keyboard).

Beats: a crate, a merge (a whole chain is one beat), a sweep or an accepted hand-over costs every customer at the stall one point of patience. Moving, swapping, selling and refused hand-overs are free. Customers in line start with full patience when they step up. A customer who leaves still pays for what they were handed. Patience is set when the customer is made: (build cost of the order + 3) x the day's slack x the archetype's share.

Interaction model: tap a good to pick it up (matches show a dashed ring and a +), tap a match to merge, tap an empty cell to move. Drag works the same and also swaps with a different good (tapping a different good changes the pick instead, so a swap is never an accident). Sell and Broom act on the picked-up good; Broom with nothing picked up arms the broom for the next tap. Keys: arrows, Enter, B, S, 1-9 crates, C cycles crates, Esc lets go.

## Standing decisions
No roguelike or deck-builder mechanics, easy to 100%, effects toggleable, collector welcome, no audio. Open questions Pb1-Pb3 are unanswered: patience in beats, no clock at all, Daily Market later (recommendations used).

Plan deviations: with five tiers the longest cascade is four merges (T1+T1, T2, T3, T4), so the plan's "5-link" Chain Master achievement and "6-link" perf test use four. Display settings live in localStorage (the Lexis rule), not in the save.

## Milestones
| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Board engine | `board.py` merge rules, cascades, legal-move solver, seeded RNG, text harness; tests for merges and no soft-lock | Done |
| 2 | Board UI | 5x6 grid, crates, drag + tap-tap + keyboard, Sell/Broom, merge highlights | Done (practice counter with a visible tally; checked at 1440x900 and 360x740) |
| 3 | Customers and orders | Queue, patience in beats, delivery, payout, 4 archetypes, order generator with a reachability test | Done (a day opens, three customers at the stall, hand-overs by tap, drag or D; a greedy bot clears the ten days) |
| 4 | Market day loop | Day start/summary, coins, stall upgrades, 10-day campaign, 3 festivals. First complete playable game | Not started |
| 5 | Combos, streaks, festivals | Order combo, cascade bonus, all 6 festivals with previews, personal-best badges | Not started |
| 6 | Standard kit + pledge tests | Save widget, settings, confirm dialog, tutorial, mobile dock/HUD, changelog, info panel, pledge tests | Not started |
| 7 | Achievements + story | 14 achievements, panel and toast, regulars, story toggle | Not started |
| 8 | Own-folder wrap-up | Favicon, Desktop boot (`pc-config.json`, `pc.html`), this table, tag | Not started |
| 9 | Daily Market (optional) | Not part of this build | Not started |
| 10 | Hub registration | BLOCKED ON NOY2; not done in this folder | Blocked |

## Working conventions
Commit + tag per milestone: `git commit -m "Milestone N: <name>"`, then `git tag pocket-bazaar-milestone-0N`. Tests: `python3 -m pytest -q games/pocket-bazaar`. Lint: `python3 -m flake8 games/pocket-bazaar --extend-ignore=E501`. Local Python is 3.9, Pyodide's is 3.12: no 3.10+ syntax.
