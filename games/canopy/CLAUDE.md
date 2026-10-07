# Canopy — Deforestation & Carbon Sinks Game

**Built following the shared conventions in `planning/archive/climate-quartet-plan.md`** (testing, feedback hook, hope-angle requirement, hub integration — moved there 2026-09-22 once all four quartet games shipped; was `climate-quartet-plan.md` at the games root while build order still mattered). This file is Canopy-specific only. This was the first of the four built, establishing the pattern the others followed.

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
| 8 | Desktop boot (PC version plan): `pc.html` generated from `index.html`, plot grid as the stage, side column for plot actions and requests, readout chips, windows for every panel | Done (2026-10-06) — see "Desktop boot" below |

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


## Reset-to-default settings button (Z-extra/A26, site-wide goal)

A "Reset to Default" button (`#settings-reset-button`) sits at the bottom of the settings panel, below the existing text-size and reduce-motion controls -- SOL's own A26 answer flagged this as a site-wide pattern rather than a SOL-only feature, folded into `planning/TODO.md`'s Z-extra checklist. Implemented entirely in `settings.js` (no Python touched, matching this file's own "deliberately independent of Pyodide" rule for the rest of the settings panel): one click calls `applyScale(DEFAULT_SCALE)` and `applyMotion(false)`, updates `--text-scale`/`data-text-scale`/`data-reduced-motion` on the live DOM immediately, resets the reduce-motion checkbox's own `checked` state to match, and writes both defaults back to `localStorage` so the reset survives a reload rather than only looking reset until the next render. No confirmation dialog -- this is a low-stakes, instantly-reversible display preference, not a destructive action, so `shared/confirm-dialog.js` is deliberately not wired up here.

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

## Highland Grove distinct rates (V-CD-5, 2026-09-21)

The completion-verification audit found the original B3 idea specified
Highland Grove should have genuinely different degradation/compounding
rates than the main forest — what shipped was a same-rules bonus copy
(the same `Plot` class, same constants, just a second grid). The user's
answer: "add distinct."

Highland Grove is already framed everywhere it appears (its lock banner,
mountain iconography, "a smaller, higher grove") as a high-altitude
ecosystem, so the distinction is grounded in real alpine-ecology
tradeoffs rather than an arbitrary number: **thin alpine soil erodes
faster once disturbed** (`HIGHLAND_DEGRADE_MULTIPLIER = 1.5` — soil
degrades 50% faster per clear than the main forest) while **a harsher,
shorter high-altitude growing season means standing value compounds more
slowly** (`HIGHLAND_GROWTH_MULTIPLIER = 0.75` — 25% slower). `Plot` gained
a `region` field ("main" or "highland", structural — fixed for a plot's
whole lifetime by which list constructed it, never saved/loaded since
reconstructing `highland_plots` always passes `region="highland"` again).
Both multipliers apply only inside `productivity_multiplier()`/
`accrue_tick()` when `self.region == "highland"` — main-forest plots
(`region == "main"`, the default) are multiplied by an implicit 1.0 and
stay byte-for-byte unaffected, pinned by a dedicated regression test.

The Highland Grove blurb (`index.html`) now states both numbers in plain
language instead of implying "same mechanics, different grid."

Tests: 350 -> 356 (`tests/test_highland_distinct_rates.py`: both
multipliers are genuinely non-1.0, the main forest's degradation math is
an exact regression pin, Highland's soil degrades faster and its value
compounds slower than the main forest at matched state, the growth ratio
is pinned to the exact constant rather than just "slower than," and
`reset_session()`'s highland-plot reconstruction correctly tags every
plot `region="highland"`). flake8 clean. Verified live: cleared plots at
matched `clear_count` on both grids and confirmed Highland's productivity
multiplier reads lower (more degraded) and its per-tick accrual reads
lower (slower growth) than the main forest's, zero console errors.

## Working conventions

- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag canopy-milestone-0N`.
- Update the milestone table Status as work happens.

- 2026-09-21: mobile-dock `body` padding-bottom now `html body` so it beats ad-bar.css (V-AB-2).
## Screen-reader accessibility audit (Z15, site-wide goal, planning/TODO.md)

Static-analysis audit (grepping/reading `index.html`/`game.py`, no live screen
reader in this environment — same audit-only method the colorblind-safety
passes already established for this hub) of the achievements and settings
panels: toggle-button accessible names, panel role/heading semantics, focus
order on open/close, keyboard reachability of interactive elements, and
checkbox/label association.

**Found and fixed one real gap:** the settings panel's own title
(`Display Settings`) was marked up as a plain `<p class="settings-panel-heading">`
rather than a heading element, so a screen-reader user navigating by heading
(the "jump between headings" navigation mode most screen readers offer) would
never see it — it read as an anonymous paragraph. Changed to
`<h2 class="settings-panel-heading">` (CSS is a pure class selector, so the
visual appearance is unaffected — it now matches the `<h2>` several other
games in this hub already use for the identical heading). No `game.py`
change needed; no test referenced the tag.

Everything else audited clean, matching this hub's site-wide pattern:
- Both toggle buttons (`#achievements-toggle-button`, `#settings-toggle-button`)
  already carry descriptive visible text ("🏆 Achievements (N/M)" / "⚙️ Settings"),
  which is a sufficient accessible name on its own — no `aria-label` needed.
- The achievements panel itself has no heading of its own, but is adequately
  labeled by the toggle button's own visible text immediately above it — the
  same "plain semantic markup is enough" call this hub's colorblind-safety
  audits already made for comparable cases; not over-engineered with ARIA
  that plain HTML already covers.
- No focus-trap exists anywhere in this hub, and none was warranted here:
  clicking the toggle button never moves focus itself, so it naturally stays
  on that same button when the panel opens or closes (no case of focus being
  silently dropped to `document.body`).
- Every interactive element inside both panels is a real `<button>`/`<input>`
  (confirmed via a site-wide grep for `.onclick =` assignments and
  `createElement("div")` calls with a wired click handler — none found; the
  achievements panel's own cards are static informational `<div>`s with no
  click behavior, so they don't need to be buttons).
- The reduced-motion checkbox is properly associated with its label
  (`<label class="settings-checkbox-label" for="reduced-motion-checkbox">`
  wrapping the input).

Verified: full pytest suite green (pure HTML tag-name change, no Python
touched), `flake8` unaffected (no `.py` file in the diff).

## Print-friendly summary (Z21, site-wide goal)

`planning/TODO.md`'s Z21: a shared `media="print"` stylesheet
(`shared/print-summary.css`) so printing the page while a game's
end-of-session summary is open produces a clean paper page instead of the
site's dark space theme (which prints as blank/near-blank on most
printers) plus a pointless copy of the nav/ad bar/toolbar/starfield. The
shared file works off one convention: whatever element the game's own
summary lives in gets a `print-summary` class, and the stylesheet hides
everything else on the page (`body * { visibility: hidden }`, then
un-hides `.print-summary` and its descendants), strips
gradients/glow/`backdrop-filter` in favor of plain dark-on-white, hides
any buttons/inputs inside the summary itself (they do nothing on paper),
forces open any collapsed `<details>` so nothing is silently dropped, and
adds `page-break-inside: avoid` on the summary's own direct-child blocks.

**Applied here:** `index.html` gained
`<link rel="stylesheet" href="../../shared/print-summary.css" media="print">`
right after the existing `ad-bar.css` link, and `#session-summary-panel`
(this game's "Session Summary" panel — counterfactual line, sparkline,
playstyle badge, the collapsible Forest report card/Forest history/
Wildlife log/Community forest sections, and the share/playstyle-comparison
controls) gained the `print-summary` class alongside its existing
`section session-summary-panel` classes. Purely additive — `media="print"`
means these rules never apply on-screen, and no `game.py`/on-screen markup
changed.

**Verification method used:** this sandbox has no print-to-PDF affordance,
so per this task's own guidance, verification was done by confirming the
new stylesheet actually loads with `media="print"` and that its selectors
have real targets in the live DOM (via `document.querySelectorAll(...)` in
the browser), rather than a literal print render. Live-verified via
`hub-dev-server`: the `<link>` tag resolves with `media: "print"`; opening
Session Summary shows `.print-summary` matches `#session-summary-panel`
with its expected classes and `hidden=false`; the panel contains 5 real
`<button>`s (Copy badge, Compare with other players, Copy, Save as Run A/
B — all targeted by the shared file's `.print-summary button` hide rule)
and 3 closed `<details>` (targeted by the forced-open rule); the page's
`.ad-bar`/`.game-toolbar`/`.ambient-bg`/`.hub-back-link` and 13 `.section`
panels (12 of which are *not* `.print-summary`) all exist as real elements
the "hide everything else" rule has to act on. On-screen appearance
before/after was visually identical (screenshot-compared) and zero new
console errors were introduced. `python3 -m pytest games/canopy/tests -q`
stayed at 356/356 (pure HTML class/link addition, no Python touched).

## 320px mobile-viewport audit (Z18, site-wide goal, planning/TODO.md)

Checked at a genuine 320px viewport (narrower than the original 375px
mobile pass) via the Claude Browser tool's `resize_window`: tutorial,
Achievements, Settings panels, plus a full-DOM `scrollWidth`/`clientWidth`
sweep. Audited, no change needed.

The one thing the sweep flagged (`#mobile-hud-bar`, showing "Harvested
income"/"Standing forest value" at the very top) is a deliberate
`overflow-x: auto` strip, not a bug — content past the first stat is
reachable by swiping sideways, the same "let it scroll instead of clip"
idiom this hub already uses elsewhere, not a page-level overflow (the
element is `aria-hidden="true"`, a decorative duplicate of stats shown
accessibly elsewhere). `document.documentElement.scrollWidth` never
exceeded 320 in any state checked. `games/canopy/style.css`'s
`.grid-size-label select` (the same inline label+select pattern that
turned out to be genuinely broken in Tide — see that game's own Z18
section) was checked too: Canopy's option text is short enough
("Small (4×4)"/"Normal (6×6)"/"Large (9×8)") that it never approaches the
320px edge, so it was left alone.

## Difficulty-aware achievements audit (Z27, site-wide goal)

Canopy's one real difficulty toggle is B7's "Forest Ranger" mode
(`DIFFICULTY_RANGER`) — each clear degrades a plot's soil twice as steeply
as normal (`DEGRADE_PER_CLEAR_BY_DIFFICULTY`). Changing it resets the
session (soil quality is derived from `clear_count`, so it can't be
flipped mid-run the way SOL's/Grid's own toggles can), so unlike most of
this hub's difficulty toggles it IS a session-long, locked-in choice.

Checked it against every achievement that touches clearing or standing
value. The key fact that keeps it safe: `MIN_PRODUCTIVITY_MULTIPLIER`
(0.2) is a hard floor — no matter how many times a plot is cleared, or how
steep the degrade-per-clear rate is, a plot's productivity can never reach
zero, only approach 20% of its fresh value. That means clearing itself is
never blocked (`soil_scarred`, `resourceful_extractor` — pure clear
counts — are completely unaffected by the degrade rate) and standing-value
growth on a recovered/preserved plot never actually stops, only slows
(`standing_fortune`, `flourishing_canopy`, `balanced_ledger` — all still
reachable, just requiring more patience under Ranger mode). `true_
conservationist` (reach 300 standing value "without ever clearing") is
untouched by construction, since the degrade rate only ever applies to a
plot that HAS been cleared. B13's grid-size presets (small/normal/large)
were also checked as a second "difficulty/length variant" candidate — they
only change plot COUNT, and no achievement requires anywhere near the
16-plot floor of the small preset (`old_growth_grove` needs 5 mature plots
at once, `every_stage_at_once` needs one of each of 4 states), so no
achievement becomes harder to reach on the smallest grid either.

**No change needed.** Ranger mode changes pacing, never reachability —
the floor multiplier is exactly what stops "twice as steep" from ever
compounding into "impossible." No code touched; `flake8`/tests unaffected.

## Achievement-progress bar in toolbar (Z-extra/A10, site-wide goal)

Already satisfied — see the existing toggle-button label. `#achievements-
toggle-button`'s `innerText` already reads `"🏆 Achievements (N/M)"` via
`update_achievements_display()`, called from the main render loop, so the
live earned/total count is visible in the toolbar before the panel is
ever opened. No code change needed here.

## "What's new since you played" banner (Z24, site-wide goal)

A new shared `shared/whats-new-banner.js` -- deliberately distinct from
this game's own in-game "What's New" changelog PANEL above (opt-in,
player-triggered, always shows the full history from scratch). The
banner instead appears automatically on page load, but ONLY for a
RETURNING player who has missed real entries since their last visit: it
diffs this game's `changelog.json` against
`localStorage["whats-new-seen:canopy"]` (the date string of the newest
entry already shown) and lists just the new ones, not the whole log. A
first-ever visit silently marks the current changelog as seen rather
than dumping the full history on a brand-new player. Reuses the same
`window.CHANGELOG_JSON` global this game's own changelog panel already
fetches -- no second network request. One `<script
src="../../shared/whats-new-banner.js" data-game-id="canopy">` include,
added right after `shared/last-played.js`'s own include. See root
`CLAUDE.md`'s Working notes for the full write-up -- shared
infrastructure, documented once there rather than duplicated across all
12 games' own files.

## Keyboard-shortcut convention: ?/Esc (Z4, site-wide goal)

Wired via the new shared `shared/keyboard-shortcuts.js` -- one script
include plus one `KeyboardShortcuts.init({panels: [...], extra: [...]})`
call at the end of `index.html`, listing this game's real toggle-button +
hidden-panel pairs: How to Play, Settings, Achievements, What's New,
Session Summary, and the Info Page. `?` opens a small floating
shortcuts-help overlay (also listing B16's existing `N` shortcut, which
this game's own separate `keydown` listener still handles); `Esc` closes
the overlay and clicks the toggle button of whichever listed panel is
currently open, reusing each panel's own open/close logic. The
stakeholder-request panel and the adopted-plot readout aren't in the list
-- both are shown/hidden by game state, not a player-clicked toggle
button, so there's no toggle to reuse for a generic Esc close.

## Guided example playthrough (B29, 2026-09-26)

A "Example playthrough" toolbar button opens a narrated five-step panel showing a strong preserve/clear balance: patience compounds, clearing costs downtime and soil, clearing early backfires, the balanced run (keep 8 of 10 plots standing, harvest 2 at maturity, replant), and what to copy. It is "AI-narrated" in the sense of a worked example, not a replayed session: every number comes from `example_playthrough()`, which computes it from the game's own constants (`BASE_ACCRUAL`, `GROWTH_PER_TICK`, `DEGRADE_PER_CLEAR`, `MIN_PRODUCTIVITY_MULTIPLIER`, `RECOVERY_TICKS`, `MATURITY_TICKS`) using base rules only (no seasons, legacy, grants or specializations), so it stays correct if a constant is retuned and never reads or changes live state. At current settings, over 10 plots and 120 ticks: never clearing about 4830, clearing every 10 ticks about 574, and the balanced run about 4372. Built as a static hidden-until-opened panel (same idiom as What's New) and registered with the shared `?`/Esc shortcuts. 356 -> 365 tests (`tests/test_example_playthrough.py`); verified live, zero console errors.

## Wetland Forest (B1, 2026-09-26)
A third region after Highland Grove. `WETLAND_UNLOCK_STANDING_VALUE_THRESHOLD` = 5000 (sticky, one-way; its lock banner only appears once Highland is open so the early game never shows two). Same `Plot` class with `region="wetland"` (`WETLAND_GROWTH_MULTIPLIER` 1.25, main-forest soil rate) and its own grid, income, selection, Clear/Replant buttons. Tension: a flood every `WETLAND_FLOOD_INTERVAL_TICKS` (50); `apply_wetland_flood()` strips `WETLAND_FLOOD_LOSS_YOUNG` (30%) of a standing plot's value, or `WETLAND_FLOOD_LOSS_MATURE` (10%) once it has stood `MATURITY_TICKS`; replanting plots gain `WETLAND_FLOOD_SILT_TICKS` of extra wait (capped); bare plots are untouched. For the last `WETLAND_FLOOD_WARNING_TICKS` (10) the status line turns into a warning and young plots get a dashed outline, so harvesting early is a real choice. Save: `_wetland_state_fields()` writes `wetland_*` keys only once unlocked; `load_state()` validates them (bool/NaN/out-of-range/wrong-type all fall back) and resets the live wetland when a save lacks them. Floods log `flood` events to the forest history. Tests: `tests/test_wetland_forest.py` (16).


## Story mode (W1, 2026-09-26)

A light narrative thread, "Wren Hollow", built on the shared `shared/story-chapters.js` (Grid was the reference integration; that file is not edited per game). `story.json` holds an opening chapter `begin` plus exactly one chapter per achievement id in `achievements.json`, in story order from early to late game, about plots, seasons and village stakeholders. `_story_reach_all(earned_ids)` in `game.py` calls `window.NoyvjStory.reach()` for `begin` and every earned id, from the achievement check (`_sync_earned_and_toast`) and from the load/baseline path, so a loaded save brings its chapters back. It is idempotent and silent when the script is missing. Progress lives in `localStorage["story-chapters:canopy"]`, never in the save. `#story-chapters` is appended to the existing `story-toggle.js` selectors, so the Story on/off pill hides it. Tests: `tests/test_story_chapters.py` (7).

## In the real world (W2-canopy, 2026-09-27)

A collapsible "In the real world" `<details id="real-world-note">` (above the action panel) shows one sourced real example, chosen deterministically by `real_world_topic()` (no RNG) and rendered by `render_real_world()`. It changes no game number and adds no save state. Priority: a pending community request (clear request -> `community`; incentive or replant-fund offer -> `funded_restoration`), else the newest mapped forest-log event (`REAL_WORLD_LOG_TOPICS`: clear -> `forest_loss`, replant -> `restoration`, wildlife/preserve/recovered -> `wildlife`, mature -> `carbon`), else rotation by `forest_tick // REAL_WORLD_ROTATE_TICKS`. Every fact below was read with a live fetch on 2026-09-27 (nothing recalled from memory); the source line reads "Source: <name> (read 2026-09-27)" and links with `target=_blank rel="noopener noreferrer"`. Tests: `tests/test_real_world.py`.

| Topic | Mechanic | Source and URL |
|-------|----------|----------------|
| `forest_loss` | clearing a plot | Wikipedia, Deforestation (FAO: 10 million ha/yr 2015-2020, 17.6 million ha/yr 1990-2000) - https://en.wikipedia.org/wiki/Deforestation |
| `restoration` | replanting | Wikipedia, Atlantic Forest (Pact for Atlantic Forest Restoration: 100+ organisations, 15 million ha by 2050) - https://en.wikipedia.org/wiki/Atlantic_Forest |
| `wildlife` | biodiversity / preserved plots | Wikipedia, Secondary forest (species richness recovers quickly, abundances and identities slower; tropical biodiversity slower than carbon) - https://en.wikipedia.org/wiki/Secondary_forest |
| `carbon` | mature plots | Wikipedia, Carbon sink (forests ~25% of human emissions annually; a third less carbon taken up in 2019 than 1990s) - https://en.wikipedia.org/wiki/Carbon_sink |
| `community` | stakeholder clear request | Wikipedia, Community forestry in Nepal (19,000+ user groups, a quarter of national forests, 1.6 million households; equity caveat) - https://en.wikipedia.org/wiki/Community_forestry_in_Nepal |
| `funded_restoration` | incentive / replant-fund offer | Wikipedia, Great Green Wall (Africa) (adopted 2007, 100 million ha goal by 2030, ~30 million ha as of 2024, figures vary by report) - https://en.wikipedia.org/wiki/Great_Green_Wall_(Africa) |

## Light theme (Y11b, 2026-09-27)

`shared/theme-light-games.css` restyles the shared chrome; Canopy's own light rules are one block at the end of `style.css` (banner "Light theme (Y11b"), every selector under `html[data-theme="light"]` so the default dark theme is untouched (no dark rule was edited). The theme control is now a "Theme" row in the Settings panel (`<button id="theme-toggle" class="secondary">`, labelled and wired by `shared/theme.js`); the floating pill is retired here (`data-floating-toggle` removed from the `theme.js` include).

Method: a computed-style contrast scan in a live light-theme page (walk visible text nodes, composite ancestor backgrounds/gradients, WCAG 4.5 normal / 3 large, skipping disabled controls and emoji-only tile glyphs), run over: fresh game; a built-up game (young/mature preserved, bare, replanting, recovered, fully mature, veteran, wildlife, selected); Highland Grove and Wetland Forest unlocked with mixed tiles; a pending stakeholder request; real-world note open; a selected feedback button; the tooltip and toast; and each panel (How to Play, Achievements, What's New, Example, Session Summary, Settings, Info Page).

Before: flagged the "Plot ... selected" readout and the other recessed dark readouts (2.9:1), the (i) info toggle (1.2:1), the back link (3.3:1), the selected feedback chip (1.3:1, dark text on dark green), the floating "+X" pop (2.1-2.6:1), How-to step numbers (3.2:1, injected by `shared/tutorial.js`), achievement progress and changelog dates (3.7-4.3:1), plus non-text problems the text scan cannot see: plot tile edges, the pale selection/focus-hover/flood/mature rings and the pale LED, and session graph lines (2-2.5:1). After: the only remaining text flag is the shared ad-bar label (`ad-bar.css`, 3.06:1; not Canopy's file).

Deliberately not recoloured: plot fill colours (`game.py`'s inline gradient carries the state, with the B9 pattern and icon per state); the plot tooltip, stakeholder badge and achievement toast (self-contained dark chips with light text, already high contrast); the amber/teal etc. section accent bars (decorative); the adopted-plot dashed outline (a star mark carries it). Known limits: the light-green mid-growth fills are only about 2:1 against the panel, so the tile edge was darkened to reach 3:1; the "+X" pop is legible through a white glow rather than a measured pair.

Tests: `tests/test_light_theme.py` (7): light block exists, every rule scoped to light, each flagged area has a rule, state fills not re-painted, dark tile rules intact, floating pill retired, Settings hosts exactly one theme control. 395 -> 402 tests.

## Gamified batch 1 (GB-2, 4, 8, 14, 18, 20, 22, 23, 27, 28, 30, 2026-09-27)

Eleven ideas from `planning/IMPROVEMENT-IDEAS-ROUND-3.md` section GB, all in `game.py` (constants and state above `reset_session()`, behaviour in one "GB batch 1" section above `render()`), `index.html`, `style.css` (one block before the light-theme banner, light rules appended at the end) and `tests/test_gb_*.py`. Rules followed: no RNG (`_gb_hash(forest_tick, salt)` picks "random" things, so runs and tests repeat); everything timed rides the 1 s tick; every new save key is written only when non-default and validated in `_load_gb_state()` (bool-as-int, NaN, wrong types, unhashable list members); a save is authoritative, so a live session's names or discoveries never leak into a save that lacks them.

- **Season indicator (new, needed by GB-23/30).** The ideas doc assumed one existed; it did not (B17's season was invisible). `<p id="season-indicator">` above the grid shows season and ticks to the next, the weather, and the Perfect Season flame.
- **GB-2 golden seedling.** A bare or replanting plot gets a seedling every 20-44 ticks (hash picked); it stays 4 ticks. Click its tile (or press G) to bank 4 ticks of recovery (a bare plot is replanted first and counts as a replant); reuses the B4 leaf burst. Never saved. Marked by an outline plus a sparkle, so it does not rely on motion or hue.
- **GB-4 Tend (T).** `tend_plot(index)`: 5 ticks of x1.5 economic growth on one plot (a replanting plot recovers an extra tick per tick), then a 20-tick cooldown; one boost at a time. T uses the last hovered/focused plot, else the selected one; a Tend button and status line do the same. Saved as top-level `tend` / `tend_cooldown_ticks`.
- **GB-8 Heart Tree.** A standing interior plot with 7 or more of its 8 neighbours fully mature wakes the Heart Tree (`heart_tree_index`, saved). No legend, hint or tooltip text; it logs a `discovery` entry (shown in the Wildlife log) and toasts. It cannot be cleared, requests never target it, and the 8 plots around it grow 10% faster. The interpretation "7 of 8 neighbours" is mine (the idea says a ring of seven).
- **GB-14 names.** Forest name (24 chars) and adopted-plot nickname (20 chars) in a "Name your forest" details block; cleaned of control characters and extra spaces. The log narrates the nickname ("Old Bramble survived a third clearing request"), the forest name heads the Forest history, share snippet, tier readout and Almanac. The nickname belongs to one adoption and is dropped on release.
- **GB-18 undo.** After a manual Clear on the main forest an "Undo clear" chip lasts 3 full ticks (3-4 s), restoring the plot, income, log entry, income record and Perfect Season flag. Off in Forest ranger; granted requests and Highland/Wetland clears are not undoable. Replanting the plot invalidates it. Never saved.
- **GB-20 rare wildlife.** `rare_wildlife_found` (saved). Ghost stag: a plot at 90% or more of `BIODIVERSITY_FULL_SCORE` (2.0) during the last 10 ticks of autumn, which also night-tints the grid (`plot-grid--dusk`) and draws the stag on that plot. Wary fox: 3 declined clear requests in total. Both go to the Wildlife log with a "Rare sightings" line.
- **GB-22 tiers.** 1k Seedling, 2.5k Grove, 5k Woodland, 10k Old-Growth from the best standing value reached (`peak_standing_value`, `milestone_tier`, saved), so clearing never un-earns a title. Toast, log line, `.forest-pulse` light pulse on the backdrop and the shared `.just-improved` flash on the title. Achievements: 1k already was `standing_fortune`; new `tier_grove`, `tier_woodland`, `tier_old_growth_steward` (24 total; three chapters added to `story.json`). Older saves get their tier silently.
- **GB-23 weather.** `weather_at(tick)` is a pure function of the tick (no state): after tick 24, rain in spring/autumn (x1.15) and drought in summer (x0.85), 8 ticks each, none in winter. Applies to every region's accrual and is included in the counterfactual (`_ideal_accrual_for_ticks`). Rain shimmers over the grid, drought sepia-tints the tiles; text on the season indicator.
- **GB-27 chain bloom.** 3 or more plots maturing within 3 ticks ripple their leaf bursts in order with growing size and delay (`plot-chain-bloom-0..7`, pure CSS delay). Juice only.
- **GB-28 Forest Almanac.** Toolbar button and panel: trees planted (4), wildlife seen (6), rare wildlife (2), hidden structures (1), seasons survived. Unfound wildlife/trees are silhouettes with "???", rare wildlife shows "???", the hidden structure shows nothing before it is found. "Species planted" maps to the four tree kinds derived from play, since species-on-replant (GB-6) belongs to another batch; add entries to `ALMANAC_TREES` when it lands.
- **GB-30 Perfect Season.** At each season boundary a season is perfect if no main-forest plot was cleared (manual or granted; an undone clear does not count) and community relations never fell below 30 (my reading of "declined-and-regretted": refusals that cost you the village's trust). Each flame gives +2% growth, capped at +10%; shown as a flame counter with the rule in its title; toasts at 1, 3 and 5.

Toasts: GB toasts queue and share the achievement toast, so a discovery in the same tick as an achievement no longer hides it. Reduced motion: every new animation has a `prefers-reduced-motion` rule and the manual switch already collapses them. Light theme: rules for the season indicator, seedling, Heart Tree, dusk, undo chip, name fields and Almanac. Hotkeys T/G/U are listed in the `?` overlay and ignored while typing.

Tests 402 -> 557 (new `tests/test_gb_*.py` files, helper `tests/gb_helpers.py`, new ids in `tests/conftest.py`). Verified live in a real browser under Pyodide: catching a seedling by clicking its tile, T hotkey on a hovered plot, U undo, no undo chip in Ranger, Heart Tree discovery with toast and log, chain bloom classes and computed CSS (delay and size grow by rank), rain and drought classes and computed filters, ghost stag at dusk, Almanac, Perfect Season toast and streak, save/load round trip, reduced-motion and light theme computed styles, and no console errors. Screenshots were not possible (the pane reported the page as hidden), so the visual look was checked through computed styles only.

## Desktop boot (PC version plan, 2026-10-06)

`games/canopy/pc.html` is the Desktop boot: the same `game.py`, saves and `game_id` as the Classic page, in a full-window layout for wide windows with a mouse. Never edit it by hand: it is generated from `index.html` plus `pc-config.json` by `scripts/generate-pc-pages.py` (a test fails if it is stale). No game rule, state or save format changed, and `game.py` is untouched. The only Classic edits are the `layout-pref.js` script tag and `GameTutorial.init(window.CANOPY_PC_TUTORIAL_STEPS || CANOPY_TUTORIAL_STEPS, ...)`.

- **Layout.** Top bar: back link, title, four icon buttons (Achievements, Almanac, Session Summary, Settings) and the Menu (also opened by Esc). Under it, readout chips for harvested income, standing value, biodiversity and community relations (mirrors of the original `*-display` lines, which move into a hidden holder and keep updating). The stage is `#plot-grid`, kept square and scaled to the window for all three grid sizes (`pc.css` reads the preset from `data-cols`: Small 4x4, Normal 6x6, Large 8 columns x 9 rows), with the season indicator above it, the legend below it and a hotkey bar (arrows, T, G, U, N, ?, Esc). The side column holds only the action panel (Clear, Replant, Adopt, Tend, Undo, specialist choices) and the community request panel, compacted so it never scrolls at 1024x700 even with a request, an undo chip, a specialist choice and an adopted plot all showing (UX-5).
- **Windows.** How to Play, Achievements, What's New, Example playthrough, Almanac, Session Summary, Settings and The Real Story are windows. Composite windows opened from the Menu: Forest summary (the stats card), Name your forest (opens unfolded), Grid size and difficulty (the two selects), Highland Grove and Wetland Forest (lock banners, progress bars and both extra grids), About this forest (tagline, context blurb, the real-world note, the decorative forest strip and the Story list, filed there by `pc.js` once `shared/story-chapters.js` creates it) and Your feedback (the Did-this-change-your-thinking prompt). Reset Session, the tutorial, How to Play, Example playthrough, The Real Story and What's New are Menu buttons.
- **Tutorial.** `pc.js` holds `CANOPY_PC_TUTORIAL_STEPS` (eight steps pointing at the grid, action panel, legend, readout chips, side column and Menu).
- **Notifications.** `notify` is null: Canopy's only log list (`#forest-history-list`) lives inside the Session Summary and is only rendered when that window is open; the existing achievement and discovery toasts already announce events.
- **Known limits.** Highland and Wetland unlocks are announced by the achievement toast, not by a banner, since those regions live in a window. The stakeholder request panel is in the side column, so the floating "pending request" badge only shows if that column is scrolled past it (it no longer scrolls at 1024x700 or larger).

## User-reported fixes UX-1, UX-3, UX-4, UX-5 (2026-10-07)

- **UX-1, phone Classic page covered by pinned pieces.** Measured at 360x740 the sticky HUD (32px), the docked action panel (231px: state line, four icon-over-label tiles that wrapped, hint text, "Name your forest"), the Stats & Legend toggle (hidden *underneath* the taller dock, so it could not be tapped), the Story pill, the Save pill and the ad bar (50px) covered about 40% of the viewport. Now `style.css`'s `@media (max-width: 640px)` block makes the dock one state line plus one non-wrapping row of compact buttons (about 89px, 98px with the Undo chip), folds the tend hint, soil hint, adopted-plot line and "Name your forest" behind a new phone-only `#action-dock-more` ("...") button, and an inline script in `index.html` publishes the dock's real height as `--action-dock-h` so the Stats pill, the Story pill and the bottom padding follow it instead of being hard-coded. The Stats pill is a small right-aligned pill, the Story pill sits in the left corner above the dock, and the collapsed Save pill is tucked inside the ad bar. Result: about 25% pinned at 360x740 (23% at 390x844), all 36 plot tiles tappable (checked with `elementFromPoint`), Clear/Replant/Adopt/Tend/Undo reachable. Left alone because they are shared files: the Save widget pill still sits over the right third of the ad slot (`shared/save-widget.js` bottom: 12px), the Story pill's default position (`shared/story-toggle.js`) is overridden here by an id selector in `style.css`, and `shared/pc-shell.js`'s Esc blocker list uses `.confirm-dialog-overlay` (a class) while the dialog is `#confirm-dialog-overlay` (an id), so on its own Esc would open the Menu behind a confirm dialog; Canopy handles Esc itself (see UX-4).
- **UX-3, arrow keys.** Root cause: the handler listened on `#plot-grid` and required the focused element to be a plot tile, but `render_grid()` rebuilds every tile every second and on every click, which drops focus to `<body>`; so after clicking a plot (or one tick after tabbing to one) the arrows did nothing, on both boots. Now the listener is on the document and starts from the focused tile, else the plot the keyboard/pointer last touched, else the selected plot (Desktop boot only: plot 0 when nothing is in play, since that page never scrolls; on the Classic page with no plot in play the arrows keep scrolling), and a `childList` MutationObserver restores focus to the same tile after each rebuild. Ignored in form fields, with modifiers, and while the opening screen, confirm dialog, tutorial or shortcuts panel is up. Arrows move focus (the visible ring); Enter or Space selects, as before. The `?` overlay lists the arrows. No shared file interfered (`shared/keyboard-shortcuts.js` only handles `?` and Esc; `shared/tutorial.js` only reacts while its overlay is open).
- **UX-4, Reset Session "does nothing".** The two-press confirm (press, then press again within 5 s) only relabelled the toolbar button, so a single press looked like nothing happened (on a phone the toolbar is scrolled away; on the Desktop boot the button is in the Menu, which closes after the first press, so the second press never came). It could not be reproduced as a hard failure in a plain session: two presses did reset. With saved games the account autoload in `shared/save-widget.js` (it fetches `/users/me/saves` and calls `load_state()` once the fetch returns) can finish after a reset made in that window and put the loaded save back, which is the one other way a reset can look like nothing; that is shared code and was not changed. Fix: Reset Session now asks through the shared `ConfirmDialog` ("Reset this session? You will give up X standing value and Y income. Saves you have already made are not touched." with Cancel / Reset session; Esc cancels), the same on both boots; with nothing at stake it still resets at once, and without `ConfirmDialog` (the pytest harness) it resets at once. `_reset_confirm_armed`, `RESET_CONFIRM_WINDOW_MS` and the relabelling are gone. Tests: `tests/test_display_batch_1.py` (B24 block rewritten, includes a load-state-then-reset case) and the harness fixture `fake_confirm_dialog` in `tests/conftest.py`.
- **UX-5, Desktop side column scrolling.** The column held the action panel, the request, the forest stats card and the decorative strip. Now it holds the action panel and the request only, compacted in `pc.css` (icon-beside-label tiles in two columns, request without its decorative roofs and N hint). The forest stats card is the Menu's "Forest summary" window, the forest strip joined "About this forest", and "Name your forest" is its own Menu window (`pc.js` unfolds its `<details>`). Measured with every optional piece forced on (request, Undo chip, specialist row, adopted-plot line, tend hint): the column needs 461px against 550px available at 1024x700 and 750px at 1440x900, so it does not scroll; `pc-config.json` zones, composites and `pc.html` (regenerated) updated, every id `game.py` uses is still present.
- Tests: 557 -> 572 (`tests/test_ux_fixes_2026_10_07.py` structural guards for UX-1/3/5, plus the UX-4 behavioural tests). Verified live in a real browser (Pyodide) at 360x740, 390x844, 1024x700, 1024x768 and 1440x900, both boots; no saves or feedback were sent to the backend.

## Gamified batch 2 (GB-9, GB-17, B-6, B-7, B-8, B-10, B-12, B-16, B-26, 2026-10-07)

All in `game.py` (constants above `reset_session()`, behaviour in one "GB batch 2" section above the per-tick hook), `index.html`/`pc.html` (regenerated), `settings.js`, `style.css`, `pc.css`, `pc-config.json`, `achievements.json`, `story.json` and `tests/test_gb2_*.py`. Same rules as batch 1: no RNG, timers ride the 1 s tick, new save keys only when non-default and validated on load.

- **GB-17 challenge runs.** Toolbar select `#challenge-select` (resets the session, like difficulty; Reset Session keeps the challenge so it retries it). Pacifist: reach 40 standing per plot with no clear (a granted request counts; an undone clear does not; failure is read off the live forest). Scorched Start: two thirds of the plots start bare (hash-picked, soil untouched, no clear counted), reach 50 per plot. Sprint: within 60 ticks hold 70 standing per plot and 28 income per plot together. No-Highland: Highland and Wetland stay sealed, reach 100 per plot. Goals scale with the grid. `#challenge-status` shows rule and progress. Finishing logs, toasts, earns an achievement (4 new, 28 total, 4 new story chapters) and records the fastest finish per browser in localStorage (`canopy_challenge_records_v1`), shown as badges in the Almanac. Saved as `challenge` {id, done_tick}.
- **GB-9 Ranger contracts.** Toolbar button and panel (`#contracts-panel`, a window on Desktop). Three open contracts out of ten kinds (replant, mature, wildlife, decline, accept, tend, seedling, standing value, calm, trust), deterministic hash pick that prefers kinds whose stamp you lack; targets scale with the grid and are set above the live value so none starts finished. Each pays 5 income per plot, adds a stamp, raises a rank (Trainee to Chief warden); a finished slot refills 6 ticks later. The board is closed during a challenge. Saved as `ranger_contracts` only once something has happened (an untouched board is rebuilt on load). New counters `tends_done`, `seedlings_caught`.
- **B-12** `#season-forecast`: next two seasons with multipliers and countdowns plus the next rain or drought (exact, scans a year ahead).
- **B-6** `#request-pace-select` (a toolbar select rather than a Settings control, because it resets the session so results stay comparable): relaxed 22, normal 15, frequent 10 ticks; saved as `request_pace`; named in the share snippet with difficulty and challenge (`session_tag_text()`).
- **B-7** `#sr-announcer` polite live region (clears, replants, requests, seasons, achievements, discoveries, contracts), C and R hotkeys act on the SELECTED plot only (deliberate two steps), thicker gold focus ring.
- **B-16** plot card second line (age, biodiversity per tick, clear count); `aria-label` equals `data-tooltip`.
- **B-8, B-10, B-26** Settings options stored per browser (`canopy-plot-contrast`, `canopy-soil-overlay`, `canopy-number-format`) and read back by Python (`ui_pref()`); letters, badges and classes exist only while on. Number formats: standard, thousands separators, compact (12.3k), two decimals.
- **Not done / deferred**: see the coordinator report (GB-11 needs W-2, GB-10 and GB-26 need W-3, GB-13/15/16 need W-1, GB-19 needs W-5, rest not started).

Tests 572 -> 736+ (`test_gb2_challenges.py`, `test_gb2_contracts.py`, `test_gb2_display.py`; two achievement-count assertions raised 24 to 28). Verified live (Pyodide) on Classic and Desktop at 1440x900 and Desktop 1024x700 (no page or side-column scroll): challenge select and completion, badge record, settings options, C/R keys, contracts panel/window, setup window with the four selects. The 360x740 Classic check was not possible (the browser pane closed), only by CSS reasoning.

## Level select, Seed Vault and ranger crews (GB-10, GB-13, GB-15, GB-16, GB-26, W-1/W-3 wiring, 2026-10-08)

Built on the new shared components (`planning/SHARED-COMPONENTS.md`): `shared/level-select.js`, `shared/skill-tree.js` + `.css` and the Python mirror `shared/skill_tree.py`. All Canopy code is in one "GB batch 3" section of `game.py` (above the per-tick hook), plus `levels.json`, `index.html`/`pc.html` (regenerated), `settings.js`, `style.css`, `pc-config.json`/`pc.js`, `changelog.json` and `tests/test_gb3_*.py`. No audio, no RNG (hash picks, as in batches 1 and 2), nothing sent to the backend.

- **Levels (`levels.json` + `LEVEL_SPECS`).** A Levels button (toolbar; in the Desktop Menu under Game) opens the shared level screen: 15 levels, every fifth a mode or mechanic. 1 Wren Hollow, 2 Fern Glade (4x4), 3 Birch Flats (9x8), 4 Ranger Trail (Forest ranger soil, income as well as standing value), **5 Poacher Patrol** (mode), 6 Quiet Valley (relaxed requests), 7 Busy Valley (frequent requests, answer 3), 8 Highland Climb, 9 Wetland Reach, **10 Storm Front** (mechanic), 11-14 the four batch-2 challenge runs (Pacifist, Scorched Start, Sprint, No-Highland, each a mode level that finishes when the challenge does), **15 The Spirit's Walk** (story level). `levels.json` carries the display data (title, kind, blurb, `requires`/`requires_count`, `unlock_text`, `better: lower`, `unit`); `LEVEL_SPECS` carries presets (grid, difficulty, pace, challenge, bare fraction) and goals, and a test pins the two together. A level is a fresh session with its presets (`start_level`), its own clock (`level_ticks`), a goal checked each tick, and a result that is "lower is better": ticks for plain levels, missed poachers for Poacher Patrol, value lost for Storm Front. Python owns the progress (`levels_state` = `{done, best}`); the screen only displays it (`setState` pushed after every change, `configure({state, onStart})` once, queued by the component until `levels.json` has loaded). A level box (`#level-box`: `#level-status`, `#spirit-line`, `#level-leave-button`) shows goal and progress; Leave level goes back to free play on the same forest. Reset Session retries the running level; changing grid size, difficulty, request pace or challenge by hand leaves it (`reset_session(level=...)`, default keeps it unless one of those is being set).
- **Saved state.** Three new keys, each written only when non-default so a fresh game's save is unchanged: `levels` (`{done, best}`), `seed_vault` (`{owned, best_tier, best_ach, crews}`) and `level_run` (the running level's id, ticks, done tick and mode state). All validated on load (unknown ids, wrong types, NaN/inf, bool-as-number, duplicates, prerequisites missing, more spent than earned, a level that does not match the loaded grid/difficulty/pace/challenge). Meta-progress (levels done, bests, vault, best tier and achievement counts) also lives per browser in `localStorage["canopy_meta_v1"]` so it survives Reset Session, and loading a save MERGES it (union of done levels, better of each best, a bigger best-tier/achievement count wins) so an older save never takes progress away; the save's owned perks replace the live ones, trimmed from the end if they cost more than is earned.
- **GB-13 Poacher Patrol.** After 8 level ticks a poacher appears on a hash-picked standing plot and stays 5 ticks (one tick less for every 3 driven off, minimum 3). Click that plot (or Enter on it) or press P to drive it off; an unanswered poacher strikes and takes a quarter of the plot's standing value (a plot you cleared meanwhile is left alone). Drive off 8 to finish. Marked with a dashed outline and an axe glyph (and an `aria-label` that says POACHER), not by motion or hue alone. Never part of the base game.
- **GB-15 Storm Front.** Starts with a quarter of the forest bare. Every 20 ticks a front sweeps two rows (the band is a pure function of the front number); for the last 8 ticks the band is dotted-outlined with a storm glyph and named in the level box ("front in 5 ticks over rows 3-4"). A standing plot loses 30% (15% if mature) when its left or right neighbour in the row is bare or still replanting, and only 5% (0% if mature) when sheltered, so replanting the gaps before the front arrives is the play. Weather four fronts to finish.
- **GB-16 The Spirit's Walk.** A forest spirit sets six tasks in order (grow a plot to 10 value, Tend, replant a bare plot, wildlife on three plots, answer a request, four mature plots at once) and narrates each: the line shows in `#spirit-line` and is logged to the Forest history (kind `spirit`, spoken once through the screen-reader announcer); the farewell ends the level. The text is original, plain text only. Tasks that were already true when their turn comes pass at once.
- **Off switch for effects.** Settings, "Level effects" (`#level-effects-checkbox`, per browser, default on, stored as `canopy-level-effects`; `html[data-level-effects="off"]`) removes only the motion of the three modes (poacher shake, storm glyph flicker, spirit glow); markers, outlines and text stay. Every such animation is also off under `prefers-reduced-motion` and the existing Reduce motion switch. Light-theme rules are in the light block at the end of `style.css`.
- **GB-10 Seed Vault + GB-26 ranger crews: one skill tree** (`VAULT_TREE` in `game.py`, three branches, 10 nodes, 23 points in all). It is validated by `skill_tree.validate`, bought/refunded through `skill_tree.buy/refund` (the Python mirror `shared/skill_tree.py` is written into Pyodide's file system by the boot script, like `info_page.py`) and drawn by `NoyvjSkillTree.render` into `#vault-tree` inside `#vault-panel` (toolbar button `#vault-toggle-button`; a window plus a toolbar icon on Desktop). Seed points are earned, never bought or random: 1 per level completed, 1 per forest tier reached (best ever), 1 per 4 achievements (best count ever, max 7), so the whole tree (23) is reachable (up to 26 points). Refunds are free and unlimited (respec), so no purchase needs a confirmation. Roots: Deep Roots +3% growth, Canopy Cover +4%, Old-Growth Memory +5% (`vault_growth_multiplier()` in `Plot.accrue_tick` and the session-summary counterfactual). Soil: Mulch Bed and Leaf Litter each cut soil lost per clear by 10% (`current_degrade_per_clear()`), Fast Sprouts replanted plots recover 2 ticks sooner. Crews (all deterministic, on the tick): Tending Crew tends your youngest plot (replanting first) once Tend has sat ready for 3 ticks, so you can tend first; Seedling Watch catches a golden seedling in its last tick; Replant Crew replants the first bare plot every 20 ticks; Crew Lead brings that to 12. Crew work is logged (kind `crew`) and counted in the panel ("Crew work this session"). **Perks and crews rest during a challenge run** (`vault_perks_active()`), so the challenge records stay comparable; the panel says so.
- **Desktop boot.** Every new id exists in both pages (`tests/test_gb3_markup.py`, and `shared/tests -k canopy`). `pc-config.json`: Levels in the Menu (Game), Seed Vault as a window with a toolbar icon, `#level-box` in the stage bar, a P hint. The Esc key: Canopy's existing window-level Escape listener now flags the event (`__pcMenuOpened`) while the level screen is open so the Desktop Menu does not open behind it; the level screen is also in the arrow-key and C/R modal lists. Mobile pinned bars, arrow-key and Reset Session behaviour are unchanged (their tests pass).
- **Files the main session must add to `sw.js`'s precache** (none were in it yet): `shared/level-select.js`, `shared/skill-tree.js`, `shared/skill-tree.css`, `shared/skill_tree.py`, `games/canopy/levels.json`.
- **Not built.** Cross-game or backend pieces (none needed), per-level star ratings, a story epilogue after the Spirit's Walk, and levels beyond 15 (the list is data: append entries to `levels.json` and `LEVEL_SPECS`).

Tests 736 -> 890 (new files `test_gb3_levels.py`, `test_gb3_modes.py`, `test_gb3_vault.py`, `test_gb3_markup.py`). Verified live (Pyodide): the level screen at 1440x900 Classic and Desktop and 360x740 (all 15 cards, locks, Play), Wren Hollow completed with the result and best shown in the screen, the Seed Vault buying a perk (live-region announcement, growth multiplier 1.03) and a crew tending on its own, Poacher Patrol (click and P both drive one off, a missed one strikes), the Storm band outline on both layouts, the Spirit line, the effects switch (`animation-name` goes to `none`), a save round trip and an old save with none of the new keys, and no console errors. Desktop Esc closes the level screen without opening the Menu.
