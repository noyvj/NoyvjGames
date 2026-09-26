# Pocket Bazaar — Groundwork Plan (Round 3 M4)

Status: PLAN ONLY. No `games/pocket-bazaar/` folder exists yet. Once approved, this becomes the seed for `games/pocket-bazaar/CLAUDE.md` (per `game-template.md`).
User answer (Round 3, M item 4): "yes, i always loved these but they had the stupid energy limits and microtransactions." Taste rule (standing): fun first, no lesson. No BCM tag (personal project). Working title only.

**Shared baseline:** `overclock-plan.md` section 4 (save, settings, achievements, changelog, tutorial, confirm dialog, mobile dock/HUD, colorblind rules, test harness, feedback) and section 5 (hub integration) apply with slug `pocket-bazaar`. Section 12 lists only what differs.

## 1. The pledge (binding design rules, from the user's answer)
This genre's usual business model is what the user disliked. These are hard constraints, not preferences, and each has a test or audit (section 11):

1. **No energy, lives, stamina, hearts or any "you can only do N things, then wait or pay" resource.** The only limit on how much you can play is how long you want to.
2. **No microtransactions.** No real-money purchases, no premium currency, no "gems", no paid boosters, no pay-to-skip, no pay-for-more-board. There is one in-game currency (coins) that is earned only by play.
3. **No timers that gate play.** No "wait 4 hours for the oven", no cooldown on the merge crates, no daily-reset lockouts, no "come back tomorrow" walls. Customer patience is counted in **beats** (player actions), not seconds, so it cannot be raced by a clock and cannot expire while the player is away or the tab is backgrounded.
4. **No dark patterns.** No daily login rewards or streaks that punish missing a day, no fake scarcity or countdown banners, no loss-aversion nags, no "are you sure you want to leave?" guilt dialogs, no interstitial or rewarded ads inside the game, no notifications, no confusing near-miss offers, no randomised paid-style loot boxes (even with earned coins).
5. **No progress is ever lost to leaving.** The board and the day state are saved on every action. Closing the tab mid-day resumes exactly.
6. **The only ads are the hub's existing labeled footer bar** (`ad-bar.css`), unchanged, non-interactive with the game, never gating anything.
7. **Fair by construction.** Every day is solvable: the board can never soft-lock (section 5.4), and difficulty scaling is visible ("this festival is harder"), not hidden rubber-banding meant to sell help.

## 2. One-line pitch
A tiny market stall: customers ask for goods, you merge basic goods on a small board into better ones, hand them over before customers lose patience, and chain fulfilments into combos, in a 3-5 minute market day.

## 3. Concept
A merge board (merge-2 game) sits above a queue of customers. Each customer wants 1-3 specific goods at specific tiers ("a level-3 scarf and a level-2 candle"). You tap crates to place basic goods on the board, merge two identical goods into the next tier, and drag finished goods onto the customer. Fulfil orders for coins and combos. The day ends when the last customer has been served or has left; a summary shows earnings, best combo and a star rating. Coins buy permanent stall upgrades and decorations. That is the whole loop; the fun is snappy merging, the small puzzle of "which goods do I need in which order", and the pleasure of a satisfied crowd.

The arcade feel comes from combos and pace, not from a clock: beats advance when you act, so the game feels quick when you play quickly and infinitely patient when you stop to think.

## 4. Stack
- Default: Python via Pyodide, plain HTML/CSS, no build step, run via `python -m http.server`.
- All rules in pure Python (`board.py`, `orders.py`, `festival.py`, `game.py`); no per-frame Python. Turn/beat-based, so the **stack's limits (no audio, no real-time precision timing) do not matter here**: the design is intentionally free of both. Feedback "juice" is CSS transform/transition and short particle-free effects, all disabled under reduce motion. Because there is no audio, satisfying feedback is visual (a pop, a glint on a merge, a coin counter tick) and textual ("Combo x3!").
- Rendering: DOM grid of buttons (5 columns x 6 rows). Pointer-event drag plus a tap-then-tap alternative (always supported, also the keyboard path).
- **Honest limit:** merge boards are drag-heavy; native HTML5 drag events are unreliable on touch, so pointer events are used and tested at 375px.

## 5. Core game design

### 5.1 The board
- 5x6 grid (30 cells) at launch; a stall upgrade adds a 6th column later.
- **Goods** belong to **families** (Produce, Textiles, Ceramics, Spices, Sweets at launch) with 5 tiers each (T1 ... T5). Two identical goods (same family and tier) merge into one tier-up good in the cell the player drops on. T5 goods are "showpieces" and cannot merge further; they sell for a large amount or fulfil top orders.
- **Bonus merge:** merging three or more identical goods in one move (place a third next to a pair, all adjacent) gives a tier +2 (a small skill reward, no randomness).
- **Crates** (one per active family) each show a stack of basic goods; tapping a crate places a T1 good in the first empty cell (or the cell you tap next). Crates are **unlimited and free**. The board's 30 cells are the only pacing pressure, which is a spatial puzzle, not a wall.
- **Special items:** **Broom** (clears one cell for free, unlimited but each use is a beat), **Scales** (reveals the next tier's family art, purely informational), **Wildcard** goods (earned through combos, substitute for one merge). All earned in play.

### 5.2 Customers and orders
- A **market day** has a fixed number of customers (8 at first, up to 16 later), shown as a short queue with 3 visible at a time.
- Each customer has: archetype, an **order** (1-3 goods with tiers), **patience** (in beats), and a **payment** (coins plus a tip if fulfilled quickly).
- Archetypes (each a small rule twist, all visible on the customer card):
  - **Regular**: standard patience; grows a "relationship" across days; small story lines.
  - **Haggler**: pays 50% more but has short patience.
  - **Critic**: wants an exact tier (no higher substitute).
  - **Bulk Buyer**: one big order of the same T1/T2 goods (an easy source of combos).
  - **Child with a coin**: tiny order, huge tip, patient.
  - **Rush Crowd**: three customers that arrive together with linked orders.
  - **Tourist**: accepts any tier of a family, pays little.
- **Patience:** counted in beats. A beat is one merge, one crate tap, one broom use, one delivery attempt. The queue shows a patience bar and a number. When patience reaches 0 the customer leaves with a polite line; the day continues. There is no punishment beyond the lost payment and a broken combo.
- **Delivering:** drag a good onto the customer (or tap good, tap customer). Wrong goods are rejected with a plain reason, never a beat cost.

### 5.3 Combos and streaks
- **Order combo:** delivering orders in a row without any customer leaving increases a multiplier (x1 to x3), shown as a number with a pip row.
- **Merge chain:** a merge that creates a good that immediately merges again (a cascade with an adjacent match) gives a coin bonus per link. Cascades are automatic and deterministic.
- **In-day only.** Combos reset each market day. There is no cross-day streak that can be lost, no "login streak", and no reward for playing on consecutive real days. The only cross-day records are **personal bests** (best combo, best day earnings), shown with the shared `personal-best.css` badge.

### 5.4 No soft-lock
- If the board is full and no merge is available, **Sell** is always allowed: drag any good to the Sell stall for a small coin amount (never zero). Also the Broom is unlimited. So a stuck state is impossible; a test asserts that from any reachable board state at least one legal move exists.
- The order generator **never asks for an unreachable good**: it builds orders from tiers achievable with the current board size and family set (checked by a solver-style test).

### 5.5 Festivals (rotating modifier)
Each market day carries one **festival** modifier, chosen by the seeded schedule in order (day number modulo the list, so it rotates predictably and can be previewed the day before). No real clock, no expiring events. Launch examples (invented names, culturally generic):
- **Lantern Night:** Ceramics goods sell for +50%; Rush Crowd customers appear.
- **Harvest Fair:** Produce crates give T2 goods half the time; Critics are more common.
- **Kite Day:** the board is 5x5 (fewer cells) but every combo starts at x2.
- **Slow Market:** patience +50%, payouts -20%. A relaxed day.
- **Twin Day:** every merge that makes a T3 also spawns a free T1 nearby.
- **Bargain Hunt:** only Haggler customers, big payouts, short patience.
The festival is shown on the day's start card and is always previewed for the next day in the summary. Later, the shared `shared/seasonal-events.js` groundwork (TODO-NEXT W-4) can map real-date events to festivals with the user's "15 minutes to get a taste" rule; the stand-in event rule applies.

### 5.6 Progression
- **Coins** buy **stall upgrades** (permanent, all small): a larger board column, a "second-best price" scales upgrade for T3 goods, a display shelf that holds one extra good (a persistent staging cell), a bigger queue preview, and a **broom polish** that gives a tiny coin refund.
- **Decorations** (cosmetic only): awnings, signs, shop cats, banners. No gameplay effect. They are the coin sink for players who have everything.
- **Renown** (a slow-filling bar by fulfilled orders) unlocks new families and new customer archetypes.
- **Modes:** Market Days (campaign of ~30 hand-tuned days), Free Stall (endless days with seeded festivals, no goals), and a Daily Market later (date-seeded day, same orders for everyone, reuses Signal's daily-seed + archive pattern) with an optional opt-in leaderboard for best daily earnings via `app/leaderboards.py` and `shared/leaderboard.js`.

## 6. Session shape
Target: **3-5 minutes per market day.** The day has a defined end (customer count reached), the summary is one screen, "Next day" is one tap, and there is never a wall between days. A session can be one day or ten.

## 7. Determinism
Everything random (crate spawns beyond T1, customer order lists, festival tie-breaks, wildcard drops) flows through a seeded PRNG stored in state, so a saved day resumes exactly and tests are exact. Crate spawns are always T1 (predictable), so there is little randomness: the luck is in customer draws, not in the merge feel.

## 8. Data model
```json
{
  "schema": 1,
  "meta": {
    "coins": 0, "renown": 0, "days_played": 0,
    "upgrades": [], "decorations": [], "families_unlocked": ["produce", "textiles", "ceramics"],
    "regulars": {"mira": {"visits": 0, "bond": 0}},
    "best": {"combo": 0, "day_earnings": 0, "best_day_stars": 0},
    "achievements_earned": {}
  },
  "day": null,
  "settings": {"text_scale": 1, "reduce_motion": false, "story_text": true, "input": "auto"}
}
```
`day` is `null` between days, otherwise `{"number", "festival", "board": [[cell...]], "queue": [customer...], "served": 0, "coins_today": 0, "combo": 0, "beat": 0, "rng": {"seed", "draws"}}`. `cell` is `null` or `{"f": family, "t": tier}`. Saved every action. Old saves tolerated; `achievements_earned` written and never read back. No field in the save relates to real time.

## 9. Content needs
- Claude drafts: 5 families x 5 tiers (names, glyphs), 7 customer archetypes, ~12 regulars with short arcs, 6 festivals, ~40 decorations, ~30 customer lines. User vetoes tone.
- Story text (regulars' stories, banter) is switchable with the shared story toggle; nothing needed to play is ever hidden. `shared/story-chapters.js` can carry a "the stall through a year" thread.
- Launch minimum for a complete game (Milestone 4): 3 families, 4 archetypes, 10 days, 3 festivals, 6 upgrades.

## 10. UI sketch (words)
- **Top:** coins, day number, festival chip, combo pips.
- **Queue:** three customer cards (glyph face + name, order icons with tier pips, patience bar and number).
- **Board:** 5x6 grid, each good drawn as a glyph in a distinct shape per family with tier pips (colour is decoration only). A highlight shows legal merge partners on select.
- **Bottom (mobile dock, `shared/mobile-dock.js`):** the crates row and Sell stall/Broom. The board stays visible above. HUD (`shared/mobile-hud.js`): coins, combo, customers left.
- **End of day:** summary card (earnings, best combo, stars, regulars' notes), next festival preview, "Next day" and "Upgrades".
- Keyboard: arrows move a cursor over the board, Enter picks up/drops, `C` cycles crates, `B` broom, `S` sell, `?` help.

## 11. Testing approach and no-dark-patterns audit
- pytest sim harness: merge rules (pair, triple bonus, T5 cap), cascade determinism, legal-move existence from every reachable state (fuzz), order generator never asks for unreachable goods, patience decrements only on player beats, festival rotation, save round-trip mid-day, old-save tolerance.
- **Pledge tests (binding):**
  - A source scan asserts no code path in the sim or UI reads the real clock for gameplay (`Date`, `time`, `datetime` usage is banned outside the changelog banner and the optional daily seed).
  - A string lint fails the build on player-visible words `energy`, `lives`, `stamina`, `refill`, `gems`, `premium`, `watch an ad`, `limited time`, `hurry` (except the word "hurry" in customer flavor lines, whitelisted by id).
  - A state-shape test asserts the save contains no timestamps or cooldown fields.
  - A manual pre-release checklist item: a fresh reviewer plays a full session and lists anything that felt like pressure to keep playing or pay; any item fails the release.
- Worst-case perf: a full board with a 6-link cascade under a step-time ceiling.
- Live checks via the shared `hub-dev-server`: 375px thumb play, tap-tap and drag, keyboard-only, text scale, reduce motion, offline.

## 12. Baseline checklist pointer (what differs)
Use `overclock-plan.md` sections 4 and 5, slug `pocket-bazaar`. Specifics:
| Item | Note |
|---|---|
| Save | Every action saves; no real-time fields |
| Confirm dialog | Reset progress and Sell a T4/T5 good only (never guilt dialogs on leaving) |
| Mobile dock / HUD | Crates + Sell/Broom in the dock; coins, combo, customers in the HUD |
| Colorblind | Families by glyph shape + letter, tiers by pips and numbers; combo by number |
| Story | Shared toggle hides regulars' stories/banter; mechanics text stays |
| Real-world examples | Not applicable (fiction); if a later festival uses a real date, it follows the seasonal-events groundwork |
| Light theme | Stall and board both render on the light palette; verify goods contrast |
| Leaderboard | Optional Daily Market board, opt-in only |
| Ads | Hub footer ad bar only, unchanged (pledge rule 6) |
| Info panel | "How the stall works" plus a plain-language "What this game will never do" list (the pledge), shown in About |

## 13. Achievements (14)
1. Open for Business — finish your first day.
2. Satisfied Customer — deliver 10 orders.
3. Chain Master — a 5-link merge cascade.
4. Full Combo — x3 combo.
5. Perfect Day — no customer leaves.
6. Showpiece — make your first T5 good.
7. Regular — bond with a regular to level 3 (each regular has a hidden variant).
8. Bargain Blitz — clear a Bargain Hunt day.
9. Well Stocked — buy all stall upgrades.
10. Decorator — place 10 decorations.
11. Twin Day Twins — 5 free T1s from Twin Day in one day.
12. All Festivals — play every festival.
13. Quiet Stall — finish a Slow Market day with no combos (a joke about slow play).
14. 30 Market Days.
Follows `ACHIEVEMENTS-SYSTEM-DESIGN.md`. Achievements never reward time spent or login frequency.

## 14. Milestones
Commit + tag each: `git tag pocket-bazaar-milestone-0N`. Milestones 1-4 ship a complete, playable game.

| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Board engine | `board.py`: merge rules, cascades, legal-move solver, seeded RNG, text harness. Tests: merge, no soft-lock | Not started |
| 2 | Board UI | 5x6 grid, crates, drag + tap-tap + keyboard, Sell/Broom, merge highlights | Not started |
| 3 | Customers and orders | Queue, patience in beats, delivery, payout, archetypes (4), order generator with reachability test | Not started |
| 4 | Market day loop | Day start/summary, coins, stall upgrades, campaign of 10 days, festivals (3). **First complete, playable game** | Not started |
| 5 | Combos, streaks, festivals | Order combo, cascade bonus, all 6 festivals with previews, personal-best badges | Not started |
| 6 | Standard kit + pledge tests | Save widget, settings, confirm dialog, tutorial, mobile dock/HUD, changelog, info panel with the pledge list, feedback, pledge tests | Not started |
| 7 | Achievements + story | 14 achievements, panel/toast, regulars, story toggle wiring | Not started |
| 8 | Hub integration | Title card, thumbnail, favicon, `sw.js`, manifests, root CLAUDE.md row, dev logs, tag | Not started |
| 9 | Daily Market (optional) | Date-seeded day, archive, opt-in leaderboard board | Not started |

## 15. Risks
- **Sliding into the genre's habits under pressure to add content.** Mitigation: pledge tests are in the test suite and the pre-release checklist; any "just one timer" proposal needs an explicit user decision.
- **Merge-drag feel on touch.** Mitigation: prototype at Milestone 2 at 375px before building customers.
- **Too little to spend on.** Without energy and premium currency there is nothing to monetise, so the coin sink has to be genuinely fun: decorations and unlock breadth matter. Mitigation: campaign of 30 days, 40 decorations.
- **Patience-in-beats feeling too easy or turn-based.** Mitigation: tune with bots; the Rush Crowd and Haggler archetypes create pressure without a clock.
- **Sameness with existing merge games.** Mitigation: the customer-order framing, festival rotation and no-soft-lock guarantee are the differentiators; keep the crate/board feel simple and quick.

## 16. Open questions for the user
1. Confirm patience counted in beats (recommended: cannot expire while away, matches the pledge and the stack) rather than a visible real-time countdown.
2. Should there be any real-time "Rush" mode later, strictly optional and off by default, or is a clock banned outright? (Recommend banned for launch.)
3. Comfortable with a Daily Market later, given no daily-login rewards are allowed either way?
