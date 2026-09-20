# Canopy — Deforestation & Carbon Sinks Game

**Read `../climate-quartet-plan.md` first for shared conventions (testing, feedback hook, hope-angle requirement, hub integration).** This file is Canopy-specific only. **Build this one first** — it's the simplest of the four and establishes the pattern the others follow.

## Concept

A single forest region divided into a grid of plots. Each plot can be cleared (for quick resource income), left alone (slow passive value growth), or replanted (recovery after clearing, slower than never-cleared). Combines active management (clicking individual plots) with passive/idle accumulation (value compounds over time on preserved/replanted plots).

## Climate issue & hope angle

**Issue:** land-use change and loss of carbon sinks.
**Hope angle:** replanting must visibly work — a cleared plot that gets replanted should recover, just more slowly than if it had never been cleared. The game needs an end-state or late-game moment where a mostly-preserved/restored forest is clearly thriving (a visible "if you'd done this from day one" or "recovery is real, just slower" signal), not just a number going up.

## Core loop

- One forest region, rendered as a grid of individual plots (not one abstract meter — the spatial layout matters for the "some plots recovering, some still bare" visual).
- Player can click a plot to: clear (immediate resource payout, plot becomes bare), preserve (do nothing, passive value accrues), replant (costs a little, starts a slower recovery timer).
- Passive value compounds the longer a plot stays intact — a multiplier that grows over time, not a flat rate, so patience is rewarded increasingly.
- Cleared plots degrade in *future* yield potential (soil quality drops) — clearing repeatedly on the same plot gets worse, not better, over time.
- No fail-state. It's a comparison game — the player accumulates two visible numbers over a session: total short-term resource income vs total standing forest value — and can watch how the balance shifts depending on their play style.

## Milestones

| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Grid + plot states | Grid of plots, each with a state (bare/preserved/replanting/recovered), basic click interactions. Tests: state transitions per plot action | Done |
| 2 | Passive value accumulation | Compounding value formula for preserved/recovered plots. Tests: value-growth-over-time calculation | Done |
| 3 | Clearing payout + soil degradation | Resource payout on clear, degrading future yield on repeated clearing of the same plot. Tests: payout calculation, degradation stacking | Done |
| 4 | Replant recovery timer | Replanted plots recover on a slower timeline than never-cleared ones, reaching near-parity eventually. Tests: recovery timer logic, near-parity threshold | Done |
| 5 | Comparison scoring + hope-angle payoff | Surfacing the short-term-income vs standing-forest-value comparison clearly at session end. Tests: comparison calculation across sample play logs | Done |
| 6 | In-game feedback prompt | Piped to Neon backend per root conventions | Done |
| 7 | Visual pass + hub integration | Grid rendering, plot state icons/colors, session summary screen | Done — all 7 milestones complete |

## Iteration Notes — Pass 1 (implemented)

Design-review pass (pre-playtest, from `climate-games-iteration-pass.md`). Anticipated issue: the plot-grid mechanic risked feeling passive/idle without clear stakes, and soil degradation from repeated clearing risked not reading clearly without a tooltip.

**Built in response (see `BCM114-DEV-LOG.md` 2026-08-11):** a continuous plot-maturity color gradient (bare → light green recovering → deep green mature) plus a recovery-milestone flash, and a short factual context blurb referencing a real reforestation approach. Audio cue on recovery was considered and skipped — no audio system in the stack; the visual-only version shipped instead.

**Open testing question:** do players notice degradation stacking on repeatedly-cleared plots without being told? Is plot state readable at a glance across the session?

## Iteration Notes — Pass 2 (implemented)

Second design-review pass, from `climate-games-iteration-pass-2.md`, building on Pass 1. **Selected additions: A (biodiversity sub-meter) + B (stakeholder tension).**

- **Biodiversity sub-meter:** preserved and recovered plots accumulate a biodiversity value over time, separate from the passive economic value already tracked — represented simply (e.g. small wildlife icons appearing on well-established plots) rather than another number to read. Deepens the hope payoff: a thriving late-game forest isn't just economically valuable, it visibly has life in it.
- **Stakeholder tension:** periodically, the player faces a plot-specific decision where local community needs (a request to clear a specific plot for housing, farming, or resources) conflict with preservation. Not a trap or a "wrong answer" mechanic — meant to introduce real ethical weighing (whose need matters, short-term vs. long-term) rather than making preservation an obviously correct default choice every time.
- **Visual polish for this pass:** biodiversity should be legible at a glance (small animated wildlife sprites/icons on mature plots, subtle motion) without cluttering the plot grid. Stakeholder-tension moments should get a distinct visual treatment (a different UI panel or framing) so they read as a different kind of decision than routine plot management.

## Iteration Notes — Pass 3 (Fun/Teaching Balance)

Third design-review pass, from `climate-games-fun-teaching-balance.md`. **Risk:** the idle/passive accumulation side of the mechanic risks tipping toward boredom — if preserving a plot mostly means waiting, without active skill or decision-making, flow drops even though the "lesson" (restraint compounds) is technically still present.

**Assessment:** the *choice of which plot to clear and when* was already reasonably skill-based going into this pass — soil degradation punishes repeatedly clearing the same plot, compounding growth rewards patience but stakeholder tension specifically targets whichever plot is currently most established, so a player who understands the system has real reasons to selectively harvest rather than just wait uniformly. The actual gap was pacing: the two Pass 2 systems meant to break up idle stretches (stakeholder-tension requests, the biodiversity wildlife-icon payoff) weren't paced against each other. Stakeholder requests fired every 20 ticks, but the first biodiversity payoff (wildlife icon) didn't land until 50 ticks in — well after two stakeholder cycles had already passed — so the early game's only felt beat was the same grant/decline decision repeating, with nothing new arriving to reinforce that preservation itself was paying off.

**Built in response:** tightened both intervals so they land close together early rather than one at 20 ticks and the other at 50. `STAKEHOLDER_EVENT_INTERVAL_TICKS` dropped from 20 to 15. `BIODIVERSITY_WILDLIFE_THRESHOLD` dropped from 1.0 to 0.2 (accrual rate unchanged), so the first wildlife icon now appears around tick 11 instead of tick 50 — inside the first idle stretch instead of after it. No new mechanics added; this is timing/frequency tuning of what Pass 1/Pass 2 already built.

## Info Page — real-world sources (implemented)

*Implementation is now shared across all 8 climate-quartet games — see `shared/info_page.py` and `shared/info-page.css`. Only the content below (framing/tie-in/sources) is Canopy-specific; the rendering/toggle code moved out of this game's `game.py`.*

An optional, player-triggered "The Real Story" panel — never forced mid-session, since the mechanic teaches first and this is a supplement for players who want to go deeper. Toggled via a button near the top of the page; shows a short framing paragraph (written fresh, not copied from any source), a one-line note tying the mechanic to real data, and a sources list with clickable links.

**Framing:** Standing forests are one of the world's largest active carbon sinks, and clearing them for quick income is one of the largest reversible sources of emissions — reversible because forests left alone, or given light assistance, can recover. Canopy's core tension, clear it now or let it compound, is a simplified stand-in for that real land-use tradeoff.

**Mechanic tie-in:** Canopy's replant-and-recover path loosely echoes real "assisted natural regeneration" — a genuinely cost-effective restoration approach, rather than costly full replanting from scratch.

**Sources:**
1. [World Resources Institute — Forests in the IPCC Special Report on Land Use: 7 Things to Know](https://www.wri.org/insights/forests-ipcc-special-report-land-use-7-things-know) — explains why deforestation and forest carbon sinks are two sides of the same coin, mapping directly to Canopy's clear/preserve tension.
2. [World Resources Institute — How Effective Is Land At Removing Carbon Pollution? The IPCC Weighs In](https://www.wri.org/insights/how-effective-land-removing-carbon-pollution-ipcc-weighs) — real reforestation carbon-removal potential, grounding the "replanting works, just slower" hope angle in actual IPCC figures.
3. [UNFCCC — Land Use, Land-Use Change and Forestry (LULUCF)](https://unfccc.int/topics/land-use/workstreams/land-use--land-use-change-and-forestry-lulucf) — the formal policy framework for tracking forest carbon sinks internationally.
4. [Climate Change Resources — Deforestation & Reforestation](https://climatechangeresources.org/learn-more/science/reforestation-deforestation/) — accessible overview with links to real reforestation organizations, for players who want to go from facts to action.

All four links verified live before merging.

## Audit Notes — Code-quality pass (implemented)

Site-wide bug/cleanup audit. Found one real bug: a pending stakeholder
request names its target plot by index, but nothing stopped the player
from selecting that same plot and clicking Clear directly instead of
using Grant/Decline. That left the request stale — Grant would hand out
its relations bonus for free (the plot was already BARE, so `clear()`
paid out nothing), Decline would penalize relations against a plot that
wasn't standing anymore, and since `maybe_trigger_stakeholder_request()`
refuses to raise a new request while one is already pending, the whole
stakeholder-tension system could get stuck indefinitely if the player
never happened to click Grant/Decline on the now-meaningless request.

**Fixed:** `grant_stakeholder_request()`/`decline_stakeholder_request()`
now check the target plot is still in an accruing state before applying
their relations delta, and `tick()` drops a request whose target is no
longer standing so a fresh one can still fire later. Everything else
audited clean — no other bugs, no convention violations (relative paths,
save-widget contract, test structure all check out).

## Audit Notes — Code-quality pass 2 (implemented)

Second, more aggressive audit pass covering minor/cosmetic issues as well
as bugs, per a hub-wide follow-up. Re-checked the stakeholder-request
guard from pass 1's fix for remaining edge cases (tick ordering around
recovery/accrual, save/load field handling) — found nothing further
there; `load_state()` already restores `plots` field-by-field onto the
existing `Plot` instances rather than replacing the list wholesale, so no
stale-reference risk exists for save/load.

**Found and fixed a real bug:** `render_grid()` rebuilds every plot tile
element from scratch on every `render()` call (at minimum once per tick,
i.e. once a second for the life of a session) and wired a fresh
`create_proxy(...)` click handler onto each one, but never `.destroy()`d
the previous render's proxies. Each `create_proxy()` call allocates a
persistent Python↔JS bridge object that Pyodide does not garbage-collect
on its own, so the old proxies leaked indefinitely even though the DOM
nodes they were attached to were long gone — a slow memory leak over a
long play session. Fixed by tracking each plot's current click proxy in
`_plot_click_proxies` and destroying the previous one before creating its
replacement each render. Covered by `tests/test_proxy_cleanup.py`.

**Also removed:** a dead `WILDLIFE_ICON` constant — the wildlife icon is
actually rendered via CSS (`.plot-has-wildlife::after`'s `content` in
style.css), so the Python constant was leftover and unused.

No other issues found worth changing; economy/scoring numbers were left
untouched per this pass's scope.

## Visual Pass — Space Theme (implemented)

Site-wide visual overhaul pass (flat/blocky panels → depth + space theme),
applied here per the shared design system already shipped for the hub and
SOL (`shared/space-bg.css`, SOL's `index.html`/`style.css` as reference).
Adopted the shared starfield/nebula background, gave `#game` and every
`.section` panel (info page, stats, action panel, legend, feedback prompt)
the translucent glass-panel treatment (gradient background, backdrop
blur, violet-tinted border, soft shadow), restyled `button.secondary`
with a two-stop gradient + glossy top highlight + a new brighten-on-hover
state, gave the `<h1>` a gradient-glow text treatment (green-tinted to
match Canopy's forest theme rather than reusing SOL's blue), and switched
flat gray borders/dividers (`.plot-tile`, `.legend-swatch`) to the
violet-tinted `rgba(140,160,255,...)` convention. `.stakeholder-panel`
kept its amber-accent identity but reskinned to the same glass treatment.

**Deliberately left untouched:** `.plot-preserved`/`.plot-bare`/
`.plot-replanting`/`.plot-recovered`'s exact hex values (state-identity
colors, also reused as the legend-key swatches), the wildlife icon and
`plot-sparkle`/`wildlife-flutter` keyframes (existing decorative motion —
no no-motion test or design-decision constraint exists for Canopy, unlike
some other quartet games), the `context-blurb`'s green border-left
accent, and every color literal inside `game.py` (`BARE_COLOR`,
`REPLANTING_START/END_COLOR`, `GROWING_START/END_COLOR`) — those drive
the actual per-plot inline `backgroundColor`, which is exactly the
state-meaning color this pass was told not to touch. No CSS class/id
selector was renamed. Canopy has no meter/progress-bar element, so that
part of the shared pass didn't apply here. Full `tests/` suite (131
tests) stayed green throughout.

## Settings panel (site-wide goal, planning/TODO.md, origin A9)

A consolidated settings panel — text-scale (A−/A/A+ buttons, same clamp/step
shape as Continuum's Phase 5 `accessibility.js`) and a reduced-motion
checkbox — toggled from a new "⚙️ Settings" button in the top toolbar
alongside Tutorial/How to Play/Reset Session, rendered into a
`.section`-styled panel matching the existing `#howto-panel`/
`#achievements-panel` hidden-until-opened idiom.

Built as `settings.js`, deliberately independent of Pyodide entirely (same
discipline as Continuum's `accessibility.js`) — it has no Python dependency
and works even if `game.py` never boots, wired up in `<head>` before
`game.py`'s own `<script>` runs. `style.css` gained a `:root
{ --text-scale: 1 }` custom property read by `html { font-size: calc(16px *
var(--text-scale, 1)) }` (every font-size in this file is already in rem,
confirmed by grep, so scaling the root font-size scales the whole game
uniformly with zero other changes needed) and a blanket
`html[data-reduced-motion="true"] *` override collapsing every
animation/transition to effectively instant — additive to, not replacing,
this game's own existing `prefers-reduced-motion` media-query-gated rules
(`wildlife-flutter`, `plot-sparkle`, `value-pop-float`,
`stakeholder-badge-pulse`, `forest-visual-sway`).

**Deliberately no sound toggle** — this hub has no audio system built
anywhere yet (see `planning/LATER.md`'s "what can you actually do with
audio" standing question), so a sound control here would control nothing
real.

Both settings are a browser-level UI preference, not game state — persisted
to `localStorage` (`canopy-text-scale`, `canopy-reduced-motion`),
deliberately never touching `get_state()`/`load_state()`, since a save code
is meant to be portable across devices/browsers and a local browser's
accessibility preference shouldn't silently override another device's.

Verified live: 268/268 pytest suite unaffected (pure HTML/CSS/JS, no Python
touched); in a real browser, applying a 1.3 text-scale correctly computed
`<html>`'s font-size to 20.8px, and enabling reduced-motion collapsed a
sampled `.forest-visual-tree` element's live `animation-duration`/
`transition-duration` to ~1e-6s, both persisting to their localStorage
keys, with zero console errors. Verification required cache-busting the
stylesheet `<link>` directly (a fresh `?v=` query on its `href`) to
sidestep this sandbox's own known static-asset HTTP-caching quirk (a
plain reload kept serving a stale `style.css` even after a fresh
navigation) — not a defect in the shipped code, the same environment
hazard Continuum's and SOL's own build notes already document.

## Tech notes

- Python/Pyodide, per root conventions.
- Keep the plot grid as a simple 2D array of plot-state objects — straightforward to test and to render.

## Onboarding-tooltip coverage check (site-wide goal, planning/TODO.md, origin A14)

Audited, no change needed. Checked whether a returning player who skipped
or forgot the tutorial (`shared/tutorial.js`'s spotlight walkthrough) can
still make sense of the permanent UI's non-obvious parts, on top of the
persistent, reachable-any-time `#howto-toggle-button`/`#howto-panel`.

Found the permanent UI already covers every non-obvious mechanic, at two
layers:
- **Section-level `.info-toggle` (i) icons** (from an earlier "add info
  buttons explaining non-obvious mechanics" pass) on the legend
  (Preserved/Bare/Replanting/Recovered — explaining compounding growth,
  soil degradation, and the biodiversity/wildlife threshold) and the
  stakeholder panel (explaining the grant/decline asymmetry).
- **Per-plot tooltips**, one level more granular than the legend: every
  plot tile carries a live `title` + `data-tooltip`/`aria-label`
  (`_plot_tooltip_text()` in `game.py`) giving that exact tile's
  coordinate, state, current value, soil %, and (while replanting) ticks
  remaining to recover — the same per-tile on-demand-detail pattern as
  Tide's D19 flood-threshold tooltips, already present here independently.

Everything else in the permanent UI is self-explanatory without a tutorial
(grid-size `<select>` with plain labelled options, a plain Reset Session
button, achievements/session-summary panels that are read-only recaps with
their own descriptive text, and the Settings panel's plain text-scale/
reduced-motion controls) — no gaps found, nothing added.

## "What's New" changelog panel (site-wide goal, planning/TODO.md, origin K16)

A new `changelog.json` manifest (flat list of `{date, entry}` objects,
hand-authored newest-first, dates sourced from real commit history via
`git log --follow -- games/canopy/CLAUDE.md` rather than guessed) plus a
"📋 What's New" toggle+panel, following the exact same hidden-until-opened
`.section` idiom and dynamic-DOM-build pattern `#achievements-panel`
already established here. Fetched into the Pyodide boot sequence alongside
`achievements.json` (`window.CHANGELOG_JSON`), with the same disk-read
fallback for the pytest harness's fake `js` module that `ACHIEVEMENTS`
already uses. `render()` keeps an open panel live on every tick/action,
same as every sibling panel.

Tests: 268 → 278 (new `tests/test_changelog.py`: catalog sanity, toggle
open/close, panel content matches `CHANGELOG` newest-first, render-time
liveness). Verified live under Pyodide: forced a fresh (`cache: 'no-store'`)
fetch + re-exec of `game.py` to sidestep this sandbox's known static-asset
HTTP-caching quirk (the *inner* `fetch("game.py")` call inside the boot
script kept resolving to a stale cached response for that exact URL no
matter how the outer page URL was cache-busted — a stricter case of the
same caching hazard SOL/Continuum's own build notes already document for
`style.css`); with the fresh code loaded, the panel opened, listed all 9
real entries with correct dates/text in newest-first order, and closed
correctly. **Found and ruled out as pre-existing:** an "Object has already
been destroyed" Pyodide console error appears on idle page load — verified
via `git stash` that it reproduces identically on the unmodified,
pre-existing codebase with zero interaction, so it predates and is
unrelated to this change; left uninvestigated as out of scope for this
pass.

## UI decluttering pass (site-wide goal, planning/TODO.md closing task)

Audited whether Canopy's single-page view is too crowded, per the
site-wide "UI decluttering pass" task (the user's own note: "everything
looks very crowded... making sections either collapsible or other
'screens' within a game could help"), the same review already run against
SOL in this same pass (see that game's `CLAUDE.md` — a real problem found
and fixed there: unconditional 6-7-card `cross-summary` stacks on every
planet view).

**Audited, no real crowding problem found here — no change made.**
Compared against SOL's actual issue (many redundant always-visible cards
stacked with no grouping), Canopy's desktop layout doesn't have an
equivalent: every major block — `#stats`, `.legend`, `#stakeholder-panel`,
`#action-panel`, `.legend`, `#feedback-prompt`, `#info-page-panel` — is
already its own visually distinct bordered/colored `.section` card (the
site's existing "HUD module" treatment, `style.css` lines ~807-816, one
accent color per section, same pattern SOL uses), not an undifferentiated
wall of text. On top of that, several already-built features already
reduce crowding as a side effect, exactly as this task's own framing
anticipated: `#achievements-panel`, `#settings-panel`, `#changelog-panel`,
`#session-summary-panel`, and `#info-page-panel` are all hidden-until-
opened behind toolbar buttons; `#stakeholder-panel` only renders when a
request is actually pending; `#highland-section` stays hidden until the
second grove unlocks; and B15 (`#mobile-info-dock`) already wraps the
stats+legend pair behind a collapsed-by-default toggle specifically on
mobile, where the same fixed content is proportionally more crowding than
on desktop. The only always-visible desktop stack is plot-grid → stats →
legend → (stakeholder, when pending) → action-panel → highland-banner →
feedback-prompt — six or so clearly-labeled cards, not the kind of dense,
ungrouped pile this task is aimed at. Matches the "audited, found no real
issue, made no speculative change" precedent this file's own Onboarding-
tooltip and Code-quality audit notes above already set.

Verified: full 278/278 pytest suite green (no change made, ran as the
baseline check this pass calls for regardless of verdict).

## Round-2 improvement pass (planning/TODO.md "Per-game: Canopy", 2026-09-20)

Built B2 (already true: `stakeholder_request_message()` has used `plot_coordinate_label()` since the original B4, now covered by the new tests' assertions), B3, B4, B6, B7, B8, B9, B10, B11, B12, B13, B14, B15, B16, B17, B18, B19, B20, B21, B22, B23, B24, B25, B26, B27, B28, B30. Not built: B1 (wetland biome), B29 (guided playthrough); B5 stays in LATER.md.

**B11/B15/B17/Z6 (2026-09-21, repair):** an account-wide session-limit cutoff interrupted the agent originally building these, leaving `game.py` with a call to `current_legacy_multiplier()` that was never defined (`NameError` on every single test) and, separately, `_ideal_accrual_for_ticks()`/`counterfactual_message()` left over from before B17/B15 existed, so B20's session-end counterfactual no longer matched real accrual once season/legacy multipliers were added to it. Diagnosed from the traceback, then completed properly (implementing B15 for real rather than deleting the dangling call, since its hook point and the TODO spec were both already in place) and reconciled the counterfactual math to match. Full details below.
- **B11 (reforestation partner):** `Plot.replant(partner=True)` halves `RECOVERY_TICKS` in exchange for a permanent `PARTNER_SHARE_RATIO` (35%) cut of that planting's future *economic* value only (never biodiversity), voided the moment the plot is next cleared.
- **B17 (seasonal growth cycle):** a 4-season, 160-tick cycle (`SEASON_CYCLE_TICKS=40` per season) multiplies economic accrual only (`SEASON_GROWTH_MULTIPLIER`, spring fastest at 1.10x, winter slowest at 0.85x) — biodiversity accrual is untouched so Pass 3's wildlife pacing doesn't shift.
- **B15 (legacy forest):** a fresh session opens with a small permanent growth bonus (`current_legacy_multiplier()`, capped at +25%) derived from the *previous* session's ending standing value, banked to `localStorage` the moment `reset_session()` wipes state for a new one — same per-browser pattern as the personal-best stat. Because this makes `_ideal_accrual_for_ticks()`'s season/legacy multipliers vary tick-by-tick instead of being a single constant, its old closed-form arithmetic-sum was replaced with an explicit per-tick loop (correctness over micro-optimization; it only runs on demand when the session-summary panel opens).
- **Z6 (site-wide goal):** the "new personal best" badge-flash pattern (a brief `.just-improved` pulse on the personal-best label) was pulled out of Canopy/Tide/Thaw's near-identical per-game CSS into one shared `shared/personal-best.css`, opt-in via `<link>` like `shared/info-page.css`. Canopy's own flash now fires at most once per session per axis (standing value / income) rather than re-firing on every tick after the stored best is first beaten — both axes climb continuously during ordinary accrual, so without a one-shot guard the flash would spam instead of marking one felt moment (`_personal_best_flashed`, reset in `reset_session()`).

Tests: still 350 (the existing B11/B15/B17/Z6 coverage from the prior pass, plus one test corrected — see below); full suite green.

Where it lives (no new always-visible blocks, per the decluttering pass):
- **Session Summary panel** gained collapsible `<details>`: Forest report card (B13, three separately labelled sparklines of biodiversity / standing value / relations, ephemeral `_report_history`), Forest history (B3), Wildlife log (B23, six deterministic species by plot index), Community forest (B19, opt-in button, fetches `/stats/games/canopy` + `/percentile` only on click, falls back to a plain "not available yet" message; the endpoint is not deployed yet). Plus the playstyle badge (B9: Preservationist/Balanced/Harvester from total clears per plot) and a "Copy badge" button (B18).
- **State** (all safe-defaulting in `load_state()`): `forest_log` (capped 200, `{tick, kind, plot, text}`), `forest_tick`, `adopted_plot_index`, `current_difficulty`, and per-plot `mature_celebrated`, `requests_survived`, `specialization` (via new `_plot_to_dict`/`_apply_plot_dict`, shared by main and Highland grids).
- **Plots:** first full maturity fires a one-shot leaf burst (B4); 3+ declined clear-requests without ever clearing marks a veteran plot (B22); an adopted plot (B27, action-panel button, mini-history filtered from `forest_log`); specialists (B21: after 90 ticks intact, one permanent economic +25% value or biodiversity x2.5 choice, lost on clear).
- **Requests:** incentive tooltips + badge relabel (B8); `N` key selects the requested plot (B16); every second incentive slot becomes a replanting grant on a bare plot when one exists (B25, `replant_grant` kind, target validity is kind-aware).
- **Difficulty / size:** Small 4x4 preset (B14); "Forest ranger" doubles soil degradation per clear (B7), changing it resets the session like grid size.
- **Small UI:** Highland unlock `<progress>` (B6), biodiversity `(+X/tick)` (B10), soil `?` hint with dynamic `title` (B12), value-pop size classes (B20, size/motion only), two-step Reset Session that names the standing value given up and skips confirmation when nothing is at stake (B24, disarms after 5s), counterfactual line states the percentage difference (B28), last-hovered plot glow (B26, plain JS + childList observer), decorative seasonal backdrop tint from the real calendar month (B30, `settings.js`).

Tests 279 -> 350 (new files: `test_display_batch_1.py`, `test_forest_log_and_badge.py`, `test_ranger_mode.py`, `test_replant_grant.py`, `test_specialist_plot.py`). The test harness `GameEnv.reset_session()` now clicks a second time when B24's confirm step arms. Verified live under Pyodide (fresh tab, service worker unregistered, caches cleared): leaf burst, adopted star, hover glow, pop sizes, badge, report-card SVGs, log panels, ranger select, specialist row and the community fallback all worked; the only console error was the expected 404 from the undeployed stats endpoint.

## Working conventions

- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag canopy-milestone-0N`.
- Update the milestone table Status as work happens.
