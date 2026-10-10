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
| `orders.py` | customers: archetypes (Regular, Haggler, Critic, Bulk buyer; renown adds Child with a coin, Tourist and Rush crowd), order matching, payment, patience from build cost, the order generator and its reachability check |
| `festival.py` | the festival a day carries (by day number alone): all six: Slow Market, Harvest Fair, Twin Day, Kite Day, Lantern Night, Bargain Hunt (previewed the day before) |
| `renown.py` | the renown bar: Child 10, Tourist 30, Spices 50, Rush crowd 75, Sweets 110; one point per customer served plus a point per star |
| `shop.py` | six permanent stall upgrades bought with coins (queue preview, broom polish, tip jar, display shelf, fine scales, wider counter) |
| `days.py` | the day recipes: first ten days hand-tuned, then Free Stall curve (capped at 16 customers, tier 5) |
| `day.py` | one market day: counter, queue (three at the stall, the rest waiting), beats, patience, hand-over, leaving, serving, summary |
| `achievements.py` | the 14 achievements, each a number (have/need) computed from facts; `achievements.json` is the hub manifest; the first three unearned are shown as goals, in any order |
| `regulars.py` | twelve named regulars (three step up per day in a fixed rotation), bond levels at 1/2/3 visits (M-4b-11), three story lines each |
| `decorations.py` | 40 cosmetic decorations in six slots, a coin sink with no effect on play |
| `pledge.py`, `info.py` | the pledge text (the only file allowed to name what the game rules out) and the About page content |
| `game.py` | the one entry point: `handle(json)`, `get_state()`, `load_state()`; state is saved with only non-default keys |

View files: `index.html`, `style.css`, `settings.js` (display settings in localStorage, never in the save), `app.js` (thin view: draws what `handle` returns, drag via pointer events, tap-then-tap, keyboard).

Combos: serve orders in a row with nobody leaving and the order multiplier steps x1, x2 (after two), x3 (after four); it multiplies the payment, not the tip. Kite Day starts at x2. A customer leaving resets it for the rest of that day only (nothing carries over; the personal bests are the only record). Every fourth order in a row puts a wildcard on the counter. A chain pays 2k coins for link k from the second link on. Rush crowds pay half their total again if all three are served.

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
| 4 | Market day loop | Day start/summary, coins, stall upgrades, 10-day campaign, 3 festivals. First complete playable game | Done (day start card with festival, summary with stars and tomorrow's festival, shop, Free Stall after day 10) |
| 5 | Combos, streaks, festivals | Order combo, cascade bonus, all 6 festivals with previews, personal-best badges | Done (also wildcards, renown unlocks and the three extra archetypes) |
| 6 | Standard kit + pledge tests | Save widget, settings, confirm dialog, tutorial, mobile dock/HUD, changelog, info panel, pledge tests | Done (opening screen, save widget, tutorial, What's New + banner, About with the pledge list, confirm only for selling tier 4-5 and erasing; `tests/test_pledge.py`). The shared mobile dock and HUD are deliberately not used: the whole counter, the stats and the crates fit one 360x740 screen, so nothing needs pinning |
| 7 | Achievements + story | 14 achievements, panel and toast, regulars, story toggle | Done (also a visible three-goals list, 40 decorations, regulars page; story lines hidden by the shared story toggle) |
| 8 | Own-folder wrap-up | Favicon, Desktop boot (`pc-config.json`, `pc.html`), this table, tag | Done (code-drawn favicon, Desktop boot, 236 tests) |
| 9 | Daily Market (optional) | One plain market day per UTC date, archive, tally grid; follows the pledge (no login reward, no streak, no missed-day penalty). The opt-in leaderboard is a separate backend job (hooks only) | Done (see "Daily Market") |
| 10 | Hub registration | BLOCKED ON NOY2; not done in this folder | Blocked |

## Daily Market
`market.py` makes one market day per UTC date from the date text alone (an FNV hash of "pocket-bazaar-market-v1|date|attempt" seeds the game's own `Rng`; no clock, no random source, no server, and no date library: the calendar maths is plain arithmetic). The date picks one of the campaign's day recipes (day 2 to 10 via `days.spec`), a festival, the crates (the three base families, plus Spices or Sweets on about a third of dates) and optional Child/Tourist customers. It is played on a fixed stall: width 5, no shop upgrades, no shelf, no regulars, no renown archetypes. **Fairness bar:** before a date's market is accepted every order must be buildable on that day's counter (`orders.order_is_reachable`) and a plain greedy player (`marketbot.py`, mirroring `tests/bot.py`) must serve at least 75% of the customers; a candidate that fails is replaced by the next one derived from the same date (about 1 date in 25 needs a second try).
- **Pledge:** it pays nothing extra and changes nothing else: no coins, renown, tally, flags, achievements or personal bests move (`Stall.market` marks the open day as a market; `_apply` skips every stall update; selling says "off the counter" with no coin figure). The only record is the best result per date. No streak counter, no "missed" count, no countdown, no reward for opening it. Any date from 2026-10-01 to today can be played in any order. `tests/test_market_pledge.py` guards all of it.
- **The one clock read** is `today()` in `market.js` (`new Date().toISOString().slice(0, 10)`), which tells the engine which date to build; `app.js` and `settings.js` still contain no `Date` at all (tested). `app.js` adds `request.today` to every request; the engine keeps it only as a runtime value (`game._today`), and no date means no market panel.
- Only from the closed stall: starting a market while a campaign day is open is refused ("Finish the open day first"); a market and a campaign day are never open together. `reset` (start the stall over) keeps the market results because they belong to dates.
- Save keys, written only when non-default: `market_days` ({date: {stars, served, total, coins}}, best result per date, validated entry by entry) and `market_day` ({date, day}, the open market, rebuilt through `Day.from_dict` with the date's own families and rules). A campaign `day` wins if a save holds both. Old saves load unchanged.
- UI (`market.js`, panel `#market-panel` inside the closed-stall card, below the shop): Today's market, a month-calendar archive (stars as symbols, not colour), a plain sentence tally and a small grid of the last 120 days; a banner `#market-open-banner` while a market is open; a result card after it. The Desktop boot shows the same panel inside the stage (the Desktop layout itself is for wide windows only, as before).
- **Leaderboard: NOT built.** Hooks only: `market.leaderboard_entry(date, record)` (view `market.entry` after a result) and `PocketBazaarMarket.leaderboardHook` in `market.js`. A future board takes `{board: "pocket-bazaar-market", date, score, stars, served}`.
- `sw.js` / `offline-manifest.json` (hub files, not edited here) must precache `games/pocket-bazaar/market.py`, `marketbot.py`, `market.js`.
- Tests: `tests/test_market.py` (calendar arithmetic against datetime, determinism, 300 consecutive dates fairness-proven, bot parity, flow, saves and tampering), `tests/test_market_pledge.py`, `tests/test_market_browser.py` (calendar to result card).

## Working conventions
Commit + tag per milestone: `git commit -m "Milestone N: <name>"`, then `git tag pocket-bazaar-milestone-0N`. Tests: `python3 -m pytest -q games/pocket-bazaar`. Lint: `python3 -m flake8 games/pocket-bazaar --extend-ignore=E501`. Local Python is 3.9, Pyodide's is 3.12: no 3.10+ syntax.

## Pre-release checklist (manual, binding)
A fresh reviewer plays one full session (a few days) on a phone and on a desktop, then lists anything that felt like pressure to keep playing or to pay: a number that looks like a countdown, a reward that depends on coming back, a dialog that argues with leaving, a price in anything but coins, a thing that quietly got harder. Any item fails the release. Also check at 360x740: the counter, queue, crates and Sell/Broom are on screen at once with no scrolling.

## Phone layout note
Under 600px the title and the row of buttons (Tutorial, What's New, Settings, About) and their panels move below the counter (CSS `order`), the board shrinks to the screen height, and short labels appear. The shared theme pill is not used (the Settings panel has the theme switch).

## Plan deviations (for the owner)
- Chain Master and the cascade perf test use four links, not five or six: five tiers allow at most four merges in a chain.
- Decorator is "own 10 decorations" (buying puts one out in its slot; there are only six slots).
- Regulars bond at 1, 2 and 3 visits (they were 1, 3 and 5 until M-4b-11, the owner's answer to Pb5) and rotate three a day (each is back every fourth day), so the first bond level 3 comes on day 10 and the last of the twelve on day 13 when every visit is served (a greedy bot that misses a few customers gets the first one on day 11). Old saves keep their visit counts, which now simply count for more; the plan's "hidden variant" per regular is not built (nothing in the game is hidden).
- Display settings are in localStorage, not the save (the Lexis rule). The shared mobile dock and HUD are not used (nothing scrolls away).

## Desktop boot
`pc.html` is generated (never edited by hand) from `index.html` and `pc-config.json` by `scripts/generate-pc-pages.py`; `pc.css` and `pc.js` are this game's own. Layout: the stats strip across the top of the stage; the stage is one panel with the customers in a column beside a counter that uses the window's height; the side column holds the crates (stacked), Sell and Broom, the pick-up hint and the tally; Achievements, Regulars, Settings and About are windows (icons and the Menu); `data-phase` on `#game` hides the crates while the stall is closed. The Desktop tutorial lives in `pc.js`. M-4b-11 (Pb4): the stats moved from a strip above the stage into the top of the (wider, 16.5-24rem) side column as a 2x2 block, `.how` (How the stall works) moved to the side column, the bought display shelf sits in the left column under the waiting line (`#counter` is `display: contents`) and, under 800px of height, the customer cards put their kind label on the name row; the board is sized from `100vh - 17rem`. Result: cells about 68px at 1024x700 (about 66px with the shelf, six columns and five crates) and 101px at 1440x900, with no scrolling inside the open-day stall panel. The closed-day card and the shop still scroll inside the panel when long, by design.

## Hub registration (not done here)
Milestone 10 belongs to the owner of the hub files: title card and tags, thumbnail, `sw.js` precache (the game's files plus `pc.*`) with a `SW_VERSION` bump, `offline-manifest.json`, the `game-*.json` files, achievements page, `admin.html`, `shared/site-settings.js`, `sitemap.xml`, share cards and JSON-LD (`scripts/generate-share-cards.py`, which also adds the share block to both pages' heads), `scripts/perf-budget.json`, the smoke tests and the root `CLAUDE.md` row. Until then the shared stats endpoint answers 404 for this game (a harmless read the achievement Share button makes).
