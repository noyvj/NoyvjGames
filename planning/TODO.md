# Site-Wide TODO

**Progress: 347/747 items checked off (46.5%).** Recompute with `grep -c "^\s*- \[[ x]\]" planning/TODO.md` (total) and the same with `\[x\]` (done) as items land. The count is high because every cross-game rollout item (Z section) is broken into one checkbox per game — see the note at the top of that section. `TODO.md` is the working title on purpose — the user will rename it once the original `planning/TODO.md` is fully finished, so the two never collide.

Built from your labeled answers in `planning/IMPROVEMENT-IDEAS-ROUND-2.md` (30 ideas per section this round, up from 20 in round 1 — sections A-L per game, M new-game concepts, Z cross-game, Y hub-shell, X the Warframe tracker). Same rules as round 1's `TODO.md`: "yes" items land here, "later"/genuinely-parked items go to `LATER.md`, open questions only you can answer go to `FOR-YOU.md`, "no" answers are dropped entirely (not carried anywhere). Section X (the Warframe tracker) originally routed to its own local `warframe_build_tracker/TODO.md` — as of 2026-09-20 that file has been deleted and everything moved into the **X** section here instead, at your request.

A few round-2 answers flagged a per-game idea as "shouldn't this be site-wide?" (A10, A22, A26) — those are folded into the Games (Z) section below instead of listed under their originating game, with a note pointing back to where they came from.

Two round-2 answers (Z3, Z5) explicitly rejected building a *shared module* for meta-progression and challenge-mode patterns ("it is better to have all the games take the progression they naturally do rather than building a one-size-fits-all standard") — every per-game idea in this doc that proposes its own meta-progression or hard-mode variant (SOL, Canopy, Herd, Drift, Continuum, Grid, Tide) is still accepted, just built independently per game, not through one shared pattern.

Order: **Z. Games** (cross-game) → **Y. Home** (hub shell) → per-game sections in the usual listing order → **M. New game concepts** → closing tasks.

---

## Site-wide goal: cross-game aggregate-stats backend (Z1)

*(Origin: Z1, accepted — "yes.")* A shared backend endpoint several other accepted ideas below depend on (Grid's C11/C15 comparisons, Canopy's community-forest comparison, SOL's compare-my-run/leaderboard, Continuum's benchmark-your-city, Herd's community stats extensions). One real decision and one real build, instead of every game separately floating its own "needs a new endpoint" caveat. Build this before touching any per-game item below that's marked "(needs Z1)."

- [x] Design and build the shared cross-game aggregate-stats endpoint on the existing FastAPI Cloud + Neon backend — decide what it aggregates (per-game average scores/completion stats, achievement rarity %, etc.) once, reused by every dependent feature below. Built: `/stats/games`, `/stats/games/{id}`, `/stats/games/{id}/percentile`, `/stats/achievements` (app/stats.py, commit 9266ba0; small-N suppression at 3, whitelist in `STATS_FIELDS`). Not yet deployed.

---

## Z. Games (things worth doing across many/all games)

**Every item below that applies "to every game" is broken into one checkbox per game, on purpose — so a rollout can't silently skip one the way a single flat checkbox could hide.** The 12-game list, in the usual order: SOL, Canopy, Grid, Tide, Aftermath, Herd, Thaw, Loop, Drift, Trade Empire, Continuum, Le Champ de Mots.

- [ ] Z2: A consistent "last played" per-game timestamp, client-side, surfaced on hub title cards (distinct from the "last updated" site badge).
  - [ ] SOL
  - [ ] Canopy
  - [ ] Grid
  - [ ] Tide
  - [ ] Aftermath
  - [ ] Herd
  - [ ] Thaw
  - [ ] Loop
  - [ ] Drift
  - [ ] Trade Empire
  - [ ] Continuum
  - [ ] Le Champ de Mots
- [ ] Z4: A consistent keyboard-shortcut convention (`?` for help, `Esc` to close any open panel) — first decide the shared convention, then audit/align each game:
  - [ ] Decide the shared convention (which keys, which actions)
  - [ ] SOL
  - [ ] Canopy
  - [ ] Grid
  - [ ] Tide
  - [ ] Aftermath
  - [ ] Herd
  - [ ] Thaw
  - [ ] Loop
  - [ ] Drift
  - [ ] Trade Empire
  - [ ] Continuum
  - [ ] Le Champ de Mots
- [x] Z6: A shared CSS utility/pattern for "new personal best" badges:
  - [x] Build the shared utility (`shared/personal-best.css`, 2026-09-21)
  - [x] Migrate SOL's existing bespoke version (n/a — SOL has no personal-best concept, checked live)
  - [x] Migrate Canopy's existing bespoke version
  - [x] Migrate Tide's existing bespoke version
  - [x] Migrate Thaw's existing bespoke version
  - [x] Migrate Grid's existing bespoke version (n/a — Grid has no personal-best concept, checked live)
- [ ] Z7: A genuine "replay value" audit — which games still lack any reason to play twice, and whether that's fine (teaching tools) or worth a light meta-progression pass. **You asked to make a new "ideas" list off the result of this one** — treat the audit's findings as the seed for a future targeted ideas round on replayability specifically, once this audit runs.
  - [ ] SOL
  - [ ] Canopy
  - [ ] Grid
  - [ ] Tide
  - [ ] Aftermath
  - [ ] Herd
  - [ ] Thaw
  - [ ] Loop
  - [ ] Drift
  - [ ] Trade Empire
  - [ ] Continuum
  - [ ] Le Champ de Mots
  - [ ] Write the follow-up replayability ideas round from this audit's findings
- [ ] Z8: A shared "export my progress" helper/module for the portable-progress-code pattern:
  - [ ] Build the shared helper
  - [ ] Migrate Aftermath's existing E12 export to it
  - [ ] Apply to SOL's A17 export idea (see per-game section) using the shared helper, not a one-off
- [x] Z10: A consistent "difficulty variant active" icon/badge on a game's title card when it has one enabled (single hub-side feature, reads each game's own difficulty flag).
- [ ] Z11: A shared "narrative log" component (a small dated feed of things that happened):
  - [ ] Build the shared component
  - [ ] Migrate Continuum's existing ongoing-log to it
  - [ ] Build Thaw's proposed scientist's-log (G19) on it
  - [ ] Build Le Champ de Mots' report-confirmation flow (L14) on it
- [ ] Z12: A quick audit confirming the achievements/settings/changelog toggle buttons land in a consistent order/position across every game's toolbar. Audited via `grep` across every game's `index.html`: 11/12 already consistent (Tutorial -> How to Play -> [Info Page ->] Achievements -> Changelog -> [game-specific toggles] -> Settings always last, whether in one `.game-toolbar` or split across two adjacent ones like Grid/Tide's difficulty-toggle row). **Aftermath was the one real outlier** (Settings landed in the first toolbar near the top, Achievements/Changelog got stranded in a second toolbar after a block of narrative content) — fix dispatched separately, see its own line below.
  - [x] SOL
  - [x] Canopy
  - [x] Grid
  - [x] Tide
  - [x] Aftermath (real inconsistency found — fix in progress, see AI-COORDINATION.md)
  - [x] Herd
  - [x] Thaw
  - [x] Loop
  - [x] Drift
  - [x] Trade Empire
  - [x] Continuum
  - [x] Le Champ de Mots
- [ ] Z13: A real "onboarding survey" — a single optional first-visit prompt (subjects of interest, quick vs. deep games) feeding the hub lobby's tag-filter defaults.
- [ ] Z14: A shared "time since last played" freshness-badge helper (groundwork for Z2).
- [ ] Z15: A genuine screen-reader accessibility audit (ARIA labels, focus order) across at least the achievements/settings panels:
  - [ ] SOL
  - [ ] Canopy
  - [ ] Grid
  - [ ] Tide
  - [ ] Aftermath
  - [ ] Herd
  - [ ] Thaw
  - [ ] Loop
  - [ ] Drift
  - [ ] Trade Empire
  - [ ] Continuum
  - [ ] Le Champ de Mots
- [ ] Z16: Audit whether the other 11 games have an equivalent lightweight in-game bug/typo report affordance to Le Champ de Mots' existing one:
  - [ ] SOL
  - [ ] Canopy
  - [ ] Grid
  - [ ] Tide
  - [ ] Aftermath
  - [ ] Herd
  - [ ] Thaw
  - [ ] Loop
  - [ ] Drift
  - [ ] Trade Empire
  - [ ] Continuum
- [ ] Z17: A shared "comparison/benchmark" chart component with swappable reference-data sources:
  - [ ] Build the shared component
  - [ ] Migrate Grid's existing global-comparison line to it
  - [ ] Build Continuum's history-comparison idea (K13) on it
  - [ ] Build Herd's real-world % comparison on it
- [ ] Z18: A mobile-viewport audit at 320px (not just 375px), catching any edge-of-screen clipping the original mobile pass missed:
  - [ ] SOL
  - [ ] Canopy
  - [ ] Grid
  - [ ] Tide
  - [ ] Aftermath
  - [ ] Herd
  - [ ] Thaw
  - [ ] Loop
  - [ ] Drift
  - [ ] Trade Empire
  - [ ] Continuum
  - [ ] Le Champ de Mots
- [ ] Z19: A genuine "New Player" landing flow — a single guided "start here" recommendation (e.g. Canopy as a simple first pick). **Builds well on Z13 per your own note** — design them together.
- [x] Z20: A consistent emoji/icon-meaning audit, confirming no icon means two different things in two different games. Audited, no change needed: catalogued every bespoke (non-shared-toolbar) emoji across all 12 games' `game.py`/`index.html`/`style.css` and cross-referenced the full list — every emoji that recurs across 2+ games maps to the same real-world referent or theme in each (growth/renewable `🌱`, protection `🛡️`, industry `🏭`, water/flood `🌊`, warning `⚠`, money `💰`, stats `📊`/`📈`, etc.), the same "consistent reuse of an obvious real-world association" pattern already ruled non-colliding elsewhere in this file; the closest borderline cases (Tide's top-tier `🌊` adaptation badge vs. Aftermath's `🌊` flood-event icon; Grid/Drift's `🔥` "intensity toggle" vs. Aftermath's `🔥` heatwave-event vs. Continuum's literal hearth `🔥`) all stay within one literal referent (water, fire) rather than crossing into an unrelated or contradictory meaning, so none reach the "a player would plausibly notice and find confusing" bar the task sets.
  - [x] SOL — toolbar-shared icons only (🎓📖📋🏆⚙️) plus bespoke: 🌍 Overview, 🎛️ Governor Report, 📝 Build Plan, 🌳 Prestige Tree, 🧪 Sandbox mode, 📊 Stats & Share, colored circles/🪐🌕🔴🟠🪨⚪🟤 as literal planet icons, ♻️/🚀/🏙️/⚙️ as per-building construction floaters, ☑/☐/✕ build-plan checkboxes. No collisions.
  - [x] Canopy — bespoke: 🌱☀️🍂❄️ season icons, ⛰️ Highland Grove (locked area), 💰 economic specialization, 🦋 biodiversity specialization, 🏘️ stakeholder request badge, ⭐ adopted plot, 🌍 compare with other players, 💾 save-run slots, plus css icons (🤝📍✅❌💬👍👎📨🌲🪓🌱🌳) for the stakeholder-request/plot-type legend. No collisions.
  - [x] Grid — bespoke: fuel-source icons (⚫ coal, ☢️ nuclear, ☀️ solar), 🌱 "Renewable" / 🏭 "Fossil" / ⚛️ "Nuclear" mix labels, 🌦️ Weather Log, 🎖️ Career, 🔥 Steeper Demand Growth toggle, 🌩️ Weather Variability toggle, ⚠ aging-risk badge, plus css sidebar icons (🔁⚡💰🔌🛢️🚨🛠️♻️🔨🗑️🔧🌍📈). No collisions.
  - [x] Tide — bespoke: TIER_BADGES progression (⚪🧱🏗️🛡️🌊), 🦪/🗼 heritage-site sprites, ⛈️ storm surge, 🎉 fish-stock recovery, ✖ heritage site lost, 🐟 fish-yield meter, plus css icons (💰🧪🏖️🎣🌿). No collisions.
  - [x] Aftermath — bespoke: disaster-event icons (🌊 flood, 🔥 heatwave, 🌪️ storm, ⚡ infrastructure failure), CATEGORY_ICON (🌦️ weather / 🏗️ non-weather / 👥 social), 📜 Review Past Runs, 📌/📍 pin a savings goal, 🔓 skill unlocked, 💡 insight tips, 🕰️ "Memory of Run #", plus css icons (📦🧠📊🔄🔒✓, and a bespoke `⚔️` on the in-game "Resolve Event" button — a literal confront/battle icon, unrelated to and never co-displayed with the hub's shared `⚔` difficulty-badge convention). No collisions.
  - [x] Herd — bespoke: ♻️ Capture Systems, 🌿 Plant-Based Pivot, 📊 Report Card, 👍/👎 feedback, plus css icons (💰🐄💨⚖⚠🌡️🥦🌱🌾🚧🐮🐔) for the investment/measure legend. No collisions.
  - [x] Thaw — bespoke: 📓 Scientist's log, plus css icons (📊🛡️💰🌡️🧊📈📡⚠️) for stats/measure labels. No collisions.
  - [x] Loop — bespoke: chain-stage icons (🪨 Extract → 🏭 Manufacture → 📦 Use → 🗑️ Discard), loop-ring icons (♻️ Recycle, 🔄 Reuse, 🔧 Repair, 🔁 "Loop closed" banner), 🌐 Trade Link, 🚚/🚢 trade tiers, goods-category icons (📱👕🪑), 🔎 efficiency audit, 🗺️ supply map, ↩/⇢ flow labels, plus css (💰⛏️🌍). No collisions.
  - [x] Drift — bespoke: wellbeing-gauge icons (📋 service quality, 📊 economic health, 🔗 social cohesion), investment icons (🏠 Housing, 📚 Integration Services, 🛠️ Infrastructure), 🌟 "Model Region" recognition tier, 🌱 "Net-positive since round", 🔥 Accelerated Severity toggle, plus css (📈🌅💰🏘️⚖). No collisions.
  - [x] Trade Empire — bespoke: ⚠️ idle-ship warning, 🚀 "First automated ship" milestone, ★ "Veteran hauler" tag, 🚚 ship-arrival notice, plus css icons (🔬🛰️💰🗺️🎯🏗️📦🤖🧾🪐) for the tech/economy sidebar. No collisions.
  - [x] Continuum — bespoke: per-era worker icons (🌾🪵🪓🔥⚒️🏭🗺️🌱📜🛰️) and building icons (⛺🫙🔥🪨🌿🏛️🚰🏗️🚉🛞), ☠️ Hard Mode toggle, 📜 Civilization Summary, 📓 Founder's Log, 📊 City Views, 🔭/🔍/🛰 camera presets, 🖼 2D view, 📸 snapshot, plus css icons (🗓️👥🏠🍞🔨📚⚖🛡️🛠️). No collisions found — **read-only finding, not independently re-verified by Noyvj since `games/continuum/` is owned by that session; flagging for Noyvj to confirm independently rather than editing it directly.**
  - [x] Le Champ de Mots — bespoke: crop-growth-stage icons (🟤 seed → 🌱 sprout → 🌿 budding → 🌷 blooming → 🌻 automated), 💧 "drooping" (needs a review) legend, 🌾 "weeds" (known mix-up) legend, 🔊 pronunciation-concern report, 🗣️ liaison practice, minigame icons (⚡ Blitz, 🏁 Verb Racer, 👗 Boutique Dash, ☕ Café Rush), 🚗/🚙 racer markers, ❤ lives, section-hero icons (📖🔁📝🧩); notably `🔥` is explicitly *banned* from ever appearing in minigame fail/success text (existing test coverage), a deliberate avoidance of the "fire = danger/failure" association other games lean on. No collisions.
  - [x] Cross-check the full list for collisions once every game's icons are catalogued — done (see summary sentence above); zero genuine collisions found, no code changes made.
- [ ] Z21: A shared print-friendly CSS stylesheet for end-of-session summary screens:
  - [ ] Build the shared stylesheet
  - [ ] Apply to Canopy's Session Summary
  - [ ] Apply to Tide's session summary
  - [ ] Apply to Aftermath's run summary
  - [ ] Apply to Herd's report card
- [ ] Z22: Audit every game's "Reset progress" confirmation wording now that the shared `ConfirmDialog` exists, and decide migrate-for-consistency vs. intentionally-varied per game. *(Folds in A22's "shouldn't this be site-wide?" flag — SOL's own full-save-wipe confirmation is exactly this case.)*
  - [ ] SOL (`_confirm()`, predates the shared pattern)
  - [ ] Canopy
  - [ ] Grid
  - [ ] Tide
  - [ ] Aftermath (two-click confirm, predates the shared pattern)
  - [ ] Herd
  - [ ] Thaw
  - [ ] Loop
  - [ ] Drift
  - [ ] Trade Empire
  - [ ] Continuum
  - [ ] Le Champ de Mots
- [ ] Z23: A lightweight shared mechanism for a game to show different flavor text/art on real-world dates (an optional seasonal Easter-egg layer) — **you specifically want this event-based**, e.g. a week-long "holiday" event (a Christmas-themed Canopy tree-planting push earning a "Christmas 2026" profile badge). Design the shared mechanism with that kind of event in mind, not just a palette swap. Opt-in per game, not a mandatory rollout — no per-game checklist needed until a specific game opts in.
- [ ] Z24: A shared "what changed since you last played" banner (distinct from each game's own changelog panel):
  - [ ] Build the shared banner component
  - [ ] SOL
  - [ ] Canopy
  - [ ] Grid
  - [ ] Tide
  - [ ] Aftermath
  - [ ] Herd
  - [ ] Thaw
  - [ ] Loop
  - [ ] Drift
  - [ ] Trade Empire
  - [ ] Continuum
  - [ ] Le Champ de Mots
- [ ] Z25: A genuine save-portability audit — confirm every game's save-code payload size is still reasonable now that achievements/run-histories/changelogs have grown each save state. Measured every game via a driven long-session script against its own pytest harness rather than eyeballing: 10 of 12 are comfortably small (a few KB to ~166KB for a fully-played session, well within reason for an uncapped Postgres JSON column); found and fixed one real bug (Trade Empire's `sale_log` was unbounded despite only ever reading its last entry — ~110KB -> ~11KB for the same session); found one real-but-deferred issue (Drift's per-round history logs are unbounded and reach the hundreds-of-KB range in an extreme session, but a safe fix needs a small refactor rather than a one-line cap — Q17 in `FOR-YOU.md`); Continuum (read-only for this pass) has a similar but compounding pattern worth a closer look.
  - [x] SOL — clicked/bought through a long session via its own test harness: ~3.3KB. No change needed.
  - [x] Canopy — 400 ticks with plot activity: 19.3KB; `FOREST_LOG_MAX_ENTRIES`/`VALUE_HISTORY_MAX_POINTS` caps working as designed. No change needed.
  - [x] Grid — 500 rounds: 12.6KB; per-round histories uncapped but tiny (floats). No change needed.
  - [x] Tide — 600 seasons: 23KB; damage/tier logs uncapped but tiny, everything else already capped. No change needed.
  - [x] Aftermath — 300 events resolved in one run: 719 bytes; meta-progression history lives in `localStorage`, never rides the save payload at all. No change needed.
  - [x] Herd — 800 rounds: 4.8KB. No change needed.
  - [x] Thaw — measured to 60 rounds (7.1KB, small and capped `SCIENCE_LOG_MAX`); found a real but unrelated exponential-slowdown bug in `_auto_play_worst_case_region()` while doing this (each Advance Round gets ~1.3x slower past round ~50) — flagged as a separate background task, not a payload-size issue so left out of scope here. No change needed to save size.
  - [x] Loop — 300 cycles: 2.1KB; `circular_fraction_log` uncapped but tiny. No change needed.
  - [ ] Drift — found a real issue: `arrivals_log`/`strain_log`/`wellbeing_log`/`subscore_log` are unbounded (3000 rounds -> 383KB, linear ~128 bytes/round) unlike every sibling game's capped rolling-history fields. Didn't fix: `average_strain()` and the `crisis_averted` achievement's `_ever_reached_critical_strain()` both need the *full* history, not a window, so a safe fix needs decoupled running-sum/flag tracking first, not just a cap — genuine design/priority call, see `FOR-YOU.md` Q17.
  - [x] Trade Empire — found and fixed: `sale_log` grew unbounded (only `sale_log[-1]` is ever read) — ~100KB of a ~110KB payload at 5000 ticks (~83 simulated minutes, this game auto-ticks via `setInterval` regardless of player presence). Added `SALE_LOG_MAX_ENTRIES = 20` + truncation in `tick()`, matching this file's own `good_profit_recent`/`price_history` cap idiom. Re-measured: 11KB for the same session. 265/265 tests green, flake8 clean, build note in `games/trade-empire/CLAUDE.md`.
  - [ ] Continuum (read-only finding: `score_history` in `sim.py`/`save.py` is never capped, and every one of the 7 possible `era_snapshots` embeds a full copy of it at time-of-snapshot, so the save grows faster than linearly as more eras complete — measured 36KB for a 105-season 7-era playthrough vs. 103KB for a 420-season one via a driver script against Continuum's own test harness. Not yet a hard concern, but the growth pattern is exactly what `Chronicle`'s own `MAX_ENTRIES` cap in `log.py` already guards against elsewhere in this same game — Noyvj's own session can check this off after reading and deciding whether it's worth a cap.)
  - [x] Le Champ de Mots — simulated all 790 plots reviewed over 400 days: 165.8KB; already follows the documented "only touched plots are saved" pattern (Milestone 5), this is the genuine full-payload ceiling. No change needed.
- [ ] Z25b: Add an opt-in autosave checkbox (every ~5 minutes) — a deliberate, explicit reversal of the original "no auto-save timer" design decision (see `SAVE-BUTTON-INTEGRATION.md` §5). Must default OFF; the player turns it on, never the other way around.
  - [ ] Build the shared opt-in autosave mechanism once
  - [ ] Roll out to each game alongside its own save widget (same 12-game list as above)
- [ ] Z26: A consistent "info page" discoverability regression check — confirm "The Real Story" button wording/icon is identical via the shared `info_page.py`, across the 8 climate-quartet games only:
  - [ ] Canopy
  - [ ] Grid
  - [ ] Tide
  - [ ] Aftermath
  - [ ] Herd
  - [ ] Thaw
  - [ ] Loop
  - [ ] Drift
- [ ] Z27: A shared "difficulty-aware achievements" audit — check whether any achievement becomes impossible or trivially easy under a game's own hard-mode/difficulty toggle:
  - [ ] SOL
  - [ ] Canopy
  - [ ] Grid
  - [ ] Tide
  - [ ] Aftermath
  - [ ] Herd
  - [ ] Thaw
  - [ ] Loop
  - [ ] Drift
  - [ ] Trade Empire
  - [ ] Continuum
  - [ ] Le Champ de Mots
- [ ] Z27b: Add a "% of players who have earned this" stat per achievement *(needs Z1)* — per your own added note, "that's how I see how difficult it is on most sites."
- [x] Z28: A consistent loading-state check — confirm every game shows a visible "loading…" state during Pyodide boot rather than a blank screen. Audited, no change needed: every game's static HTML (rendered instantly, before Pyodide even starts fetching) already includes its `<h1>` title plus every interactive control in a `disabled` state showing the literal text "Loading..." (buttons) or a "Loading..." status paragraph — confirmed via `grep -rn "Loading\.\.\." games/*/index.html` across all 12. No game shows a blank screen at any point between initial paint and Pyodide finishing boot; the pattern is already consistent site-wide (a disabled-button/status-text convention, not a dedicated spinner component) rather than needing one to be built.
  - [x] SOL
  - [x] Canopy
  - [x] Grid
  - [x] Tide
  - [x] Aftermath
  - [x] Herd
  - [x] Thaw
  - [x] Loop
  - [x] Drift
  - [x] Trade Empire
  - [x] Continuum
  - [x] Le Champ de Mots
- [ ] Z29: A cross-game "credits/sources" aggregation page — gather each game's real-world sources, then build the page:
  - [ ] Canopy's Info Page sources
  - [ ] Grid's Info Page sources
  - [ ] Tide's Info Page sources
  - [ ] Aftermath's Info Page sources
  - [ ] Herd's Info Page sources
  - [ ] Thaw's Info Page sources
  - [ ] Loop's Info Page sources
  - [ ] Drift's Info Page sources
  - [ ] Continuum's era sources
  - [ ] Build the aggregation page from the gathered list
- [x] Z30: A quick pass confirming every game's favicon/tab title is set correctly and distinctly, matching the NoyvjGames branding. Tab `<title>` half needed no fix (already distinct per game). Favicon half was a real gap — all 12 games (and the hub itself) pointed at the exact same `icons/icon-192.png`, pixel-identical across tabs. Fixed: one new `icons/favicon-<slug>.svg` per game (rounded-square background in that game's own existing hub-thumbnail accent color, single bold letter/small glyph centered), one new `<link rel="icon">` line per game's `index.html`. `icons/icon-192.png`/`icon-512.png` (PWA manifest icons) untouched. Hub's own root `index.html` kept the original placeholder icon. Live-verified (200 + correct content-type + visually distinct at 16px) for SOL/Canopy/Continuum/Le Champ de Mots; all 12 diffed for the same one-line change.
  - [x] SOL
  - [x] Canopy
  - [x] Grid
  - [x] Tide
  - [x] Aftermath
  - [x] Herd
  - [x] Thaw
  - [x] Loop
  - [x] Drift
  - [x] Trade Empire
  - [x] Continuum
  - [x] Le Champ de Mots
- [ ] Z-extra (folded from C16's answer): audit one-time toast/banner callouts (first-X, milestone-crossed, etc.) and convert the ones that are really just "you did a thing once" into achievements instead of bespoke UI — "these should all be built into achievements and stop doing callouts since it will be announced through achievement gains" was Grid's own C16 answer; audit case by case, not a blanket removal:
  - [ ] SOL
  - [ ] Canopy
  - [ ] Grid (originating case — C16's "first battery built" callout)
  - [ ] Tide (D12, D17 callouts)
  - [ ] Aftermath (E17-era callouts)
  - [ ] Herd
  - [ ] Thaw
  - [ ] Loop
  - [ ] Drift (I10, I26 callouts)
  - [ ] Trade Empire (J28's callout, see per-game section)
  - [ ] Continuum
  - [ ] Le Champ de Mots
- [ ] Z-extra (folded from A26): a "reset settings to default" button inside every game's settings panel — SOL's A26 flagged this as a site-wide pattern, not SOL-only:
  - [ ] SOL
  - [ ] Canopy
  - [ ] Grid
  - [ ] Tide
  - [ ] Aftermath
  - [ ] Herd
  - [ ] Thaw
  - [ ] Loop
  - [ ] Drift
  - [ ] Trade Empire
  - [ ] Continuum
  - [ ] Le Champ de Mots
- [ ] Z-extra (folded from A10): an achievement-progress bar (X/N) visible in every game's toolbar itself, not only after opening the achievements panel — SOL's A10 flagged this as a site-wide pattern:
  - [ ] SOL
  - [ ] Canopy
  - [ ] Grid
  - [ ] Tide
  - [ ] Aftermath
  - [ ] Herd
  - [ ] Thaw
  - [ ] Loop
  - [ ] Drift
  - [ ] Trade Empire
  - [ ] Continuum
  - [ ] Le Champ de Mots
- [ ] Z-extra (folded from Z11, "let players pick to do a story mode in each game or turn off the story elements"): audit which games carry narrative/flavor-text framing and add an opt-out toggle where relevant:
  - [ ] SOL (flavor text/milestone framing)
  - [ ] Canopy
  - [ ] Grid
  - [ ] Tide
  - [ ] Aftermath (legacy system)
  - [ ] Herd
  - [ ] Thaw (region flavor lines)
  - [ ] Loop
  - [ ] Drift
  - [ ] Trade Empire
  - [ ] Continuum (story/era-transition beats)
  - [ ] Le Champ de Mots
- [ ] Z-extra (folded from Le Champ de Mots' L1/L10/L29 answers): a general design principle for any future minigame/practice feature anywhere on the site — every such action should visibly feed a measured top-level progress stat, so it always visibly "counts" toward something the player can see. (Forward-looking guidance, not a per-existing-game retrofit task.)
- [ ] Z-extra (folded from Le Champ de Mots' L30 answer): preserve a player's current visual/display-mode choice when navigating away to the hub and back, instead of resetting to default. Currently only concretely actionable for Le Champ de Mots (the only game with a visual-style switcher) — revisit the checklist here if another game adds a similar per-game display setting.

**Explicitly rejected this round (not carried anywhere, per your own answers):**
- Z3: a shared meta-progression module — build each game's own accepted meta-progression idea independently instead (see SOL, Canopy, Herd, Drift below).
- Z5: a shared challenge-mode/hard-mode naming convention — build each game's own accepted hard-mode idea independently instead (see Grid, Tide, Continuum below).

---

## Y. Home (the hub shell — index.html/script.js/style.css)

**Already done, not carried forward** (this ideas doc was drafted before these landed this session): Y1 (public roadmap page → `roadmap.html`, done), Y3 (admin aggregate stats page → `admin.html` + `GET /admin/stats`, done), Y5 ("claim your save" nudge, done), Y7 (PWA install banner, done). If you want any of these revisited/extended, that's new scope, not this list.

- [x] Y2: Let the hub's search/filter bar remember the last-used search term and tag filter across a reload, via `localStorage`.
- [x] Y4: A small live game-count readout ("12 games and counting") on the hub's header/tagline.
- [x] Y6: Let the review widget's star-rating show the current average as a filled/half-filled star visual, not just numeric text.
- [x] Y8: A small persistent "you're signed in" indicator visible even when scrolled past the account section.
- [x] Y9: A permanent service-worker cache-busting fix — a proper cache-version scheme for `sw.js` so it doesn't need the "reload twice" workaround this whole project has repeatedly had to use. *(Promoted out of `LATER.md`'s L16 — this round's "yes" resolves it; remove the old L16 entry there.)*
- [x] Y10: A small "new since your last visit" count badge on the What's New nav link itself.
- [ ] Y11 **(you answered "yes" in round 2, and approved it in round 1 as L5 — this had been dropped from this list by mistake)**: A genuine site-wide dark/light theme toggle. Needs the dedicated design pass first: a real second (light) colour scheme for the hub shell and every game's `style.css` (backgrounds, borders, meter fills, text contrast, per-game accent hues, Continuum's 3D scene sky/lighting), then a `data-theme` attribute + CSS custom-property swap, a toggle in each game's settings panel and on the hub, persisted per-device. Do it game by game after the current per-game feature passes land (they all edit `style.css`), and keep the colorblind-safety audit rules.
- [x] Y12: A small "member since" date on the hub's account section for signed-in users.
- [x] Y13: A light, skippable "site tour" onboarding flow for first-time hub visitors — **make it optional, same as the per-game tutorials.**
- [x] Y15: A "community highlights" section periodically featuring a real anonymized notable playthrough (needs Z1's aggregate backend).
- [x] Y16: A loading skeleton/placeholder for the title-card grid while the ratings widget's async fetch resolves.
- [x] Y17: A proper 404/error page for a broken game link, styled to match the hub.
- [x] Y18: A brief "Signed out" confirmation message on sign-out before the UI switches views.
- [x] Y19: A deeper site search that also searches inside game descriptions and changelog entries, not just the visible title-card text.
- [x] Y20: A "share this game" button per title card (copies a direct link), distinct from the review widget.
- [x] Y21: A "what's popular" sort option on the hub lobby — **build two separate sort modes**, sort-by-rating-average AND sort-by-save-count, per your own note that save count is probably the more honest popularity signal right now (reviews skew toward test/friend accounts).
- [x] Y22: A visual marker on title cards for games with an active difficulty/challenge variant (ties to Z10).
- [x] Y23: A short, honest terms-of-use/privacy page covering what's stored (accounts/saves/feedback) and why.
- [x] Y24: A "random game" button for an undecided visitor, weighted toward unplayed titles for a signed-in player.
- [x] Y25: A dismissible, `localStorage`-tracked site-wide announcement banner mechanism, distinct from the What's New page, for time-sensitive notices.
- [x] Y26: Let the achievements dashboard's overall progress bar show the exact fraction as a hover tooltip, not just the bar width.
- [x] Y27: A "recently added" hub-lobby section, separate from Continue Playing, surfacing the newest game(s).
- [x] Y28: A consistent focus-ring style audit across all hub-level interactive elements for keyboard-navigation clarity.
- [x] Y29: A privacy-respecting, self-hosted pageview-counter opt-in for real BCM206 visitor-count evidence (not a third-party tracker).
- [x] Y30: A "back to top" floating button on the hub lobby once scrolled past the fold.
- [ ] Y31 (new, 2026-09-21, from the Continuum K15 audit question): a real site-wide **account-synced settings** feature. Origin: K15 asked whether Continuum's text-scale/colorblind settings should survive save/load — they don't, by design, same as every game's own browser-local settings.js. User's actual answer went further: "this should be a user settings thing site-wide... I want players to be able to have their preferences saved throughout the site," with guests keeping the current per-device reset behavior. Scope: a signed-in player's site-wide prefs (at minimum text-scale + reduced-motion, the two every game's settings.js already exposes; extend to per-game accent/theme prefs once Y11's light/dark pass exists) sync via their account, the same way achievements/saves already do — a small new backend field on the account record (or reusing the existing save/account infra rather than a new table), a shared client-side helper each game's settings.js calls instead of reading `localStorage` directly, falling back to today's per-device `localStorage` behavior when signed out. A real cross-cutting build, not a one-game fix — needs its own design pass (backend shape, migration for the 12 games' existing settings.js files) before a full rollout; a good first slice is the backend field + the shared helper + one reference game integration (matching how SOL was the achievements reference integration), then roll out per-game after. — you confirmed the repo is already public, no action needed there, but asked for this as a safety check): a full scan of every tracked file **and commit history/messages** across the whole repo for anything personal that shouldn't be public — names, personal notes, stray credentials, anything written assuming a private audience. Worth doing sooner rather than gated behind everything else in this list, since the repo is public right now.

**Resolved, not carried forward:** Y14 — the repo is already public; no action needed.

---

## Per-game: SOL

- [x] A1: A second prestige tier beyond the existing flat yield bonus — a genuine skill-tree branch unlocked only after N prestiges.
- [x] A2: Show the current prestige level as a small badge next to the game's title, not just inside the win-banner toggle.
- [x] A3: A "New Game+" replay variant — **built as an unlock inside the existing prestige tree**, per your own note, rather than a separate standalone mode.
- [x] A4: A tooltip on the Prestige button stating exactly what resets and what doesn't, distinct from the "reset this world" option.
- [x] A5: A real "while you were away" delta report (resources gained, Governor decisions made) — reports on real elapsed time, doesn't gate progress on it, so it doesn't violate the no-idle-timer rule.
- [x] A6: Let the Stats & Share card's copy button flash "Copied!" like the shared save-widget's own copy button.
- [x] A7: A "Governor AI personality" choice per planet (aggressive/balanced/conservative presets) instead of one flat priority dial.
- [x] A8: Surface `governed_resource_generated`'s lifetime total on the main Stats screen too.
- [x] A9 **(prioritize — you called this "very important"):** A proper multi-planet overview dashboard — every unlocked planet's key stats at once, instead of navigating planet-by-planet.
- [ ] A10 → folded into Z (see "Games" section above): achievement-progress toolbar badge, site-wide.
- [x] A11: A "trade route automation" layer — once two planets have stable economies, set a standing trade rule instead of manually re-triggering.
- [x] A12: A subtle particle/spark animation on the resource icon when a manual click lands.
- [x] A13: A build-order planner/checklist players can manually tick through.
- [x] A14: Let the research-tree diagram collapse by tier.
- [x] A15: A "sandbox mode" toggle post-win-state — remove resource costs for free end-game experimentation.
- [x] A16: A small planet-count readout ("7/11 bodies visited") near the Travel button.
- [x] A17: An export/import progress code for lifetime stats, mirroring Aftermath's E12.
- [x] A18: `title` tooltips on each Governor priority button explaining exactly what the weighting does numerically.
- [x] A19: A "close call" achievement family — surviving a near-0%-ecology collapse and recovering.
- [x] A20: A small swatch legend for the terraform color-shift tiers.
- [x] A21: A "compare my run" feature against site aggregate stats *(needs Z1)*.
- [ ] A22 → folded into Z22 (see "Games" section above): confirm-before-full-save-wipe, as part of the site-wide `ConfirmDialog` wording audit.
- [x] A23: A "planet specialization" system — a fully-developed planet leans into one resource type for a production bonus.
- [x] A24: Surface the exact prestige-bonus percentage next to resource-gain numbers, not only in the Stats panel.
- [ ] A25: A "story mode" toggle surfacing existing flavor text more prominently as a light narrative thread.
- [ ] A26 → folded into Z (see "Games" section above): "reset settings to default" button, site-wide.
- [x] A27: A proper end-game "epilogue" screen once every planet is 100% terraformed, beyond the current banner.
- [x] A28: Let the Sky City info-toggle state the exact Mars-material cost ratio.
- [ ] A29: A community leaderboard for fastest full completion, opt-in *(needs Z1)*.
- [x] A30: A small animated icon transition when a building finishes constructing.

---

## Per-game: Canopy

- [ ] B1: A third biome beyond the main forest and Highland Grove — a wetland/coastal-forest region with its own tension (e.g. flood risk on preserved plots), unlocked at a higher threshold than Highland Grove.
- [x] B2: Let the coordinate-style plot labels also show up in the stakeholder-request panel.
- [x] B3: A "forest history" timeline view — a scrollable log of every clear/preserve/replant decision this session.
- [x] B4: A confetti/leaf-burst animation the first time a plot reaches "fully mature."
- [x] B6: Let the Highland Grove's unlock threshold show as a progress bar toward 2,000 standing value, not a silent unlock.
- [x] B7: A "forest ranger" harder-difficulty mode — steeper soil degradation from clearing.
- [x] B8: A tooltip on the stakeholder "incentive" request type clarifying it's a genuinely positive offer before opening it.
- [x] B9: A named-run "playstyle badge" (Preservationist/Balanced/Harvester) computed from the session's clear-vs-preserve ratio.
- [x] B10: Let biodiversity's numeric readout show its rate of change (+X/tick), not just the current total.
- [x] B11: A "reforestation partner" mechanic — a second party co-funds replanting a bare plot for a smaller cut of its future value.
- [x] B12: A small "?" tooltip on soil-quality percentages explaining what degradation costs in future yield.
- [x] B13: A proper end-of-session "forest report card" — biodiversity/standing-value/stakeholder-relations trends as three small graphs.
- [x] B14: A "Small (4×4)" grid preset alongside the existing Normal/Large options, for a faster session.
- [x] B15: A "legacy forest" feature — a fresh session starts with a small permanent bonus based on a previous session's final standing value (Aftermath-style meta-progression, opt-in, built independently per Z3's resolution).
- [x] B16: A keyboard shortcut for "select next stakeholder request."
- [x] B17: A visible seasonal cycle — plots grow slightly faster/slower by an in-game season indicator.
- [x] B18: A "copy my playstyle badge" button next to the existing shareable snippet.
- [x] B19: A "community forest" comparison page — see how other players' saved Run A/B snapshots compare in aggregate, anonymized *(needs Z1)*.
- [x] B20: Let the "+X value" floating animation vary its color slightly by magnitude (size/motion only, no new color-only meaning, consistent with the colorblind audit).
- [x] B21: A "specialist plot" upgrade — a long-preserved plot gets a one-time permanent specialization choice (biodiversity vs. economic value).
- [x] B22: A small "veteran plot" icon marker for plots that survived 3+ clear-requests without ever being cleared.
- [x] B23: A wildlife log — a running record of which species icons have appeared and when.
- [x] B24: Let the Reset Session confirmation show the current standing value being given up.
- [x] B25: A "community grant" event type — a stakeholder occasionally offers funding specifically for replanting.
- [x] B26: A subtle highlight/glow on whichever plot the mouse last hovered, for easier tracking on the larger grid.
- [x] B27: An "adopt a plot" personal-goal feature — mark one plot as a long-term project with its own mini-history.
- [x] B28: Let the Session Summary's counterfactual line also state the percentage difference, not just the absolute value.
- [ ] B29: A guided "best strategy" AI-narrated example playthrough demonstrating a strong preserve/clear balance.
- [x] B30: A small monthly/seasonal color-palette shift on the forest background art, purely decorative.

**Deferred to `LATER.md`** (your answer): B5 — comparing your forest's standing value against the site aggregate average — parked pending "a full multiplayer pass soon," distinct from B19 above (which only needs Z1, not multiplayer, and is accepted).

---

## Per-game: Grid

- [x] C1: A genuine "grid operator career" meta-progression — persistent stats/unlocks across multiple runs (Aftermath-style skill tree), since Grid currently resets fully each session (built independently per Z3's resolution).
- [x] C2: Let the breakdown-risk badge show the exact percentage chance, not just a badge.
- [ ] C3: A regional/multi-grid mode — manage two interconnected grids, sharing surplus capacity between them.
- [x] C4: A tooltip explaining exactly what "aging" does numerically on hover over any plant's wear percentage.
- [x] C5: A "grid operator report" — extend the existing Run Summary with a letter-grade/tier ranking against the real-world benchmark line.
- [x] C6: Let the plant-mix bar chart animate bars growing/shrinking on change, rather than snapping instantly.
- [x] C7: A "demand response" mechanic — invest in reducing peak demand itself, a fourth lever alongside build/retire/maintain.
- [x] C8: A small icon distinguishing renewable vs. fossil plant rows in the plant-mix chart legend, beyond color.
- [x] C9: A storage-arbitrage mini-game layer — once the battery tier is built, manually choose when to charge/discharge for a small bonus.
- [x] C10: Let the disruption-event toast include a "why this happened" reason tied to the specific plant that failed.
- [x] C11: A "grid resilience score" separate from clean-share — rewarding diversification (not all-renewable, not all-fossil) as its own axis.
- [x] C12: A small historical "best round" marker on the trend graph.
- [x] C13: A scenario-select mode at game start ("coal-heavy legacy grid," "greenfield renewable-first," etc.) with different starting plant mixes.
- [x] C14: Let the funds-breakdown panel show a small pie/bar visual, not just numbers.
- [x] C15: A cross-player aggregate comparison *(needs Z1 — the same shared endpoint C15 was already waiting on in `LATER.md`; resolve this one via Z1 rather than the separate multiplayer pass B5/others are waiting on)*.
- [x] C17: A weather-event log (separate from the disruption log) narrating exactly how Weather Variability affected a specific round's renewable output.
- [x] C18: Let Retire's confirmation dialog show the plant's current age/wear alongside the "last unit" warning.
- [x] C19: A "policy lever" mechanic — an occasional opt-in choice (carbon pricing, subsidy) that shifts the cost curve temporarily.
- [x] C20: A small up/down arrow next to the demand number each round, showing faster/slower growth than average.
- [x] C22: Let the steeper-demand-growth toggle show its exact multiplier in its own label.
- [x] C23: A maintenance-scheduling feature — pre-commit to a maintenance cadence per plant type instead of manually clicking Maintain.
- [x] C24: A subtle pulse on the emissions meter the instant it crosses the 50% renewable-capacity tipping point.
- [x] C25: A "grid of the future" endgame projection — extrapolate the current trajectory 20 more rounds, like Thaw's counterfactual.
- [x] C26: Give the plant-age wear icon three distinct visual tiers, not just a percentage number.
- [x] C27: An "emergency response" mode — a rare opt-in scenario where a major disruption hits and the player must stabilize the grid within a few rounds (built independently per Z5's resolution).
- [x] C28: A small "clean streak" counter visible at all times, not just inside the achievements panel.
- [ ] C29: A community-sourced "real utility" comparison mode against a specific real region's actual generation mix (stretch — needs real per-region data sourcing).
- [x] C30: A one-time tooltip explaining why renewable costs decrease with cumulative investment, the first time a renewable is built.

**Folded into Z (see "Games" section above):** C16's original "first battery built" callout — reshape into an achievement instead of a bespoke toast, per your own "these should all be built into achievements" answer; this is the specific case that seeded the broader Z-extra callout-to-achievement audit.

**Deferred to `LATER.md`** (your answer): C21 — the "grid twin" split-view comparison mode — you left this as a judgment call on whether it's too much for a player; parking it for a real scoping conversation rather than deciding unilaterally.

---

## Per-game: Tide

- [x] D1: A fifth adaptation tier beyond Storm-surge barriers — a "managed retreat" option trading some coastline for guaranteed long-term stability, a genuinely different strategy branch.
- [x] D2: Let the worst-season callout also show which specific investment (or lack of one) contributed most to that season's damage.
- [x] D4: A small wave/tide animation cue tied to the sea-level meter's current percentage, purely decorative.
- [x] D5: A "climate refugee" mechanic — once a coastline is sufficiently flooded, population must relocate to remaining land (a light connection to Drift's displacement theme, not a duplicate of its mechanics).
- [x] D6: Let the fish-yield crash warning banner include a suggested action (invest in acidity reduction), not just the warning.
- [x] D7: A "delayed consequence" visualization — a timeline graph showing today's acidity choices against the eventual fish-yield impact several seasons later.
- [x] D8: A small tide-level indicator showing the current season's high/low tide relative to the coastline tiles.
- [ ] D9: A community seawall-design comparison — aggregate stats on which adaptation-tier combination other players reach fastest *(needs Z1)*.
- [x] D10: Let the acidity/fish-yield mini-graph show a dashed reference line at the historical average, like Thaw's melt-threshold gridline.
- [x] D11: A "coastal economy diversification" mechanic — a third income source (tourism, aquaculture) as a hedge against acidity-driven fish crashes.
- [x] D13: A "storm season" event layer — periodic acute weather events (distinct from the slow background sea-level rise) testing whether adaptation infrastructure holds under immediate shock.
- [x] D14: Let the then-vs-now stat block include a small sparkline, not just numbers.
- [x] D15: A proper settlement-growth mechanic — population/economy grow over a successful session, giving "success" a visibly growing settlement, not just a stable one.
- [x] D16: A tooltip on the hard-lag difficulty toggle explaining exactly what the extended lag means in seasons.
- [x] D17: A "coastal heritage" mechanic — certain coastline tiles carry extra value (a historic site, a reef) worth protecting even at higher cost.
- [x] D18: Let the comparison-baseline checkpoint show a small marker on the trend graphs at the exact season it was set.
- [x] D19: A "sea-level rise scenario" select at game start — conservative/moderate/severe real-world-grounded trajectories.
- [x] D20: A small icon-badge extension of the seawall visual's per-tier signature into the investments panel too.
- [x] D21: A "citizen science" side-mechanic — monitoring investment periodically reveals a piece of real-world acidification data as a reward.
- [x] D22: Let the output-mix sub-choice show a live preview of the income/fish-yield tradeoff before committing.
- [x] D23: A proper "recovery" narrative — a distinct celebratory callout once a crashed fish stock rebuilds, mirroring the existing decline narration with equal weight.
- [x] D24: A small "seasons survived" counter always visible, not just inside the session summary.
- [x] D26: Let the per-tile flood-threshold tooltip also state how many seasons remain at current pace.
- [x] D27: A "before it's too late" replay mode — replay from a mid-session checkpoint with knowledge of what's coming, distinct from the existing counterfactual.
- [x] D28: A subtle color-independent pattern on the seawall visual tiers, extending the existing colorblind-audit redundancy to the new infrastructure art.
- [x] D29: A "settlement name and history" light narrative layer, scaled-down diegetic flavor in Continuum's spirit.
- [x] D30: A one-time tooltip the first time hard-lag mode is toggled, confirming the change takes effect next season.

**Folded into Z (see "Games" section above):** D12's original "first adaptation tier unlocked" celebratory callout — tie into an achievement pop-up instead, per your answer.

**Deferred to `LATER.md`** (your answers): D3 — a multi-settlement mode — left as a judgment call on player-facing complexity, parked for a scoping conversation. D25 — the "shared coastline" cooperative-framing stat — explicitly saved for the multiplayer update.

---

## Per-game: Aftermath

- [x] E1: A sixth and seventh skill node, extending the existing prerequisite-tree pattern into a genuine multi-branch tree — **"will add a bunch of new nodes with important decisions,"** per your note, so treat this as a real tree expansion, not just two extra leaves.
- [x] E2: Let the skill-unlock toast persist slightly longer for skills with more real-world grounding text to read.
- [x] E3: A "disaster type specialization" — the skill tree branches into weather-focused vs. social-shock-focused resilience paths, giving Civil Unrest its own upgrade path.
- [x] E4: A small "runs completed" counter always visible, not just inside the Review Past Runs panel.
- [x] E5: A "generational memory" mechanic — a run occasionally references a specific past run's outcome in its event flavor text, deepening the legacy system.
- [x] E6: Let the extended-run mode show its exact new event count in the toggle's own label.
- [x] E7: A proper difficulty-scaling curve across many runs — event severity variation could also scale with total lifetime runs played.
- [x] E8: A one-time tooltip the first time a run scores negative, reassuring the player the skill tree persists regardless.
- [ ] E9: A "community resilience index" — an aggregate stat showing average skill-tree strength across all players *(needs Z1)* — **you flagged this for a fuller build-out once the multiplayer update and "holiday events" (see Z23) land**, so treat the Z1-dependent version here as a first pass, not the final shape.
- [x] E10: Let the toughest-run-yet comparison show the specific event sequence that made it toughest, not just the score.
- [x] E12: A small badge on the settlement art for reaching a "toughest run" personal best, not just per-skill badges.
- [x] E13: A proper narrative epilogue at the end of an extended run, in Continuum's era-transition-beat spirit, scaled to Aftermath's shorter format.
- [x] E14: Let the expected-damage preview show a confidence range, not just a single number.
- [x] E15: A "specialize or generalize" build-diversity achievement family, rewarding both a narrow deep-investment strategy and a broad balanced one.
- [x] E16: A small animated flourish on the Review Past Runs panel when a run's score beats the previous best.
- [ ] E17a: A "climate scenario pack" — choose among a few real-world-grounded event-schedule variants (coastal/inland/urban) at run start.
- [ ] E17b: Extend E17a to real named locations (per your example: San Francisco skews earthquake/fire risk with near-zero snow/hurricane risk), not just generic region types.
- [x] E18: Let the knowledge-points-live-preview show a small "+" animation when it increases.
- [ ] E19: A proper "resilience curriculum" mode — a guided sequence of runs with specific goals each time.
- [x] E20: A tooltip explaining exactly how skill-tree strength affects severity variation.
- [x] E22: Let the reset-skill-tree two-click confirm show exactly how many knowledge points will be refunded before the second click.
- [ ] E23: A community "hardest schedule survived" leaderboard, since severity variation means no two hard runs are identical *(needs Z1)*.
- [x] E24: A small icon per event category (weather/non-weather/social) in the Review Past Runs list itself, not just the live event display.
- [x] E25: A proper "settlement identity" customization — name the settlement once, carried across all runs.
- [x] E26: Let the export/import progress code show a short human-readable summary of its contents before copying.
- [ ] E27: A "resilience mentor" onboarding mode — an optional guided first run with inline suggestions, distinct from the standard tutorial.
- [x] E28: A one-time callout the first time severity variation swings notably harsher due to skill-tree strength, explaining why.
- [ ] E29: A "societal memory" system — a very bad past-run outcome permanently unlocks a unique defensive skill not otherwise available.
- [x] E30a: A small "X runs until next skill affordable" estimate next to a locked skill's cost, based on average knowledge-point earn rate.
- [x] E30b: A "pin" feature so the player can mark specific skills they're saving toward and have E30a's estimate tracked for exactly those, per your addition.

**Explicitly rejected this round:** E21 — the "what would have happened" hypothetical-skill-tree replay — dropped, not carried anywhere.

**Deferred to `LATER.md`** (your answer): E11 — the "mutual aid network" positive event — explicitly waiting for the multiplayer update.

---

## Per-game: Herd

- [ ] F1: A "regional herd network" — manage a second, smaller satellite farm with its own coupling ratio; surplus decoupling investment from the main farm partially offsets the satellite's emissions.
- [x] F2: Let the pasture visual's cow-count thresholds include a small herd-size number overlay, not just the visual count.
- [x] F3: A "consumer demand shift" mechanic — market preference occasionally shifts toward plant-based output, temporarily making the pivot more profitable.
- [x] F4: A one-time tooltip the first time coupling ratio crosses below 0.5, explaining "decoupled" in plain terms.
- [x] F5: A "generational herd genetics" system — invest in breeding for naturally lower methane intensity per animal, a slow-burn fourth decoupling lever.
- [x] F6: Let the report card show the exact percentage the player's score beat the pure-growth baseline by.
- [x] F7: A "farm cooperative" comparison — aggregate stats on community-wide methane-per-unit avoided *(needs Z1 for a first pass — you flagged this as feeling especially important but possibly better suited to a fuller build once the multiplayer update lands; ship the Z1-backed version now, expand later)*.
- [x] F8: A small "record decoupling ratio" marker on the coupling gauge, like Grid's best-round marker.
- [x] F9: A proper multi-season weather/feed-cost variation layer, adding light unpredictability to the investment-return math.
- [ ] F10: Let the community stat show a small trend arrow if the backend can support it cheaply *(same F7/Z1 caveat above)*.
- [x] F11: A "sustainable certification" milestone — a sustained low coupling ratio for N rounds unlocks a permanent price premium.
- [x] F12: A tooltip on the Plant-Based Pivot's confirm dialog stating the exact income tradeoff percentage.
- [x] F13: A "supply chain" expansion — invest downstream (processing, distribution efficiency) as a new income lever distinct from herd growth.
- [x] F14: Let the real-world comparison message update its framing once the player's own reduction exceeds the cited 42% figure, congratulating them for beating the real benchmark.
- [x] F15: A "herd health" sub-system — animal welfare as a light second axis, where certain decoupling measures (better feed) also improve welfare.
- [x] F16: A small pulse on the methane trend graph the moment the curve visibly flattens.
- [x] F17: A "farm tour" narrative mode — periodic short flavor vignettes reacting to the farm's current coupling ratio.
- [x] F18: Let the investment consequence preview show numbers with a small before/after arrow.
- [x] F19: A "regional methane cap" scenario mode — an opt-in harder variant with a hard regulatory cap forcing decoupling.
- [ ] F21: A community "decoupling leaderboard" by best score-vs-baseline gap *(same F7/Z1 caveat above)*.
- [x] F22: Let the min/max range labels behind the coupling gauge flash when a new session-best is set.
- [x] F23 **(you called this "the next big thing this game needs"):** A "second herd type" — a genuinely different animal (poultry, aquaculture) with its own coupling curve, **unlocked via prestige**, each type with its own needs and decoupling levers, per your framing.
- [x] F24: A tooltip explaining exactly what the ambient haze overlay's intensity represents.
- [ ] F25: A "farm succession" meta-progression, Aftermath-style (built independently per Z3's resolution) — **explicitly tie this to F23**, per your note that they work well together (e.g. succession unlocking or feeding into new animal types).
- [x] F26: A small icon distinguishing the three original decoupling measures (feed/caps/capture) from the plant-based pivot in any summary list.
- [x] F27: A "policy advisor" event — periodically offers a choice between a subsidy for decoupling investment or a flat cash bonus.
- [x] F28: Let the worked numeric example in the tutorial be revisitable from the How to Play panel directly.
- [x] F30: A small animated methane-wisp effect that visibly thins as coupling ratio improves, reinforcing the haze overlay's intensity cue with motion.

**Folded into Z (see "Games" section above):** F20's "maximum feasible decoupling ratio" badge — build as an achievement pop-up instead of a bespoke badge, per your answer.

**Needs a feasibility check before deciding:** F29 — a "methane capture marketplace" where excess capture capacity is "sold" for a small return. You asked: is there a real-world example of this? If yes, build it; if it's not grounded in anything real, drop it. Research this before adding it to the working list.

---

## Per-game: Thaw

- [x] G2: Let the region flavor lines be visible as a permanent subtitle under each region's name, not just discoverable once.
- [ ] G3: A "permafrost carbon bank" mechanic — sustained low-acceleration play in a region banks a resource usable for a one-time bonus elsewhere.
- [x] G4: A tooltip on the Region D reveal toggle explaining what "worst case" means before the player reveals it.
- [ ] G5: A "tipping cascade" mechanic — once one region tips into the feedback loop, a small chance it accelerates a neighboring region too.
- [x] G6: Label the melt-threshold gridline with its exact temperature value, not just a dashed line.
- [ ] G7: A "climate scientist" info-mode — an optional deeper data view showing real-world methane-release curves alongside the in-game graph.
- [x] G8: A small distinct color-independent icon on the critical melt-status tier, reinforcing its text label with a shape cue.
- [ ] G9: A "long game" mode — significantly extend session length for players who want the full long-run trajectory.
- [x] G10: Let the next-round preview tooltip show all three regions' previews simultaneously in one combined tooltip.
- [x] G11: A community "average acceleration factor" comparison, reinforcing the hope-angle message that intervention is common and effective *(needs Z1)*.
- [x] G12: A one-time callout the very first time `dampening_at_melt_start` is nonzero, praising the pre-emptive investment.
- [ ] G13: A "policy simulation" branch — choose a real-world-inspired regional policy stance at game start, subtly weighting starting dampening.
- [x] G14: Let the preset strategies show a small preview of the resulting investment split before committing.
- [ ] G15: A "permafrost restoration" late-game mechanic — once a region stabilizes, sustained investment slowly reverses some melt.
- [x] G16: A small trend arrow next to each region's temperature readout, showing faster/slower rise than last round.
- [ ] G17: A "four regions, one story" narrative thread connecting A/B/C/D lightly (a shared research effort or funding pool) without merging their independent mechanics.
- [x] G18: Let the intervention feedback message's tiered phrasing include a small icon per tier, not text alone.
- [x] G19: A "scientist's log" — a running, dated record of key moments per region, a lightweight version of Continuum's ongoing-log system.
- [x] G20: A tooltip explaining exactly what `SECOND_WARMING_MILESTONE` represents in real terms before it's ever crossed.
- [ ] G21: A "region rescue" mechanic — a costly one-time emergency intervention if a region tips into critical, a last-resort lever.
- [x] G22: Let the best-run personal record show which region achieved it, not just the raw `temperature_saved` number.
- [ ] G23: A proper multi-session "climate archive" — a persistent record across many sessions of every region's best-ever performance.
- [x] G24: A small pulse on the acceleration-factor readout the instant a region crosses into the critical tier.
- [x] G26: Let the intervention free-text field show a short prompt/example answer as placeholder text.
- [ ] G27: A "thaw forecast" mini-game — periodically predict next-round temperature before advancing, rewarded cosmetically for accuracy.
- [x] G28: A small "rounds since last tipping event" counter, giving stability its own visible streak like Grid's clean streaks.
- [ ] G29: A "global vs. regional" framing toggle — the same mechanic reframed as either "my region's choices" or "the global aggregate."
- [x] G30: A one-time tooltip the first time Region D is revealed, clarifying it's fully automated and never needs player input.

**Explicitly rejected this round:** G1 — a fifth "wildcard" region — dropped; you don't think the game needs that many regions running.

**Deferred to `LATER.md`** (your answer): G25 — the "counterfactual world tour" applying Region D's trajectory to Region A/B/C's starting conditions — parked as "maybe later," not rejected outright.

---

## Per-game: Loop

Every idea in this section was accepted. **You also flagged a real cross-cutting design direction here:** on H25/H29 (see below), you said visual design could be a big thing for this game, even if some visual options only work on desktop — build a simple/text version that works everywhere, alongside a richer visual version that's a notably better experience on desktop specifically, rather than one-size-fits-all. Keep that framing in mind for both items.

- [x] H1: A third trading partner beyond Trade Link and Regional Partner, with its own distinct cost/supply ratio.
- [x] H2: Let the closed-loop streak tracker show its current streak with a small progress indicator (no guilt-driven "flame" framing, per this game's own design spirit).
- [ ] H3: A "supply chain redesign" late-game layer — once fully circular, over-invest in a specific measure (repair/reuse/recycle) for a small efficiency bonus.
- [x] H4: Let the alternate goods-flavor sets be switchable mid-session as a cosmetic-only relabeling, not just at game start.
- [x] H5: A "circular economy index" community comparison — aggregate stats on average circular-fraction reached across all players *(needs Z1)*.
- [x] H6: A small animated particle burst specifically on the moment circular fraction crosses each 25% milestone.
- [ ] H7: A "product lifecycle" vignette expansion — follow a specific named product across multiple cycles, a small ongoing narrative thread.
- [x] H8: Let the cost-per-unit-of-supply readout show a small trend indicator (getting cheaper/pricier).
- [ ] H9: A "waste stream diversification" mechanic — specialize in recovering a specific material type for a bonus.
- [x] H10: A tooltip on the "time to close the loop" projection clarifying it's an estimate, not a guarantee.
- [ ] H11: A "regional recycling network" — a shared community pool where excess recovered material could represent value for others (stretch — needs real backend support).
- [x] H12: Let the score breakdown show a small pie chart of score sources.
- [ ] H13: A "circular design challenge" scenario mode — start with a deliberately hard-to-close chain as an opt-in harder variant.
- [x] H14: A small badge for trying all available goods-flavor sets across different sessions.
- [x] H15: A "loop efficiency audit" panel — a periodic optional deep-dive showing exactly where supply is wasted, with actionable suggestions.
- [x] H16: Let the first-time-closed-loop banner include the exact cycle number it happened on.
- [ ] H17: A "consumer behavior" mechanic — invest in demand-side changes (encouraging reuse/repair culture) distinct from supply-side investment.
- [x] H18: A small glow on the loop-ring visualization's node currently receiving the most investment.
- [ ] H19: A "circular economy scorecard" comparing the player's achieved circularity against several real-world sector benchmarks simultaneously (extends the existing single comparison).
- [x] H20: Let the alternate vignette phrasings rotate randomly among a fraction-bucket's options, for variety on repeat sessions.
- [ ] H21: A "material passport" mechanic — track a piece of material's full journey as a literal traceable object.
- [x] H22: A tooltip explaining the hard-ceiling note with its exact multiplier value inline.
- [ ] H23: A "zero-waste challenge" mode — a stricter variant where the extraction meter must stay below a hard cap.
- [x] H24: A small running count of "cycles since last new extraction," visible once circularity is high.
- [x] H25a: A "trade network visualization" upgrade — a small diagram showing both trade partners and the internal loop simultaneously, in a simple/text version that works everywhere.
- [ ] H25b: A richer visual version of H25a, notably better on desktop specifically, per your note above.
- [x] H26: Let the reactive pulse on the trade-network display vary in intensity based on the size of the change.
- [x] H27: A "community goods category" vote/rotation — periodically feature a specific goods category as the "challenge of the week."
- [x] H28: A one-time tooltip the first time Regional Partner becomes available, distinguishing it from Trade Link.
- [x] H29a: A "circular supply chain map" — a visual network diagram (nodes for extraction/manufacturing/use/disposal/trade partners), replacing or supplementing the current linear-flow visualization, in a simple/text version that works everywhere.
- [ ] H29b: A richer visual version of H29a, notably better on desktop specifically — same simple/visual split as H25.
- [x] H30: Let the "Start New Chain" reset show the two lifetime counters that survive (chains completed, categories tried) in the confirmation message.

---

## Per-game: Drift

Every idea in this section was accepted, no exceptions.

- [ ] I1: A second receiving region — manage two regions with different starting capacity/pressure profiles simultaneously.
- [x] I2: Let the passive unmanaged control region show its wellbeing trend on the same trend graph as the player's own region.
- [ ] I3: A "policy toolkit" mechanic — choose among a few real-world-grounded institutional policy levers (streamlined credentialing, language-access funding) as named investment options, rather than the current abstract housing/services/infrastructure split.
- [x] I4: A visible (not just hover) statement of the accelerated-severity toggle's exact multiplier.
- [x] I5: A "generations forward" interactive coda — one or two final symbolic choices that flavor (not mechanically alter) the epilogue text.
- [x] I6: Let the session-milestone summary include a small trend indicator (improving/plateauing/declining) alongside the snapshot numbers.
- [ ] I7: A "regional network" mechanic — a well-prepared region optionally supports a struggling neighboring region (light connection to I1).
- [x] I8: A small icon distinguishing the three composite wellbeing sub-scores (services/economy/cohesion) everywhere they're shown.
- [x] I9: A "capacity planning" forecast tool — a projected arrivals curve for the next N rounds based on current background severity.
- [x] I10: Let the net-positive turning-point badge show the exact round it was reached.
- [x] I11: A "thriving region" showcase mode — reaching the Thriving band unlocks a short optional descriptive vignette, institutional framing.
- [x] I12: A tooltip explaining what "unmanaged control region" represents and why it's shown.
- [x] I13: A "resettlement outcome" real-data comparison — the region's integration rate compared directly against the real 89% benchmark as a live in-session stat.
- [x] I14: Label the target marker on wellbeing gauges with the exact threshold number.
- [x] I15: A "crisis-to-recovery" narrative mode — an opt-in harder start (already-strained region) demonstrating the "not too late" message from a bad starting position.
- [x] I16: A small badge for reaching Model Region tier via a from-behind recovery, distinct from steady management.
- [ ] I17: A "community capacity index" — aggregate stat showing average regional wellbeing across all players *(needs Z1)*.
- [x] I18: Let the free-text tone/framing feedback field show a short explanatory placeholder.
- [x] I19: A "resource reallocation" mid-run mechanic — shift already-committed capacity between housing/services/infrastructure at a small cost.
- [ ] I20: A one-time callout the first time the arrival-dot stream's density visibly changes due to a difficulty toggle.
- [x] I21: A "long-horizon divergence" comparison — the coda's generations-later outcome shown side by side for both the player's region and the passive control region.
- [x] I22: Show the funds-to-economic-health scale reference as a small always-visible conversion note.
- [x] I23: A "regional identity" light customization — name the region once, carried through the whole session and into the coda.
- [x] I24: A small trend arrow next to each of the three composite sub-scores.
- [ ] I25: A "second wave" mechanic — after initial arrivals integrate, a second, larger wave tests whether improved capacity holds up.
- [x] I26: Let the comfortably-ahead dimension callout name the specific sub-score that's ahead.
- [x] I27: A "capacity investment ROI" dashboard — exactly how much each dollar invested has returned in integration contribution.
- [x] I28: A tooltip explaining exactly what triggers the strain-level consequence descriptions.
- [ ] I29: A "cross-region learning" mechanic — reaching Thriving once unlocks a small permanent efficiency bonus for any future region managed (built independently per Z3's resolution).
- [x] I30: A small "rounds until next capacity milestone" estimate, based on current investment pace.

---

## Per-game: Trade Empire

- [ ] J1: A fourth self-contained expansion cluster beyond the home system and Kepler Cluster, requiring deeper research investment.
- [x] J2: Let the per-route profitability readout show a small trend arrow (improving/declining) based on recent trips.
- [ ] J3: A "trade guild" mechanic — an NPC faction offering occasional bulk contracts (deliver X units of Y to Z by a deadline) for bonus rewards.
- [x] J4: Let the historical price sparkline show the exact current price as a labeled point, not just the trend line.
- [ ] J5: A "fleet composition" upgrade — choose among distinct ship archetypes (cargo-heavy/fast/balanced) at purchase time.
- [x] J6: A tooltip explaining exactly what Fleet Priority's target-ring visualization is pointing at.
- [ ] J7: A "colony investment" mechanic — directly fund a colony's development to accelerate its growth/specialization.
- [x] J8: Let the idle-manual-ship warning badge show exactly how many ticks it's been idle.
- [ ] J9: A "market speculation" layer — stockpile a good during a price crash, sell during a later recovery.
- [ ] J10: A small animated docking/undocking visual on the map when a ship arrives/departs.
- [ ] J11: A "trade route insurance" mechanic — a small recurring cost protecting against a rare route-disruption event.
- [x] J12: Let the ship-rename feature support a quick "reset to default name" option.
- [x] J13: A "galactic economy overview" dashboard — a single screen summarizing every colony's need/supply state at once.
- [x] J14: A small badge for a ship completing N round trips on the same route — a "veteran hauler" marker.
- [ ] J15 **("I do love extensive research trees," per your note):** A "research specialization" branch — choose between an automation-focused or market-focused research path once the tree grows large enough.
- [ ] J16: Let the endgame galaxy-dot canvas respond to mouse hover with a small info tooltip per dot.
- [ ] J17: A "player-run trade post" mechanic — once automation is maxed, establish a passive trade post generating income without an assigned ship.
- [x] J18: A tooltip on the automate button reminding the player automation is a one-time, non-reversible choice per ship.
- [ ] J19: A "colony rebellion/loyalty" mechanic — chronically under-served colonies occasionally demand a one-time concession.
- [x] J20: Let the market-crashed styling include a small recovery-ETA estimate in its tooltip.
- [ ] J21: A "trade empire legacy" meta-progression — a fresh game starts with a small permanent bonus once the endgame state is reached (built independently per Z3's resolution).
- [x] J22: A small particle/spark effect on a successful high-value sale.
- [ ] J23: A "diplomatic relations" layer between the home system and Kepler Cluster — sustained trade volume unlocks a small permanent efficiency bonus.
- [x] J24: Let the colony detail sparkline show a small "needs met %" summary number alongside the graph.
- [x] J25: A "fleet-wide efficiency report" — a periodic optional panel showing which ships/routes are underperforming.
- [x] J26: A tooltip on the research panel's locked nodes explaining exactly what's still needed to unlock them.
- [ ] J27: A "trade empire almanac" — an in-game reference documenting each good's typical price range and which colonies produce/need it.
- [ ] J29: A "seasonal demand" mechanic — periodic, predictable shifts in which goods are in higher demand.
- [x] J30: A small map legend explaining the automated-vs-manual diamond/circle ship-dot distinction for a first-time viewer.

**Folded into Z (see "Games" section above):** J28's original "first automated ship" congratulatory animation — build it as an achievement pop-up instead of a bespoke callout, per your answer.

---

## Per-game: Continuum

*(This section is Noyvj Claude's to execute, not Noy2 Claude's — Continuum is being actively worked on in a separate concurrent session. Written here so the full ideas doc lands in one place; see `planning/AI-COORDINATION.md` before starting any of it.)* This section was written with real audience research behind it (40-year-old tech-industry men, your dad's friends) — see the ideas doc's own K-section preamble for the research summary (SimCity/Civilization-era nostalgia, deep optimization systems, competitive benchmarking).

- [x] K1: A "city planner's dashboard" — an optional dense, data-forward overlay (numeric readouts for every stat at once) as an alternate view mode alongside the 3D scene.
- [x] K2: A small "founded [year]" plaque-style readout on the main screen.
- [x] K3: A "benchmark your city" comparison mode against the aggregate of all other players' cities at the same era *(needs Z1)*.
- [x] K4: A subtle SimCity-era-style isometric camera preset alongside the existing Overview/Close-up/Aerial presets.
- [ ] K5: A "policy log" — a running, dated ledger of every major research/infrastructure decision, styled like city council meeting minutes.
- [x] K6: Let the research tree's search/filter support filtering by branch (provision/community/craft) as quick-toggle chips.
- [x] K7 *(this is `TODO.md`'s still-open K5, now with a concrete direction)*: The "civilization summary" end-of-playthrough report — frame it like an annual shareholder/stakeholder report, complete with a scored "sustainability rating," in-character.
- [x] K8: A small efficiency-per-capita readout always visible in the HUD.
- [x] K9 *(this is `TODO.md`'s still-open K12, marked "maybe" this round)*: A scenario/difficulty select at new-game start, including a "hard mode: resource-scarce start."
- [x] K10: A small "years since last unrest event" streak counter, mirroring Grid's clean-streak idea.
- [x] K11 **(prioritize — you called this out explicitly):** A "civic engineering challenge" mode — periodic optional constraints (e.g. build the next tier using 20% less resource extraction) as opt-in mini-challenges within an ongoing playthrough.
- [x] K12: A tooltip on each research node showing its exact numeric effect directly in the tree view.
- [x] K13: A "my city vs. history" comparison — the player's city trajectory plotted against a real historical reference curve for the same era.
- [x] K14 *(this is `TODO.md`'s still-open K17, now with a concrete direction)*: A day/night cycle toggle that can be paused on a specific time-of-day for screenshot purposes.
- [x] K15: A "founder's log" — the player writes (or selects templated) short personal annotations at each era transition.
- [x] K16 *(this is `TODO.md`'s still-open K18, now with a concrete direction)*: An optional stricter "hard mode" sustainability variant with meaningfully tighter livability thresholds, framed as a mastery challenge.
- [x] K17: A small "efficiency rank" badge (Bronze/Silver/Gold city) computed from the final sustainability score.
- [x] K18: A "settlement archive" — a gallery of every past completed playthrough's final city (stats + screenshot).
- [x] K19 **(you flagged this as important for BCM114):** A small real-world GDP-per-capita-style reference line on the resource-balance graph, grounding the abstract number in a familiar economic framing.
- [x] K20 *(this is `TODO.md`'s still-open K13, now with a concrete direction)*: A "shareable settlement snapshot" rendered as a clean, professional-looking infographic card (stats + a 3D-scene screenshot).
- [x] K21a: A small "tech tree completion %" readout.
- [x] K21b: Expand the research tree further, per your added note — a real tree-growth task, not just K21a's UI readout.
- [x] K22: A "consulting mode" — an optional harder scenario taking over a pre-built, already-struggling city that must be turned around.
- [x] K23: A small "next tier unlocks in ~N research points" estimate on locked research nodes.
- [x] K24: A "civic infrastructure map" overlay — a simplified 2D top-down schematic view of building placement/density.
- [x] K25: A small "livability vs. growth" scatter-plot mini-graph tracked across the whole playthrough.
- [ ] K26a **(direction changed from the original pitch, per your answer):** Do NOT build the originally-pitched "Space Age expansion" epilogue that closes out the seven-era arc — "rather than closing it, lets keep making more eras," per your answer.
- [ ] K26b: Scope what an eighth (and future) era beyond Space Age would look like, continuing the arc rather than ending it.
- [x] K27: A small keyboard-shortcut cheat-sheet overlay (accessible via a "?" key).
- [x] K28: A "resource flow diagram" — an optional Sankey-style visualization of how resources move through the current era's production chain.
- [x] K29: A small "time played this city" readout, purely informational.

**Deferred to `LATER.md`** (your answer): K30 — the "peer city" async ghost overlay *(needs Z1)* — you said it could be good but might also be confusing, and you want to prioritize working multiplayer into as many games as possible soon as "the next big development after this set" — parking this specifically until that multiplayer work is scoped, not rejecting it.

---

## Per-game: Le Champ de Mots

**Two real design changes in this section — read these before the checklist:**
- **L4 reverses this game's own row-unlock pacing design.** The original idea (a "days until next row unlocks" countdown) was rejected outright — your actual answer replaces it with two concrete steps below, touching the core "row-unlock pacing" mechanic this game has had since Milestone 1. Scope as its own real design pass, not a quick tweak.
- **L7 (study streak calendar) needs a real day-tracker built first** — the game currently has no actual concept of a calendar day (the player just advances "whenever"), so that infrastructure has to exist before the calendar view can be built. Split into its own prerequisite step below.

- [x] L4a: Remove the row-unlock pacing gate entirely — unlock every row immediately, so a player joining weeks into the course isn't locked out.
- [ ] L4b: Build a general placement test that lets a returning/advanced player skip past earlier content.
- [ ] L1: A fifth arcade minigame covering a sequence range not yet dedicated (e.g. passé composé/partitive weeks). **You also pitched a genuinely new idea here**, worth scoping as part of this same item: a music- or reading-based game that links to a Spotify song (quizzing on its lyrics/words) or an open-source short story (quizzing on its content) — decide whether this becomes L1's fifth minigame itself or a separate addition. **Also a real site-wide principle from this answer** (see Z-extra below): every practice-through-a-minigame action should visibly feed a measured top-level progress stat (watering count or equivalent), so playing a minigame always visibly "counts" toward something.
- [ ] L2: Let the visual-style switcher remember two saved per-context presets (e.g. Cartoon for casual review, Text-based for a focused cram session) instead of one single choice.
- [ ] L3: A "weak spot drill" mode generated purely from the error-pattern digest's flagged topics. **Also wire Review-tab practice into watering**: if a plot's topic hasn't been watered yet today, reviewing it through this (or any) practice mode should count as watering it, per your addition.
- [ ] L5: A "conversation simulator" — a longer-form practice mode chaining several related vocab/grammar items into a short simulated dialogue exchange.
- [ ] L6: Let the confidence-rating buttons show a small running accuracy-by-confidence stat, so the player can see whether their self-assessment is well-calibrated.
- [ ] L7a: Build the day-tracker prerequisite — a real concept of a calendar day, since the player currently just advances "whenever."
- [ ] L7b: A "study streak calendar" — a lightweight monthly calendar view of review activity, without guilt-driven streak-fire framing (needs L7a).
- [ ] L8: A small "plots automated" progress bar always visible at the top of the farm.
- [ ] L9: A "listening comprehension" practice type (TTS-based audio prompts) — **you noted audio is still hard, but L1's music-minigame pitch might be the practical way in**; scope these two together rather than solving audio comprehension from scratch here.
- [ ] L10: Let the gender-tagging drill show its own running accuracy stat, separate from the overall dashboard. **Same top-level "everything shows measurable progress" principle as L1 applies here too**, per your note.
- [ ] L11: A "sentence builder" freeform mode — a general-purpose sentence constructor usable with any mastered vocabulary at any time.
- [ ] L12: A small "next review due" countdown on each automated plot.
- [ ] L13: A "study buddy" pacing coach — an opt-in daily suggested review-session length based on how many plots are currently due.
- [ ] L14: Let the report-button flow show a short "thanks, noted" confirmation distinct from the normal question-feedback flow.
- [ ] L15: A "grammar deep-dive" panel per grammar topic — an optional expanded explanation beyond the terse in-practice rule.
- [ ] L16: A small visual distinction (border color or icon) between vocab/grammar/phrase/phonetic plot types on the farm grid itself.
- [ ] L17 **(you called this "very important"):** A "mixed review marathon" mode — a long-form session pulling due plots from across the entire farm regardless of row.
- [ ] L18: Let the weeds mix-up state show a small note naming exactly which other item it's being confused with.
- [ ] L19: A "personal phrasebook" — bookmark specific items into a custom cross-cutting list, independent of the syllabus row structure.
- [ ] L20: A small "catch-up progress" readout for already-unlocked rows, distinguishing "reviewed since unlocking" from "never yet watered." *(Note: since L4 above removes row-gating entirely, re-scope this as covering however "already unlocked" ends up being defined post-L4 — likely "every row.")*
- [ ] L22: Let the cultural-notes toggle show a small "new note available" indicator when a freshly-unlocked row has cultural context worth reading.
- [ ] L23: A "spaced repetition transparency" panel — an optional, fully explained view of exactly how the SM-2-style scheduling works.
- [ ] L24: A small animated watering-can cursor/effect when actively watering a plot.
- [ ] L25: A "review before the exam" cram mode — a dedicated denser review session covering everything from a chosen chapter range.
- [ ] L26: Let the liaison/elision quiz show a small phonetic-symbol legend.
- [ ] L27: A "farm-wide health" summary visualization — a single glanceable chart of the whole farm's mastery distribution.
- [ ] L28: A small badge/icon for perfectly answering a full row's worth of plots in one sitting.
- [ ] L29: A second, standalone mini-game family — a lighter, more frequent "quick water" mode (a single rapid-fire question, no full session) for very short study breaks. **Same top-level progress-visibility principle as L1 applies here.**

**Folded into Z (see "Games" section above):** L30's original "preserve visual style when navigating back from the hub achievements link" — generalize this into a site-wide UI-state-preservation principle, not a Le Champ de Mots-only fix, per your answer.

**Parked pending the audio question already tracked in `LATER.md`:** L21 — the pronunciation-practice mode (slowed TTS + syllable breakdown) — your answer was "audio is still an issue we are not dealing with yet"; add this to `LATER.md`'s existing "Standing question: what can you actually do with audio" section rather than duplicating that discussion here.

---

## M. New game concepts

A "yes" here means "worth a groundwork plan" (a new `planning/<game>-plan.md`, per this repo's own convention), not scoped work yet — per your own standing instruction for this section.

- [ ] M3 — **Signal**: a small, standalone daily puzzle game (Wordle-adjacent in spirit, original mechanic) — "may as well try it... that can be good," per your answer. Write a groundwork plan.
- [ ] M4 — **Undersleep**: a wellness-themed idle/management game balancing a daily schedule against a circadian-rhythm meter. You liked this one specifically and want it expanded — **also explore a life-tracker angle**, per your note that "there is a lot that can be done to make this more and better." Write a groundwork plan with that broader scope in mind.
- [ ] M6 — **Overclock** (roguelike deck-builder): accepted, but **scoped down for now** per your instruction — the initial groundwork plan should cover only the baseline every game gets (save system, settings panel, the other standard shared infrastructure), not the deck-building specifics. You're leaning toward a **space or cult theme/gimmick** — revisit the actual gimmick in the next ideas round, per your own instruction.
- [ ] M7 — **Last Line** (tower defense): accepted, **same scoping as M6** — baseline infra first, gimmick/specifics deferred to the next ideas round.
- [ ] M10 — **Deep Descent** (roguelite dungeon-crawler): accepted, **same scoping as M6/M7** — baseline infra first, specifics deferred to the next ideas round.

**Rejected/parked this round — too teaching-coded, per your own stated preference for "fun not learning" in new games:**
- M1 — **Compound Interest** (financial-literacy incremental) — parked unless a specific class assignment ever calls for it.
- M5 — **Rootstock** (digital-garden knowledge sim) — same reasoning, "I like it but again with these being too informative."

**Deferred to `LATER.md`, pending a feasibility/differentiation call:**
- M2 — **Silk Road**: you left this as "if you believe it is different enough [from Trade Empire], build it." My honest read: mechanically it's still "route goods between nodes reacting to market/events," the same shape as Trade Empire, just historically themed — not different enough from Trade Empire's existing mechanics to justify a whole new game without a sharper, more specific hook. Parking rather than building, but revisit if a genuinely distinct mechanic (not just a reskin) comes up.
- M8 — **Contraption** (physics-based sandbox puzzle): you asked "if you think it's possible, yes; otherwise no." Honest read: a real drag-and-place physics puzzle game needs a proper JS physics engine (e.g. Matter.js) and a much heavier interaction model than anything else on this site — feasible, but a bigger stack decision (similar in scale to Continuum's Three.js adoption) than a normal new-game groundwork plan. Parking until that's a deliberate decision, not building it as a default-scope game.
- M9 — **Offbeat** (rhythm/timing arcade): you flagged the same concern yourself — precise timing is hard given how these games load (Pyodide boot overhead), and audio is still an open question (see `LATER.md`'s audio section). Parking until both are resolved.

---

## X. Warframe Build Tracker

**This section now lives here instead of a separate local `warframe_build_tracker/TODO.md`** — that file has been deleted and everything it held is consolidated below, per your instruction (2026-09-20). It's still not part of the hub's own site (no game, not built with Pyodide), but it's tracked in this same list now rather than a second file. **`.gitignore`'s exclusion of `warframe_build_tracker/` has also been removed** — it can be committed to this repo.

**Already shipped, not carried forward as tasks** (kept here for context): the reverse "used in" lookup per resource, real farm/refine locations for all 65 resources, Amp/Zaw/Kitgun component grouping with honest per-slot notes, and the buildable-highlight + one-click Build button.

**Decided order of work (2026-09-20) — do these two first, everything else after:**
- [x] X-a **[BIG]**: Rearchitect the tracker from its current Flask app (`render_template`/`data.json`-on-disk) into a static HTML/JS frontend + small backend, matching the hub's own `admin.html` pattern — committed to this repo, unlinked from the hub nav, direct-URL only. Built as a full Python-via-Pyodide port (`game.py`, `index.html`, `style.css`) matching every other game's own stack — turned out no *new* backend was needed at all: the hub's existing `shared/hub-auth.js` + `shared/save-widget.js` (unmodified, `data-game-id="warframe-tracker"`) work against the already-deployed, game-agnostic FastAPI Cloud `/saves`/`/auth` endpoints exactly as-is. Real progress from the old `data.json` (24/33 parts owned, 55 tracked resources) was migrated into `game.py`'s bootstrap state, not lost. 33 new pytest tests (own fake-DOM harness, `tests/`), all green. Live-verified against the real production backend: saved anonymously (real code `ADHA-H47B`), reloaded the page fresh, loaded it back, and confirmed a Build-button click's state change round-tripped correctly — zero console errors throughout. Old `app.py`/`templates/`/`static/`/`data.json` removed.
- [x] X-b **[BIG]**: Add a `lastData.dat` file-upload/import feature on top of X-a's architecture. Inspected `warframe-api-helper`'s own source directly (no sample file existed) — confirmed `lastData.dat` is just the real (unofficial) Digital Extremes mobile-inventory-API JSON response, AES-128-CBC + PKCS7 encrypted with a key/IV that's hardcoded and published in that tool's own open-source code, so it's decryptable client-side with the Web Crypto API, no server round-trip, no secret involved. Built: an upload button + hidden file input, plain-JS AES-CBC decrypt (falls back to treating the file as already-plain JSON, for the tool's own `inventory.json` sibling output or AlecaFrame's format), handed to a new `import_last_data()` in `game.py` that fuzzy-matches each of the 65 tracked resources against the file's `MiscItems` list by the tail of its internal item path (not a hardcoded exact-path table, since the real schema isn't something this project could verify against a live sample) and fills only the "built" bucket — never part-owned counts or the "raw" bucket, since neither has a real equivalent in Warframe's own data model (a built component isn't a stackable countable item; "raw precursor" is this tracker's own convenience concept). Returns a plain summary naming exactly what matched and what didn't, so a partial/imperfect match is transparent, not silent. 8 new tests (41 total), all green. Live-verified end-to-end with a synthetic file encrypted using the same real key/IV: decrypted, matched, and applied correctly (confirmed via direct Pyodide state inspection), plus the plain-JSON fallback path separately. Honest caveat, documented in the code/README: matching accuracy against a *real* export hasn't been verified, since no real sample file was available to test against.

**Everything else (original tracker ideas):**
- [ ] Recursive refinery expansion — populate `MANUFACTURING_RECIPES` for the ~15-20 resources (Alloys, Toroids, Marquise-tier gems) that are themselves refined from a raw material; `flatten_recipe()` in `app.py` already supports expanding these recursively, it's just not populated yet.

**Everything else (round 2, from `IMPROVEMENT-IDEAS-ROUND-2.md` Section X):**
- [ ] A small "days since last `data.json` update" readout.
- [ ] A "build priority" sort/highlight — rank the 33 parts by "closest to buildable" (fewest missing resources), not the fixed category order.
- [ ] A small icon per planet/location on the resource location tooltip, for faster scanning.
- [ ] A "farming route planner" — suggest which single location would satisfy the most outstanding resource needs at once.
- [ ] A confirmation-gated "reset all inventory to zero" button.
- [ ] Expand the category-level "meta build" notes into per-part notes pulling from each part's own Wiki "Tips" section — **and go bigger, per your own note**: also track what the built parts *become* (e.g. a "177" amp combo), not just per-part tips. Ties directly to the build-comparison idea below.
- [ ] A small per-category (Amp/Zaw/Kitgun) progress bar ("X/Y parts complete"), not just one overall number.
- [ ] A "resource shopping list" export — a plain-text/copyable summary of exactly what's still needed.
- [ ] Let the "used in" tab show a resource's own total remaining-needed count inline.
- [ ] A source layer for resources gated behind **Syndicate standing**, not Void Relics — you confirmed none of the 65 resources are relic-gated, but some are standing-gated, so build that instead of the originally-pitched relic layer.
- [ ] A dark/light toggle for the tracker's own UI (a personal preference option, separate from the hub site's own much bigger dark/light-theme discussion in `planning/LATER.md` L5).
- [ ] A "resource value" heuristic — flag which owned resources are rare/hard-to-farm vs. common, to help prioritize which builds to do first.
- [ ] Visually distinguish Wiki links already visited this session.
- [ ] A small favicon for the tracker itself.
- [ ] A small inline "grindy" flag on resources with unusually high quantity requirements.
- [ ] A "build comparison" mode suggesting which un-built combinations are closest to completion — **specifically tracking known community "meta" combos**, per your note ("many people want to build the metas... rather than saying just build whatever"), not a quality-agnostic closest-to-complete ranking.
- [ ] A small manual "note to self" free-text field per part.
- [ ] A small confirmation toast ("Built!") on a successful Build click, replacing the current page-reload-based feedback.
- [ ] A "what's blocking me" summary at the top of the page — the single resource currently blocking the most builds.
- [ ] A small percentage-complete readout for the whole 33-part list.
- [ ] A mobile-friendly layout pass.
- [ ] A small "copy resource name" button next to each resource.
- [ ] A market-price reference (Warframe.market or similar) integration.
- [ ] An "archive completed parts" toggle to hide fully-built parts, **plus a search/sort system**, per your own addition, to make things easier to find.
- [ ] A "session farming log" (resource-inventory deltas over time) — makes a lot more sense once X-b's import exists, since manual entry alone makes deltas unreliable to track meaningfully.

**Deferred to `LATER.md`:**
- A "riven disposition" reference column for completed builds — "maybe much later, right now is a crafting and resource tracker," per your answer.

**Explicitly rejected, not carried anywhere:** a "build queue" (batch-build several parts in one click), and a per-part "last built" timestamp — both answered "no."

---

## Closing tasks (run these last, per your standing instruction)

- [x] A full site-wide bug-check pass, once everything above is done. (Done 2026-09-20: two real bugs found and fixed, see the BCM114/BCM206 dev logs.)
- [x] Generate a fresh round-3 ideas document (same 30-ideas-per-section format as `IMPROVEMENT-IDEAS-ROUND-2.md`) once this list is complete, for you to answer again. Generate a "gamify the teaching games" in the ideas document (Canopy, Grid, Tide, Aftermath, Herd, Thaw, Loop, Drift): fun-first, 30 ideas per game (10+ big, 10+ small), not duplicating round 2. Built 2026-09-21 as `planning/IMPROVEMENT-IDEAS-ROUND-3.md` (one file: gamify sections GB-GI, round 3 for all games A-L plus M/Z/Y/X, and Part 3 R "Returning later"). Was requested to be queued in this closing section rather than built now (round 2 wasn't framed around fun; carried over from the old TODO.md's closing task). Also pull eveything from later and make that a section.

---

## N. Recovered tasks

*(Added 2026-09-21 after an audit of both ideas rounds against this list, `LATER.md` and the code found approved items that had been dropped, half-carried, or attached to the wrong idea. Each line says why it was missed. Findings from the separate "were completed items really done?" audit get appended here too, as `V-` items, when that audit finishes.)*

### From round 1
- [ ] R1-other-1: Consolidate the workspace's floating markdown files. Your note: "the main workspace issue is all the md files are floating around that could be consolidated." Audit the `.md` files at the repo root, in `planning/` and in each `games/<slug>/` (e.g. `games/continuum/continuum-real-world-sources.md`); merge, archive or fold related docs so the workspace is less cluttered. Only resolved or superseded docs move to `planning/archive/`; update the root `CLAUDE.md` structure listing to match. *(Recovered: round 1 converted only the in-game decluttering half of this note.)*
- [x] R1-L14: Auto-discover each game's `achievements.json` for the hub achievements dashboard instead of the hand-maintained `GAMES_WITH_ACHIEVEMENTS` map in `script.js`. You answered "yes". GitHub Pages has no directory index, so use a generated manifest (a script like `scripts/generate-last-updated.py`, or extend `game-added.json`). *(Recovered: I recorded "no change needed" without your agreement.)*
- [x] R1-L13: Site-wide keyboard-accessibility pass on the hub shell (`index.html`, `whats-new.html`, `roadmap.html`, `admin.html`, `terms.html`): logical tab order, every interactive element reachable and operable by keyboard (title-card links, star widget, `<details>`, sign-in/sign-up forms, banners), sensible focus management on view switches. *(Recovered: only the focus-ring half landed, as Y28.)*

### From round 2
- [x] R2-Y14: Finish the hub footer: add the site name, a link to the public GitHub repo, and a feedback/contact link (anchor to the site-feedback section) to the existing `.hub-footer` (currently only Terms & Privacy, What's New, Roadmap). If a contact address is wanted, add one question to `planning/FOR-YOU.md`. *(Recovered: the TODO closed Y14 as "repo already public" and dropped the footer request.)*
- [x] R2-Z9: Record the cross-game "campaign" idea (one combined progress checklist across all games) in `planning/LATER.md` with your words: "maybe later but probably not, I am trying to let all the games exist on their own right now". Do not build it. *(Recovered: your answer appeared nowhere.)* Done — added under a new "Z. Games (cross-game)" heading in `LATER.md`'s Round 2 section.
- [x] R2-Z23b: Build the hub-side profile display for earned holiday-event badges (e.g. "christmas 2026" from a week-long Christmas Canopy event), stored on the account or save; coordinate with Z23's event mechanism. *(Recovered: the badge display had no concrete task.)*
- [ ] R2-multiplayer: Write a scoping plan for the "full multiplayer pass" you said is the next big development: which games get which multiplayer feature, and the shared backend needs beyond Z1. Items waiting on it: B5, D25, E9 (build-out), E11, F7 (build-out), K30. *(Recovered: the dependent items sit in LATER but nothing owned the pass itself.)*
- [ ] R2-C16: Grid: add a "first battery built" achievement (and the other first-plant-type callouts as achievements) with the in-game achievement pop-up, per your note that callouts should become achievements. *(Recovered: C16 was folded into the generic callout audit, which never creates it.)*
- [ ] R2-E3: Aftermath E3: your note "this will add a bunch of new nodes with important decisions" belongs to E3 (the disaster-type specialization branches), not E1. Check that E3 is a real multi-node branch with meaningful decisions, not one extra node; extend if it is thin. *(Recovered: the note was attached to the wrong item.)*
- [x] R2-F29: Herd F29: you asked "is this realistic? if there are real-world examples, yes; otherwise no." Research whether excess methane-capture capacity is actually sold or credited (biogas, carbon-credit markets), write the finding into `planning/FOR-YOU.md`, then build or drop F29 on that basis. *(Recovered: nothing made the research happen.)*
- [ ] R2-K26: Continuum: you said "rather than closing it, let's keep making more eras." Build an eighth era beyond Space Age (sim content, research tier, sustainability mechanic, log/transition beats, info-panel content, Three.js scene, tests), then keep going. *(Recovered: the request was reduced to a scoping note, K26b.)*
- [x] R2-L1b: Le Champ de Mots: retrofit the practice modes so each visibly feeds a measured progress stat and the player score (the four arcade minigames, gender drill, liaison quiz, proficiency tests, bonus sentence sections), per "practice through games should show progress on respective topics... it should impact the player score" and "everything gives progress to something measured at the top". *(Recovered: the TODO called it a forward-looking principle, not a retrofit.)*
- [x] R2-X17: Warframe tracker feasibility, resolved in conversation rather than as a separate FOR-YOU.md write-up: (a) direct/live account linking isn't practical (no public live API; `warframe-api-helper`/AlecaFrame only ever produce a one-time exported `lastData.dat`/`inventory.json` snapshot while the game is running) — the real answer was to build the file-import path itself rather than write a report about it, which X-b already did (client-side decrypt + fuzzy resource-name matching, see `warframe_build_tracker/README.md`'s "Importing a real inventory snapshot" section). (b) Frame/weapon/companion crafting tracking is still genuinely out of scope/not built — the tracker remains scoped to the original 33 Amp/Zaw/Kitgun parts; revisit as its own item if wanted later.

### Answers to re-review (not yet tasks)
- [ ] R2-review: C21 (grid twin) and D3 (multi-settlement) got "I'll let you make the call" and are parked in `LATER.md` pending a real scoping conversation — user wants to have that conversation now (see next session). K9 and X23 resolved: user confirmed keep both as their own plain build items, no folding/moving.

### Completion audit: round-1 items marked done that weren't fully done (Thaw, Loop, Drift, Trade Empire, Continuum)
*(Found 2026-09-21 by re-checking each ticked item against the code. Where it says "confirm with user", that is a judgement call for you, not a silent fix.)*
- [x] V-E-1: Thaw G2 - `best_region_message()` (games/thaw/game.py ~506) only says which region has lowest temperature; original ask was to name "what investment mix achieved it". Add the winning region's preserve/monitor/output unit mix to the line.
- [x] V-E-2: Thaw G5 - user chose a real number over the vague wording. Info-toggle (index.html) now states the fixed +1.0°/round works out to roughly 50 real-world years, calibrated from NOAA's current warming rate (~0.20°C/decade since 1982) against `BASE_TEMP_RISE_PER_ROUND`; caveat that it's stylized/compressed kept.
- [x] V-E-3: Thaw G10 (minor) - the "dampening delayed a threshold" callout keys off a new +15 degree SECOND_WARMING_MILESTONE, not the melt threshold (+10) the user's idea referenced. User confirmed: leave as-is, no change.
- [x] V-E-4: Loop H10 - the "2.5x cost multiplier is a hard ceiling" note is only a hover `title` on #damage-display (game.py ~1237), invisible on touch. Make it visible text (or info-toggle) near the environmental damage meter.
- [x] V-E-5: Loop H13 - milestone toasts at 25/50/75/100% are only the one-shot achievement-unlock toasts (quarter_loop/half_loop/three_quarter_loop/loop_closed) plus a particle burst; no dedicated milestone toast, and achievement toasts never repeat on later chains. User confirmed: substitution is fine, just don't let it overlap the loop-closed banner. Fixed the one real overlap case (loop-closed banner + achievement toast firing together) by delaying the toast until the banner's window passes.
- [x] V-E-6: Loop H20 (minor) - "2-3 alternate goods-flavor sets" is the same goods-category picker as H2 (label/item/icon only); no distinct flavor content. User confirmed: distinct. Built `CATEGORY_LOOP_DETAIL` giving each category its own concrete loop mechanics across every fraction bucket.
- [x] V-E-7: Drift I8 (minor) - coda still shows three meter bars, now with a "today" marker and "Today X -> generations from now Y" text, rather than replacing the bars with a separate before/after comparison. User confirmed: close enough, no change.
- [x] V-E-8: Trade Empire J11 - per-route readout (`_route_profitability_lines`, game.py ~1775) shows lifetime total credits per good route plus a trend arrow, not "profit-per-trip". Add avg profit per trip (total / trips) to each route line.
- [x] V-E-9: Continuum K7 - investigated per user request rather than ratified blind. This was a false positive: two unrelated ideas coincidentally share the label "K7" from different rounds. Round 1's K7 (LATER.md: "a way to actually view a revisited era's snapshot in the 3D layer, not just its stats," answered "later") was itself separately built later, in Milestone 15's "Look Back" feature (`games/continuum/game.py` ~line 1184, `render_revisit()`) — confirmed it genuinely re-renders the real Three.js scene for the revisited era via the existing render layer, not just stats, exactly the deferred ask. Round 2's own, differently-worded K7 ("civilization summary" end-of-playthrough report, the one checked off in this file's K-section) is a completely different feature that never went through LATER.md at all. Nothing was built against an unratified "later" answer; both ideas are legitimately done. Removed the now-stale K7 entry from `planning/LATER.md`.
- [ ] V-E-10: Continuum K15 - ask was to confirm accessibility settings (text scale, colorblind) persist through a real save/load; result was "they don't, and that's by design" (CLAUDE.md Milestone 16). Get the user's explicit agreement that browser-level-only persistence is acceptable, or make them round-trip via save state.

### Completion audit: round-1 items marked done that weren't fully done (SOL, Canopy, Grid, Tide, Aftermath, Herd)
*(Found 2026-09-21. The archived list's Aftermath labels shifted by one from E5 on, which is how E20 fell off it.)*
- [x] V-CD-1: Aftermath original idea E20 (user said yes): make the Growth button/readout show its ACTUAL current payoff (e.g. "+16 resources/event" at growth 2) instead of static "+8 resources". Never built and not in TODO/LATER: archived TODO E-labels from E5 onward were shifted by one vs planning/archive/IMPROVEMENT-IDEAS-2026-09.md, so the last idea fell off the list. games/aftermath/game.py only sets "Invest in Growth (cost)"; index.html info text is static.
- [x] V-CD-2: Aftermath "E6" social event category (Civil Unrest) was built and marked done but is original idea #5 which the user answered "later". User confirmed: keep it. Removed the now-pointless Aftermath "E5: later" entry from `planning/LATER.md`.
- [x] V-CD-3: SOL A18 "reset this world only": user answered "later"; built anyway (Reset This World button, test_reset_world.py) and marked [x] with no recorded approval; LATER.md still lists it as deferred. User confirmed: keep it. LATER.md's SOL A18 entry removed.
- [x] V-CD-4: SOL A3 welcome-back toast: idea was "what changed since last session"; built is a static snapshot ("N/8 worlds visited, X achievements earned") fired only on save load (game.py _show_welcome_back_toast). User confirmed: real delta. Built a per-browser localStorage snapshot comparison (same pattern as Canopy's personal_best/Tide's best_coastline_saved), falling back to the static wording on first load or a same-or-lower reload.
- [x] V-CD-5: Canopy B3 second biome: user idea specified "different degradation/compounding rates"; Highland Grove (games/canopy/game.py ~line 456) reuses identical Plot rates. User confirmed: add distinct. Built `HIGHLAND_DEGRADE_MULTIPLIER` (1.5x faster soil degradation) and `HIGHLAND_GROWTH_MULTIPLIER` (0.75x slower compounding), grounded in alpine-ecology framing already established for the biome.
- [ ] V-CD-6: Aftermath E4 legacy system: idea was a visual settlement marker referencing prior runs; built is only a per-event-type count chip row (legacy_event_counts). Add a marker on the settlement art tied to run history, or get user sign-off.
- [x] V-CD-7: Grid C11 (user said yes): archived TODO marked [x] while saying it was moved to LATER (never agreed). Feature is now satisfied via round 2 (/stats/games/grid/percentile in app/main.py + Grid index.html), so only cleanup needed: remove the stale C11 entry from planning/LATER.md. Done — confirmed the endpoint/hook both exist, removed the stale LATER.md entry.
Not audited (site-wide goals, folded lines): C1/D1/E1 mobile dock, B15 pin-restraint condition.
Test suites at audit time all pass: sol 670, canopy 350, grid 311, tide 202, aftermath 244, herd 174.
---
All six suites pass at audit time (sol 670, canopy 350, grid 311, tide 202, aftermath 244, herd 174).

### Completion audit: round-1 site-wide goals marked done that weren't fully done
*(Found 2026-09-21. Includes the fact that the "gamify the teaching games" ideas document was ticked off in the old list without being built; it is now queued in Closing tasks.)*
(paste-ready)
- [x] V-AB-1: Le Champ de Mots visual-style switcher was DEVIATED from the user's request. User wrote (ideas doc L, ~line 567): "When you first load in you choose a visual style which can be accessed through settings." Built instead: High-def auto-applied on first visit, no first-load chooser (`games/champ-de-mots/visual-style.js` header comment states this was a deliberate reinterpretation; `index.html` line ~43 too). The user never agreed to dropping the picker. Remaining: add a first-run picker (four options, shown once when `localStorage["champ-de-mots-visual-style"]` is unset, still changeable in Settings), or get the user's explicit OK to keep the auto-default. Also disclose/confirm that low-poly/cartoon/text-based are CSS-only chrome treatments (visual-styles.css) rather than distinct art.
- [x] V-AB-2: Mobile-dock reserved bottom padding is ineffective in Grid, Canopy, Tide, Aftermath and Trade Empire. Their mobile `@media` rules `body { padding-bottom: 130/268/230/230/150px }` (grid/style.css ~659, canopy ~1130, tide ~1227, aftermath ~1062, trade-empire ~1174) lose to `ad-bar.css`'s unconditional `body { padding-bottom: 66px }` because ad-bar.css is linked AFTER style.css (same specificity). Continuum's CLAUDE.md Milestone 20 found this, fixed only Continuum (`html body {...}`), and flagged the rest as a follow-up that is not in any TODO. Result: docked panels/buttons can cover the page's last content on phones. Fix: change those five rules to `html body { padding-bottom: ... }` (or ad-bar.css to `:where(body)`), verify at 375px width.
- [x] V-AB-3: Grid mobile-dock was DEVIATED: ideas doc C1 asked to dock "Grid's plant-build action row"; what was built docks only `#advance-round-button` (`games/grid/index.html` ~535-546 admits the label mismatch; documented as a "judgment call" in games/grid/CLAUDE.md). Same pattern for Continuum K9 (only Advance Season docked). User confirmed: keep the lighter version deliberately — "if you pin too much then might as well be pinning nothing, because at some point everything will feel important enough to be pinned." No change.
- [ ] V-AB-4: Archived TODO "Closing tasks" item 3 (second ideas doc "gamify the teaching BCM114 games") is checked `[x]` but its own text says "moved to TODO2.md ... not built yet". Nothing was generated. It IS re-queued (unchecked) inside the live TODO.md round-3 ideas-doc line (~887), so nothing is lost, but the archive's [x] is wrong: keep that live item open until the gamify doc exists and confirm nobody counts this as done.
- [ ] V-AB-5 (minor): 4 games' achievements-panel hub link goes to `../../index.html` without the `#account-achievements-dashboard` anchor (tide game.py ~1283, trade-empire ~1702, champ-de-mots ~2465, canopy ~2144), while SOL, Continuum, Grid, Herd, Loop, Drift, Thaw, Aftermath use the anchor. Make them consistent.
- [x] V-AB-6 (minor, judgment call needing user OK): UI decluttering pass — user said "everything looks very crowded ... collapsible or other screens". Canopy and Le Champ de Mots were self-audited as "not genuinely crowded" and left unchanged (Champ has a 722-cell farm plus many toggle buttons/panels). User agrees. No change.
- [ ] V-AB-7 (cosmetic): root CLAUDE.md "Working notes" still says to revisit whether Instagram/audience-engagement content is needed, but this was resolved 2026-09-15 (no). Delete/rewrite that stale bullet.
