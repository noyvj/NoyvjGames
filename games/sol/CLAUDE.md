# SOL — Solar System Incremental Clicker

Dual-purpose university digital artefact (DA) for BCM114 + BCM206 at UOW, Spring 2026 semester (starts July 27, 13 weeks). Built almost entirely via AI-assisted development.

## Stack
- **Python via Pyodide** (runs in-browser via WebAssembly) — not JavaScript. All game logic should be written in Python in `game.py`, using the `js` module / `pyodide.ffi.create_proxy` to interact with the DOM.
- Plain HTML/CSS shell (`index.html`, `style.css`). No frameworks.
- Must be served via a local HTTP server (`python -m http.server`) — `fetch()` of `game.py` fails on `file://` due to CORS.
- No build step, no bundler. Keep it simple — this is a solo AI-assisted project, not a production app.

## Core design constraints (do not violate without asking)
- **No idle/wait-timer mechanics.** No countdowns, no "wait 30 min for upgrade." Everything is either an active click or a continuous passive rate — never a timer gate.
- **Mobile-friendly**, responsive, playable in a browser.
- Visual style: **text/numbers first** (no icons yet), but structure code so icons/images could be layered in later without a rewrite.
- Button press gives visible feedback (darkens briefly on click, ~120ms).

## Game concept
Universal-Paperclips-style incremental game, solar-system themed. Player starts clicking to gather a resource on Earth, unlocks automation, then expands outward through the solar system.

**Core loop progression:** click → automation → multi-resource economy → ecology tension → research-gated expansion → trade → terraforming → endgame.

### Key systems
1. **Resources** — named per planet (e.g. Iron, Water on Earth), not abstract points. Numbers can go into scientific notation at scale.
2. **Ecology system** — one global sustainability meter.
   - Below 10% health: 25% output penalty.
   - At 0% health: production halts entirely until back to 10%.
   - Recoverable by shipping in materials from an already-stabilized planet (ties into trade system).
   - Certain buildings cost resources to build but improve ecological health / contribute to terraforming.
3. **Research system** — NOT strictly linear planet-by-planet. Research unlocks "distance tiers"; reaching a tier can open multiple bodies in parallel (e.g. Jupiter's moons together). Some buildings require resources only found on specific other planets (e.g. gas giant buildings need Mars materials) — this is what makes trade matter.
4. **Trade system** — resource exchange between active planets. First introduced as a 2-planet mechanic, later extended to more.
5. **Governor system** — when the player leaves a planet, it doesn't go idle-silent; the player sets priorities + a resource budget, and a "governor" manages it passively while away.
6. **Terraforming** — a per-planet progress bar filled by sustained economic/ecological balance (not a separate grind resource).
7. **Manual clicking** — relevance fades as automation kicks in per-planet, but re-becomes relevant again on each *new* planet (small structural loop, not literal one mechanic reused forever).
8. **Gas giants** — reuse the standard building system, reskinned; not a separate subsystem.
9. **Win condition** — 100% completion across the solar system triggers a soft "win" state; game remains playable sandbox-style afterward.
10. **Balance philosophy** — soft punishment for imbalance, always recoverable. No dead-end/unwinnable states.

## Milestone plan (17 milestones, weeks 1–13; milestone 9 is a multi-part batch and will likely run over its single nominal week)

| Wk | Milestone | Content |
|----|-----------|---------|
| 1 | Core loop | Click Earth resource, dark-button feedback, basic mobile UI — **DONE** |
| 2 | First automation | Auto-generators, continuous passive rate, no timers — **DONE** |
| 3 | Ecology system | Global sustainability meter, penalty curve, ecology-improving buildings — **DONE** |
| 4 | Research system v1 | Tech-tree/distance framework, first unlock tier (Moon or Mars) — **DONE** |
| 5 | Planet transition + governor | Travel to new planet, governor priority/budget system — **DONE** |
| 6 | Second planet resource loop | New resource, reuse week 2/3 systems — **DONE** |
| 7 | Trade system v1 | Resource exchange between two planets, ties into ecology recovery — **DONE** |
| 8 | Terraforming | Per-planet progress bar — **DONE** |
| 9a | Research tier 2 framework | Second distance tier, parallel-unlocks Moon/Venus/Asteroid Belt/Pluto/Jupiter's moons/Saturn's moons; generalize governor + trade from a hardcoded 2-planet pair to N planets — **DONE** |
| 9b | Moon resource loop | New resource, reuse the standard building system — **DONE** |
| 9c | Venus resource loop | New resource, reuse the standard building system — **DONE** |
| 9d | Asteroid Belt resource loop | New resource, reuse the standard building system — **DONE** |
| 9e | Pluto resource loop | New resource, reuse the standard building system — **DONE** |
| 9f | Jupiter's moons resource loop | New resource, reuse the standard building system (one combined economy, not one per moon — matches the "parallel-unlock" framing) — **DONE** |
| 9g | Saturn's moons resource loop | New resource, reuse the standard building system (one combined economy, not one per moon) — **DONE** — Milestone 9 fully complete |
| 10 | Gas giant buildings | Reskinned building system + sky cities + Mars-material dependency — **DONE** |
| 11 | Full system endgame | 100% completion win-state, final balance pass — **DONE** |

All 17 milestones complete.

**Important:** milestones can be built ahead of schedule, but should be *tagged* (`git tag milestone-0N` — sub-parts of 9 use `git tag milestone-09a` etc.) at actual completion time and *not publicized* (Instagram/devlog) until their assigned week. Don't backdate anything — the tag date must be real. This is a deliberate anti-burnout pacing strategy, not a submission deadline system.

## Post-milestone audit notes
- Code-quality audit (Sep 2026): `deserialize_state()` used to `.clear()`
  `planet_state` before `.update()`-ing it from the loaded save dict, so a
  save whose `planet_state` was missing a body (an older save format, or a
  corrupted payload) would silently delete that body from `planet_state`
  entirely instead of leaving its freshly-initialized default state in
  place — the next `tick()` would then `KeyError` on that planet and crash
  the whole game. Fixed to merge into `planet_state` instead of replacing
  it wholesale; regression test in `tests/test_save_system.py`. Also fixed
  a CSS oversight where only Mars's "Return to Earth" button had a
  `margin-top` spacing rule — Moon/Venus/Asteroid Belt/Pluto/Jupiter's
  Moons/Saturn's Moons never got the equivalent rule when their views were
  built in later milestones, so their return buttons sat flush against the
  last summary block. No gameplay/balance changes.
- Second, more aggressive audit pass (same day): `press_feedback()` — which
  runs on essentially every button press — created a fresh
  `create_proxy()` for its one-shot `setTimeout` callback but never
  `.destroy()`-ed it after firing, leaking a PyProxy every press for the
  whole session; fixed by destroying the proxy from inside its own
  callback. Also found the planet-level merge fix above only went one
  level deep: `deserialize_state()` still replaced each present planet's
  own saved sub-dict wholesale, so a save missing a newer per-planet field
  (`trade_destination` pre-9f, `terraform_progress` pre-8, `sky_city_count`
  pre-10) would wipe that field's default and crash the next `tick()`;
  fixed to merge each planet's dict key-by-key too. Removed one orphaned
  CSS rule (`#away-summary`, no matching element) and corrected two
  comments left over from before every Far Body/gas giant had shipped.
  Regression tests in `tests/test_core_loop.py` and
  `tests/test_save_system.py`. Deliberately left alone: `#away-view` is
  confirmed genuinely unreachable now, but it's already documented and
  tested as an intentional retention rather than an oversight — removing
  it spans `index.html` + `conftest.py` + several test files, out of scope
  for this pass. No gameplay/balance changes.

## TODO.md "Per-game: SOL" batch + achievements retrofit (Sep 2026)
Ten items from the site-wide `planning/TODO.md` plus the achievements
unlock-toast/hub-link retrofit, all built this session on top of the
18-achievement catalog (`achievements.json`, `ACHIEVEMENT_CHECKS` etc. in
`game.py`) that shipped earlier the same day per
`planning/ACHIEVEMENTS-SYSTEM-DESIGN.md`.

- **Achievements retrofit**: an unlock-moment toast (`_display_toast()`,
  diffed each tick against a baseline re-seeded on every `_full_render()`
  so loading a save never replays its whole earned history as a burst of
  toasts) and a link from the in-game panel to the hub's
  `#account-achievements-dashboard`.
- **A1 (Prestige / New Game+)**: went with the simple flat-bonus version
  TODO.md itself leaned toward, not a skill tree — `prestige_level` (never
  reset) and a flat `+10%` resource-yield multiplier per level, applied to
  both manual clicks and automated production. Only available once every
  world is fully terraformed (reuses the existing win-banner's own hidden
  toggle — no separate gating needed since the button lives inside that
  banner). Resets every world's economy, research, unlocked/visited
  bodies, and Governor settings; keeps prestige_level, every lifetime stat,
  and every one-shot achievement flag. Deliberately does NOT try to
  preserve live-derived achievements (first_ore etc.) across a prestige —
  those are pure functions of planet_state, so resetting planet_state
  un-earns them exactly the same way spending your last Iron down to 0
  would without ever prestiging. `any_generator_ever_built` is the one
  exception that DOES reset on prestige, deliberately, so a New Game+ run
  gets a genuine second shot at the pure-clicker achievements below.
- **A2/A13 (second achievement wave)**: 4 new achievements (18 → 22),
  generous by design per the explicit "no extreme grinding" constraint —
  two speedrun-style (`quick_start`: Near Bodies tier within 10 sim-minutes;
  `swift_expansion`: both tiers within 30) and two pure-clicker
  (`manual_labor`: 100 Iron by hand before any generator anywhere;
  `off_the_grid`: clear the Near Bodies tier the same way). All four are
  one-shot historical flags, not live-derived — "before a generator ever
  existed" and "within N minutes" both describe play history a live check
  can't reconstruct after the fact, the same class of exception
  `visited_bodies`/`governor_purchase_count` already needed. Timers use
  `total_ticks` (an in-game clock, ticks × 100ms) rather than wall-clock
  time, so a backgrounded/throttled tab can't make them harder or easier
  than intended.
- **A3 (welcome-back toast)**: fires from `load_state()`/
  `load_save_state_json()` — the only situation SOL can call "a returning
  player." Since this game has no offline-production system (the "no
  idle/wait-timer mechanics" rule means nothing advances while the tab's
  closed), it's a snapshot recap of the loaded save's own current
  standing, not a "here's what happened while you were away" delta.
- **A4 + A8 (lifetime stats + shareable summary card)**: consolidated into
  one "📊 Stats & Share" toolbar panel rather than two separate ones — both
  are read-only look-back views and the toolbar already carries several
  other buttons. New lifetime counters (manual clicks, resources mined by
  hand vs. generated by automation, buildings built by type) all live
  outside `planet_state` so a world reset (A18) or a prestige (A1) can't
  touch them. The share card is plain text, not a rendered image — this
  project has no image/asset pipeline (see A6 below), and plain text is
  trivially shareable without inventing one just for this. The card's Copy
  button is static markup wired once in `setup()`, deliberately living
  outside the panel's own dynamically-rebuilt content div, so re-rendering
  the panel every tick it's open can't re-bind (and leak) a new listener
  the way `press_feedback()`'s own proxy-leak bug once did.
- **A6 (icon/visual layer)**: investigated first, per the "only if
  straightforward" instruction — found the codebase had *already* solved
  this, via a pure-CSS `[id$="..."]::before` icon system (see style.css's
  own "Icon labels" comment) covering every section label/button
  game-wide with zero markup or `game.py` changes needed. Concluded this
  satisfies the design doc's original ask on its own; added only a small
  finishing touch (planet-specific emoji on the 7 travel buttons, which
  the existing system gives one shared icon for the whole Travel section
  rather than one per destination). Did not need `LATER.md` — never became
  an asset-pipeline project because one already existed in a different
  (CSS-only) form.
- **A11 (governor efficiency readout)**: a new "🎛️ Governor Report" panel,
  one card per currently-governed world (every real planet except
  `current_planet`), showing the same `production_multiplier()` the
  ecology penalty already applies every tick (surfaced explicitly as a
  percentage) plus a new lifetime `governed_resource_generated` per-planet
  field — only accumulated when that planet's automation produces while it
  is NOT `current_planet`, i.e. genuinely "while you were elsewhere."
- **A15 (terraform color shift)**: a `terraform-tier-0`..`terraform-tier-4`
  class on each planet's existing `.planet-visual` container (one new `id`
  per planet, `_dom_id(planet, "planet-visual")`), with a `::after` overlay
  in style.css that layers an increasingly lush green tint over whatever's
  already drawn there (glow/rings/rocks/backdrop) rather than replacing it.
- **A16 (research-tree diagram)**: `update_research_tree_display()`
  replaces the single flat progress bar's implicit "what's next" with an
  explicit card per tier (Completed / In Progress / Locked, plus which
  bodies it unlocks), connected by a plain arrow — reuses the same
  dynamic-DOM-building pattern the achievements panel already established.
- **A17 (ecology warning banner)**: `.ecology-status--warning` turns the
  existing (always-present, previously plain-text) ecology-status
  paragraph into an actual bordered/colored banner exactly while the
  25%-output penalty or a full collapse is in effect.
- **A18 (reset this world)**: one new "Reset This World" button per
  planet, gated behind a real `confirm()` dialog (`_confirm()`, a lazy
  `import js` per call rather than a top-level `from js import confirm` —
  the latter would bind this module's own copy at import time in a way the
  pytest harness's fake couldn't swap out afterward for the cancel-path
  test). Clears only that world's own economy — resources, buildings,
  ecology, trade routes, terraforming; research, `unlocked_bodies`,
  `visited_bodies`, and every achievement are untouched, distinct from a
  full save wipe.
- **Bug found and fixed during this session's live-browser verification
  pass, unrelated to any of the above**: `.achievements-panel { display:
  grid }` (from the original achievements build) won the CSS cascade over
  the browser's own default `[hidden] { display: none }` rule, so toggling
  the panel closed left its `hidden` attribute and toggle-button label
  correct while the card grid stayed visibly on screen the whole time.
  Fixed with an explicit `.achievements-panel[hidden] { display: none }`
  override. Not caught by the pytest suite since the fake DOM harness
  tracks the `hidden` attribute itself, not real CSS cascade/rendering —
  worth remembering for any future element that combines a `hidden`
  toggle with its own `display` override.
- Tests: 522 → 616 across new files (`test_prestige.py`,
  `test_reset_world.py`, `test_lifetime_stats.py`,
  `test_governor_report.py`, `test_research_tree.py`) plus extensions to
  `test_achievements.py`, `test_ecology.py`, `test_terraforming.py`, and
  `test_save_system.py`. Verified live under Pyodide via the browser
  preview tooling (`hub-dev-server` launch config): toast lifecycle,
  achievements-panel hub link + the CSS bug above, Stats & Share and
  Governor Report panel content, the research-tree diagram, the ecology
  warning banner and terraform color tier via direct state manipulation,
  a full reset-this-world cycle, and a full prestige cycle (win the game →
  prestige → level 1, bonus applied, banner readout updated) — all with a
  clean browser console (no uncaught errors) in a freshly-loaded tab.

## Colorblind-safety audit (site-wide goal)

Audited as part of the site-wide colorblind-safety audit (Okabe-Ito-palette method, per Continuum's Phase 5, Canopy's B9, Tide's D11). Checked `game.py`/`style.css` for any place game-state meaning is conveyed by color alone.

**No real hue-only encoding found — no change made.** The candidates checked and ruled out:
- The ecology-status danger state (`.ecology-status--warning`, red-bordered) isn't paired against a green "healthy" equivalent — the ecology meter (`.meter-fill`) is a single always-green gradient bar whose *width* (not hue) shows health, and the warning state adds a border/background plus a "⚠ Output reduced 25%..." text line, not a red-vs-green color switch.
- The reset-world button (`.reset-world-button`, muted red border + amber text) is a single button with its own "Reset This World" label, not one half of a color-coded pair.
- Governor priority buttons (Growth/Balance/Ecology) and priority-option tiles (Travel) mark selection with a full background-gradient fill change plus a green LED dot — selected vs. unselected is green-vs-neutral-grey, not green-vs-red, and the button's own text label already states which option is active.
- Achievement cards' earned state (`.achievement-card--earned`, green border/glow) has no "failed"/red counterpart to be confused with — locked achievements are just the default card styling, not a red variant.
- Section accent colors (`border-left-color` per section: automation blue, ecology green, terraform cyan, research indigo, governor purple, trade amber, sky-city orange, travel green) are per-section decoration, each section already headed by its own text label — not a functional pair a player needs to visually discriminate for meaning.
- The research-tier panel's Completed/In Progress/Locked states are plain text labels (`update_research_tree_display()`), with no color-only distinction in `style.css` at all.

Matches Tide's D11 precedent: investigated a real candidate list, found the colors in play were never a genuine deuteranopia/protanopia confusion pair (no side-by-side red/green state pair exists in this game), and made no speculative change.

## Settings panel (site-wide goal, planning/TODO.md, origin A9)

A new `settings.js` (independent of Pyodide, same discipline as Continuum's
Phase 5 `accessibility.js` — see `games/continuum/CLAUDE.md`) consolidates
two real, working browser-level preferences into one panel behind a new
"⚙️ Settings" toolbar button, following the same hidden-until-opened
`.section` idiom every other panel here already uses (achievements/stats/
governor report):

- **Text size** (A−/A/A+, clamped 0.85–1.5, step 0.1) — sets `--text-scale`
  on `document.documentElement`; `style.css` reads it via
  `html { font-size: calc(16px * var(--text-scale, 1)); }`. Every font-size
  in this file was already `rem` (confirmed by grep before relying on
  this), so the one root-level change scales the whole game uniformly.
- **Reduce motion** (a checkbox) — sets `data-reduced-motion="true"` on
  `<html>`, which a new blanket CSS override collapses every
  animation/transition duration to ~0 for, additive to (not replacing) the
  existing `@media (prefers-reduced-motion: reduce)` rules already guarding
  planet-spin/rock-drift/meter-shimmer.

**Deliberately no sound toggle** — this hub has no audio system anywhere
yet (`planning/LATER.md`'s standing "what can you actually do with audio"
question), so a sound control would control nothing real.

Both settings persist to `localStorage` (`sol-text-scale`,
`sol-reduced-motion`) rather than `get_state()`/`load_state()` — a
per-browser accessibility preference, not portable save state, matching
Continuum's own K15 reasoning verbatim.

Verified live: 616/616 pytest suite unaffected (pure HTML/CSS/JS, no
Python touched); in a real browser, text-scale visibly resized every panel
and persisted its exact value across a fresh navigation via localStorage,
and toggling reduced-motion collapsed every `.planet-visual`-family
element's live `animation-duration`/`transition-duration` to ~1e-6s with
zero console errors. Verification required working around this sandbox's
own known static-asset HTTP-caching quirk (a fresh navigation kept serving
a stale `style.css`/`index.html` even after clearing the service worker and
Cache Storage — the same category of environment hazard Continuum's own
Milestone 11 build notes already documented for `sw.js`, but here at the
plain browser HTTP cache layer instead): confirmed by cache-busting the
stylesheet `<link>` directly (a fresh `?v=` query on its `href`), which
showed the real computed `html` font-size respond exactly as expected
(20.8px at a 1.3 scale) — not a defect in the shipped code.

## Onboarding-tooltip coverage check (site-wide goal, planning/TODO.md, origin A14)

Investigated whether the permanent UI explains itself to a returning player who
skipped/forgot the one-time tutorial (`shared/tutorial.js`'s spotlight walkthrough
only covers Earth's click/automation/ecology/terraform/research/governor/travel
steps) or the How-to-Play panel (persistent `#howto-toggle-button`, reachable any
time, not a one-shot).

**Found the permanent UI already covers almost everything**, via the `.info-toggle`
(i) icons added in an earlier pass (commit `c258996`, "SOL: add info buttons
explaining non-obvious mechanics") on Ecology, Terraforming, Research, Governor,
Trade Routes, and Travel — all on Earth's instance, which every player passes
through first regardless of save state, so the explanation is guaranteed seen
before the mechanic matters anywhere else in the system.

**Real gap found and fixed**: Sky Cities (gas-giant buildings, Jupiter's Moons +
Saturn's Moons only, Milestone 10) are a genuinely different mechanic — a dual-cost
building (local resource + Mars materials) — introduced nowhere on Earth and never
covered by the tutorial's STEPS array (which stops at Travel, well before any
gas-giant content is reachable). Their permanent UI (`Sky Cities: N (+X% production)`
+ a "Build Sky City (...)" button) had zero in-context explanation of what a Sky
City is or why it needs a second planet's resource. Added a matching `.info-toggle`
to both `#jupitermoons-sky-city` and `#saturnmoons-sky-city` in `index.html`,
reusing the exact same pattern/copy style as the existing six.

Not changed: nothing else — the ecology/terraform status paragraphs already
self-explain dynamically at the moment they matter (e.g. "⚠ Output reduced 25% —
ecological health critical", "Paused — ecology 40% (needs 60%+)"), which is a
stronger form of on-demand explanation than a static tooltip would be, so no
change was needed there.

Verified: full pytest suite green for this change (624 passed; 2 unrelated
failures in `tests/test_changelog.py` belong to a different session's concurrent
in-progress work on a separate feature, not touched by or affecting this change).
Live in a real browser (`hub-dev-server`, fresh tab to avoid a separate session's
concurrent browser-tab navigation), unhid both Sky City sections directly via JS,
confirmed the (i) icon renders and expands to readable text identical to the other
six info-toggles, with the DOM's "details becomes a sibling of the auto-closed
`<p>`" quirk matching the exact same pre-existing rendering behavior the original
six already have (browsers don't allow `<details>`, a flow-content element, inside
`<p>`, which auto-closes) — not a regression, a pattern already shipped and verified
site-wide. One unrelated pre-existing console error was observed (an `AttributeError`
from a `None.addEventListener` call) tied to another session's concurrent
in-progress "What's New" changelog feature (uncommitted `game.py`/`style.css`
changes at the time) — not caused by, or fixed by, this change.

## "What's New" changelog panel (site-wide goal, planning/TODO.md, origin K16)

A new `changelog.json` manifest (flat list of `{date, entry}` objects,
hand-authored newest-first, pulled from this file's own milestone table
and the session build notes above — a quick highlights view, not a full
duplicate of the dev logs) plus a "📋 What's New" toggle+panel, following
the exact same hidden-until-opened `.section` idiom and dynamic-DOM-build
pattern the achievements/stats/governor-report panels already established.
Fetched into the Pyodide boot sequence alongside `achievements.json`
(`window.CHANGELOG_JSON`), with the same disk-read fallback for the pytest
harness's fake `js` module that `ACHIEVEMENTS` already uses. `tick()` and
`_full_render()` both keep an open panel live, same as every sibling panel.

Tests: 616 → 626 (`tests/test_changelog.py`: catalog sanity, toggle
open/close, panel content matches `CHANGELOG` newest-first, tick-liveness).
Verified live under Pyodide via the `hub-dev-server` launch config: panel
opens and lists all 12 real entries with correct dates/text, toggle button
label flips to "Hide What's New", zero console errors on the SOL page
itself.

## UI decluttering pass (site-wide goal, planning/TODO.md closing task)

Audited whether SOL's single-page view is too crowded, per the site-wide
"UI decluttering pass" task (the user's own note: "everything looks very
crowded... making sections either collapsible or other 'screens' within a
game could help"). Read through `index.html`'s full structure across all
nine views (Earth + 7 planet views + the `away-view` travel placeholder).

**Real crowding found, and it wasn't the panels already gated behind
toggle buttons** (Achievements/Stats/Governor Report/Settings/Changelog
are already `hidden`-until-opened `.section`s, per their own build notes
above — those already solved this). The actual problem was the
`cross-summary` widgets: every non-Earth planet view unconditionally
stacks six or seven "`<Planet>` (governed)" status cards — one per every
*other* real economy — one after another, with no `hidden` gating at all
on those views (only Earth's own copies were gated, per
`update_cross_summary()`'s comment on this). That's up to 7 always-visible
read-only stat cards piled beneath the view's own
automation/ecology/terraform/trade/sky-city sections and above its Reset/
Return buttons — by far the densest stretch of the page, and the one part
of the layout that scales with how many planets are unlocked rather than
staying fixed.

**Fixed**: wrapped each view's own group of `.cross-summary` divs (Earth's
7 gated ones, and the 6-8 unconditional ones on each of Mars/Moon/Venus/
Asteroid Belt/Pluto/Jupiter's Moons/Saturn's Moons/`away-view`) in a new
`<details class="cross-summary-group"><summary>Other Worlds
(Governed)</summary>...</details>`, collapsed by default — same
`<details>`/`<summary>` disclosure idiom `.info-toggle` already uses here,
and Tide's `.ticker-history-toggle` uses for its own "supplementary,
not-checked-every-turn" panel. Purely a markup wrapper: every inner div
keeps its exact `id`/class/`hidden` attribute, so `update_cross_summary()`
and `update_all_cross_summaries()` in `game.py` (untouched, zero Python
changes) keep toggling each card's visibility by its own id exactly as
before — the `<details>` wrapper doesn't know or care which children are
currently hidden inside it. New `.cross-summary-group` CSS in `style.css`
(arrow-marker summary matching the site's existing disclosure look, no
changes to `.cross-summary`'s own card styling). Nothing else on the page
was dense enough to warrant touching — the per-planet sections
(automation/ecology/terraform/research/governor/trade/sky-city/travel)
are each a single focused block already given their own bordered card via
the existing "HUD module" `.section` styling, not a wall of undifferentiated
text.

Verified: full 626/626 pytest suite green (pure HTML/CSS change, `game.py`
untouched, and no test asserts exact DOM nesting around the cross-summary
divs — confirmed by grep before relying on this). Not verified live in a
running browser this pass (a markup-wrapper-only change with no JS/Python
behavior difference and an existing widely-used `<details>` pattern
elsewhere on this same page).

## Working conventions
- Commit + tag at the end of each milestone: `git commit -m "Milestone N: <name>"` then `git tag milestone-0N` (e.g. `milestone-09a` for lettered sub-parts of milestone 9).
- Keep `game.py` as the single source of game logic where reasonable; split into modules only once it gets unwieldy.
- Public evidence: Instagram (BCM114, audience-facing) + WordPress devlog on ah752bcm.wordpress.com under a new tag/category (BCM206, process-facing) — not part of this codebase, but milestones should produce something screenshot/clip-worthy.
- Prefer asking before large architecture changes — this project intentionally avoids scope creep beyond what's listed above.
