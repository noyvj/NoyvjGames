# SOL notes (long history)

This is the long history moved out of CLAUDE.md on 2026-10-18 (per-item build notes, audit logs, dated batches). The local AI should read only the section it is told to (`grep -n "^## " NOTES.md` lists them), never the whole file.

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

## Reset-to-default settings button (Z-extra/A26, site-wide goal)

A "Reset to Default" button (`#settings-reset-button`) sits at the bottom of the settings panel, below the existing text-size and reduce-motion controls -- SOL's own A26 answer flagged this as a site-wide pattern rather than a SOL-only feature, folded into `planning/TODO.md`'s Z-extra checklist. Implemented entirely in `settings.js` (no Python touched, matching this file's own "deliberately independent of Pyodide" rule for the rest of the settings panel): one click calls `applyScale(DEFAULT_SCALE)` and `applyMotion(false)`, updates `--text-scale`/`data-text-scale`/`data-reduced-motion` on the live DOM immediately, resets the reduce-motion checkbox's own `checked` state to match, and writes both defaults back to `localStorage` so the reset survives a reload rather than only looking reset until the next render. No confirmation dialog -- this is a low-stakes, instantly-reversible display preference, not a destructive action, so `shared/confirm-dialog.js` is deliberately not wired up here.

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

## Per-game TODO batch, A1-A30 (2026-09-20)

Built from `planning/TODO.md` "Per-game: SOL". All new persistent state is in `get_state()`/`load_state()` via `_load_session_additions()` (each field defensively typed; legacy saves default prestige points to prestige level). Tests 626 -> 670 (`tests/test_session_batch.py`).

- **A9 Overview** (toolbar "Overview"): a card per unlocked world (resources, buildings, ecology/terraform bars, efficiency, routes, Sky Cities), a "Travel here" button (any world to any world), and per-world Governor + Focus controls. Cards are rebuilt only when structure changes (signature check) and updated in place each tick, so buttons stay clickable; all buttons in panels use one delegated listener reading `data-*` attributes (`_target_attr`).
- **A7** per-world Governor personality (Global/Aggressive/Balanced/Conservative presets override the global dial in `governor_step`). **A23** planet Focus (Output: +25% yield, +25% ecology decay; Stability: -30% decay), available at 75% terraform.
- **A13 Build Plan**: manual checklist (30 steps, 80 chars), suggested opening, saved in state.
- **A1/A3 Prestige Tree**: 1 point per prestige. Tier 1 (Head Start, Cheaper Machinery, Eco-Conscious); Tier 2 (Deep Research, Governor's Mandate) gated on Prestige Level 3; "New Game+ Challenge" node (level 2) unlocks a harder-replay toggle (+0.05 generator/Recycler cost growth, +1 extra point on prestige).
- **A2** title badge, **A24** per-world "+N% Prestige bonus" tag, **A4** prestige-button tooltip, **A18** Governor priority tooltips, **A28** exact Sky City ratio (5:2, +15%/city), **A16** "N/8 bodies visited", **A20** terraform swatch legend, **A14** collapsible research tiers, **A8** governed-total stat row, **A6** copy button flashes "Copied!".
- **A5** away report: on returning to a world, shows resources generated, Governor buys and ecology change since leaving. Uses simulated ticks (not wall clock) and is transient (not saved); no offline progress, so the no-idle rule holds.
- **A15** sandbox (post-win, zero costs, off on prestige), **A27** epilogue panel, **A12/A30** floating spark/build icons (`#spark-layer`, hidden under reduced motion, silently skipped headless).
- **A17** `SOLSTATS1:` base64 lifetime-stats code (import only raises counters). **A21** Compare my run: `compare.js` calls the public `GET /stats/games/sol/percentile` only on button click, degrades to one calm sentence (backend not deployed yet).
- **A19** two achievements (Close Call, Back From the Brink; 22 -> 24), historic flags + per-world pending sets, cleared on world reset/prestige.
- Not done: A25 (SOL has no existing flavor text to surface), A29 (needs backend), A10/A22/A26 (folded into Z). Live-verified in the browser pane (overview, build plan, prestige tree, away report, floaters, stats code, compare fallback); only network errors in console.

## Welcome-back toast: real delta, not a static snapshot (V-CD-4, 2026-09-21)

The completion-verification audit found the original A3 idea asked for
"what changed since last session"; what shipped was a static recap of
current standing ("N/8 worlds visited, X achievements earned") on every
save load, with no actual comparison against a previous visit. The
user's answer: "real delta."

SOL has no offline-production system (this project's own "no idle/wait-
timer mechanics" rule), so there's genuinely nothing that changes purely
from time passing — the only meaningful "since last time" comparison is
against what THIS BROWSER last saw, not what the loaded save code
implies (a save is portable across devices, so diffing against the save
itself would conflate "time passed" with "you're on a different
computer"). `_load_welcome_back_snapshot()`/`_save_welcome_back_
snapshot()` persist a `{worlds_visited, achievements_earned}` pair to
`localStorage` (`_read_local_storage_item()`/`_write_local_storage_item()`,
the same lazy-`import js`/per-browser-record pattern Canopy's
`personal_best` and Tide's `best_coastline_saved` already established —
deliberately outside `get_state()`, since this is a per-browser fact, not
a save-state fact) — SOL's first use of Python-side `localStorage`.

`_show_welcome_back_toast()` now diffs the just-loaded numbers against
the stored snapshot and shows "+X world(s) visited, +Y achievement(s)
since you were last here" when both deltas are non-negative and at least
one is positive. Falls back to the original static wording in the two
cases where a delta wouldn't make sense: this browser's first-ever load
(nothing stored yet), or the loaded save's numbers sitting at or below
the stored snapshot (an older or different save code loaded into the
same browser) — never shows a negative delta as though progress was
lost. The stored snapshot updates to this load's numbers only AFTER
computing the delta against the OLD values, so the next visit compares
against this one, not a frozen baseline.

Tests: 670 -> 676 (new `tests/test_welcome_back_delta.py`: first-load
fallback, a genuine positive delta, the same-or-lower no-negative-delta
guard, the snapshot updating correctly across two consecutive loads,
malformed-storage defaulting, and confirming the snapshot never leaks
into `get_state()`). A new `FakeLocalStorage` (`tests/fakes.py`) backs
`game_env.local_storage` for these tests. flake8 clean. Verified live:
cleared `localStorage`, confirmed the first load shows the static
snapshot, then confirmed a second load after real progress shows the
real "+1 world(s), +1 achievement(s)" delta, zero console errors.

## Export-progress shared helper (Z8, site-wide goal)

`planning/TODO.md`'s Z8: A17's `SOLSTATS1:` stats code now runs on a new
shared `shared/export_progress.py` module (the base64<->JSON codec, the
prefix check, the finite-non-negative-number field validation, and the
"counters only ever go up" max-merge) instead of hand-rolling all four of
those inline. Aftermath's E12 export/import migrated onto the same shared
module in the same pass — the two turned out to be genuinely different
shapes of one "portable progress-code" pattern (A17: flat counters,
monotonic merge; E12: a structural bundle, replace-on-import), which is
why the shared module exposes small composable pieces
(`encode_progress_code`/`decode_progress_code`/`validate_numeric_fields`/
`merge_counters_max`) rather than one do-everything function.

Pure refactor, no player-visible change: `export_stats_code()`/
`import_stats_code()` keep their exact signatures, the exported code's
shape (`SOLSTATS1:` prefix, same field set, `prestige_level` still along
for the ride on export only, unchanged from before) and status messages
are untouched, and the "Export / import lifetime stats" panel's UI/copy
didn't change. `game.py` now does `import export_progress` — SOL's first
use of a shared Python module, loaded into Pyodide's virtual filesystem by
`index.html` the same fetch-then-`FS.writeFile` way Aftermath's
`info_page.py` already is (and pointed at via `sys.path` in
`tests/conftest.py`, matching Aftermath's own conftest pattern, since this
is SOL's first shared-module import for tests to resolve at all). No
`changelog.json` entry added — A17 itself already shipped and was already
checked off in `planning/TODO.md` before this pass; only its internals
moved.

Verified: full pytest suite (680/680) and `flake8` clean. Live via
`hub-dev-server`: exporting real (non-zero) lifetime-counter state
produced a correctly-prefixed, real decodable code; importing a code with
a lower counter value correctly left the higher existing value alone
(monotonic merge); and both a garbage string and a wrongly-prefixed code
failed soft with the existing "That doesn't look like a SOL stats code."
message — zero console errors throughout.

## Working conventions
- Commit + tag at the end of each milestone: `git commit -m "Milestone N: <name>"` then `git tag milestone-0N` (e.g. `milestone-09a` for lettered sub-parts of milestone 9).
- Keep `game.py` as the single source of game logic where reasonable; split into modules only once it gets unwieldy.
- Public evidence: Instagram (BCM114, audience-facing) + WordPress devlog on ah752bcm.wordpress.com under a new tag/category (BCM206, process-facing) — not part of this codebase, but milestones should produce something screenshot/clip-worthy.
- Prefer asking before large architecture changes — this project intentionally avoids scope creep beyond what's listed above.
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

## Reset-confirmation migration to shared ConfirmDialog (Z22, site-wide goal)

`planning/TODO.md`'s Z22 audit flagged SOL as one of two games (Aftermath's
skill-tree reset is the other) whose irreversible-action confirmation
predates `shared/confirm-dialog.js`: Reset This World (A18) and Prestige/
New Game+ (A1) both gated on a native `js.confirm()` (`_confirm()`, a lazy
per-call `import js`). Migrated both to the shared ConfirmDialog via a new
`_confirm_dialog_ask()` helper, same shape as Grid/Herd/Loop/Trade Empire's
own copies — falls through to running the action immediately if `window`
or `window.ConfirmDialog` isn't available (Pyodide not loaded yet, or the
script somehow missing), which is also what the pytest fake-DOM harness's
`js` module does by default. Added `shared/confirm-dialog.js` to
`index.html` — SOL never included it before, since it had no prior use for
the shared widget.

`_reset_world()`'s and `on_prestige()`'s actual mutation logic is
unchanged, just moved inside an `on_confirm` callback instead of running
directly after an `if not _confirm(...): return` guard. `on_prestige()`
no longer needs `global prestige_level` at its own top level — only
`_do_prestige()` mutates it now, declared in its own scope.

`tests/conftest.py`'s old `set_confirm_response()`/`fake_js.confirm`
plumbing was removed (nothing reads `js.confirm` anymore) in favor of a
new `tests/test_confirm_dialog.py`, matching the technique already
established by Grid/Herd/Loop/Trade Empire's own `test_confirm_dialog.py`
files: a fake `window.ConfirmDialog` installed only where the real gating
branch needs exercising, recording `ask()` calls and letting a test fire
the pending `onConfirm` on demand. The pre-existing
`test_prestige_does_nothing_without_confirmation`/
`test_reset_does_nothing_without_confirmation` tests (which drove
`js.confirm` returning `False`) were replaced by `test_confirm_dialog.py`'s
`test_cancelling_*_leaves_*_untouched` equivalents — same behavior, correct
mechanism.

Tests: 676 → 680 (`test_confirm_dialog.py`'s 7 new tests, net of the 2
removed from `test_prestige.py`/`test_reset_world.py`), all green;
`flake8` clean. Live-verified via `hub-dev-server`: clicking "Reset This
World" on Earth shows the dialog with the correct message and a "Reset
Earth" (not generic "OK") confirm label; Cancel leaves `resource_count`
untouched; a second click through to Confirm actually resets the planet.
Zero console errors throughout.

## 320px mobile-viewport audit (Z18, site-wide goal, planning/TODO.md)

Checked at a genuine 320px viewport (narrower than the original 375px
mobile pass) via the Claude Browser tool's `resize_window`: tutorial, How
to Play, Overview, Build Plan, Achievements and Settings panels, plus a
full-DOM `scrollWidth`/`clientWidth` sweep. No SOL-specific overflow
found — audited, no change needed.

**Real bug found here, but fixed at the shared site level, not in this
game:** the fixed bottom ad bar (`ad-bar.css`, present on every game's
page) had its "Ad" label sitting as a normal flex sibling of the 320px-wide
ad slot inside `.ad-bar`'s `justify-content: center` row — the label's own
width plus the row's `gap` pushed the combined content past 320px,
clipping ~13px off *both* edges of the ad slot on every phone-width screen
(320–480px), not just 320px; the original 375px mobile pass never isolated
the ad bar to notice it. Fixed in `ad-bar.css` by taking the narrow-screen
label out of the flex flow (`position: absolute`, overlaid rather than
laid out beside the ad slot), so `justify-content: center` centers the ad
slot alone at its full width. This fix applies to all 12 games at once
(shared file) — see root `CLAUDE.md`'s Working notes for the full writeup.
`flake8`/tests unaffected (pure CSS); SOL's own suite stayed at 680/680.

## Difficulty-aware achievements audit (Z27, site-wide goal)

`planning/TODO.md`'s Z27: check whether any achievement becomes impossible
or trivially easy under a game's own hard-mode/difficulty toggle. SOL's
only real candidate is the prestige tree's "New Game+ Challenge" node
(`ng_challenge`/`ng_challenge_active`, A1/A3) — a genuine opt-in harder
replay variant: once unlocked it can be switched on/off freely at any time
(`_challenge_on()` just reads the two flags live, no lock-in), and while on
it grows every generator's and Recycler's cost faster (`NG_CHALLENGE_COST_
GROWTH_BONUS`), in exchange for +1 extra prestige point per prestige.

Checked all 24 achievements against it. The two time-limited ones
(`quick_start`, `swift_expansion` — fund a research tier within 10/30
sim-minutes) get genuinely harder with the challenge on, since a slower-
growing economy is slower to reach a funding target — but not impossible:
the toggle is freely reversible, so a player going for either achievement
can simply switch it off first, and neither achievement's own condition
checks whether the challenge was active while earning it. The two pure-
clicker achievements this same wave added (`manual_labor`, `off_the_grid`)
are explicitly defined as "before ever building a generator anywhere," so
a cost-growth toggle on generators has no bearing on them at all. Every
other achievement (ecology thresholds, building counts, trade routes,
terraforming, visited-body counts) reads state that the challenge toggle
never touches.

**No change needed.** Every toggle in SOL that affects economy pacing is
freely switchable per-action rather than a session-locked choice, which is
what keeps a harder setting from ever permanently locking an achievement
out — the player can always turn it off immediately before attempting
something toggle-sensitive. No simulation was needed; the toggle's own
implementation (a live-read boolean with no historical stickiness) settles
this by inspection. `flake8`/tests unaffected — no code touched.

## Achievement-progress bar in toolbar (Z-extra/A10, site-wide goal)

Already satisfied — see the existing toggle-button label. SOL's own
`update_achievements_display()` sets `#achievements-toggle-button`'s
`innerText` to `"🏆 Achievements (N/M)"` (or `"Hide Achievements (N/M)"`
while open), and that function is called from the main render loop, not
only from the toggle handler — so the live earned/total count is visible
in the toolbar on every render, before the panel is ever opened. This is
in fact the pattern SOL's own A10 answer flagged as worth rolling out
site-wide. No code change needed here.

## "What's new since you played" banner (Z24, site-wide goal)

A new shared `shared/whats-new-banner.js` -- deliberately distinct from
this game's own in-game "📋 What's New" changelog PANEL above (opt-in,
player-triggered, always shows the full history from scratch). The
banner instead appears automatically on page load, but ONLY for a
RETURNING player who has missed real entries since their last visit: it
diffs this game's `changelog.json` against
`localStorage["whats-new-seen:sol"]` (the date string of the newest
entry already shown) and lists just the new ones, not the whole log. A
first-ever visit silently marks the current changelog as seen rather
than dumping the full history on a brand-new player. Reuses the same
`window.CHANGELOG_JSON` global this game's own changelog panel already
fetches -- no second network request. One `<script
src="../../shared/whats-new-banner.js" data-game-id="sol">` include,
added right after `shared/last-played.js`'s own include. See root
`CLAUDE.md`'s Working notes for the full write-up -- shared
infrastructure, documented once there rather than duplicated across all
12 games' own files.

## Keyboard-shortcut convention: ?/Esc (Z4, site-wide goal)

Wired via the new shared `shared/keyboard-shortcuts.js` (see that file's
own header comment for the full API and rationale) -- one script include
plus one `KeyboardShortcuts.init({panels: [...]})` call at the end of
`index.html`, listing every real toggle-button + hidden-panel pair this
game has: How to Play, Settings, Achievements, Stats, Governor Report,
What's New, Overview, Build Plan, Prestige Tree, and the Epilogue
(`epilogue-button`/`epilogue-panel`). `?` opens/closes a small floating
help overlay (built generically by the shared file, since SOL had no
pre-existing one of its own); `Esc` closes the help overlay and clicks
the toggle button of whichever of the listed panels is currently open,
reusing each panel's own existing open/close logic (button-label swaps
like "Achievements (N/M)" stay correct) rather than touching `.hidden`
directly. Sandbox mode's flag toggle and the always-visible cross-summary
`<details>` groups aren't in the panel list -- neither has a dismissible
"panel" shape a generic Esc handler could safely close.

## Hold to repeat (U11, 2026-09-26)

Holding the mining click button or any world's Auto-Miner/Recycler buy button repeats it slowly: after a 450ms pause, one extra click every 250ms (about 4 a second). It's deliberately gentler than a quick manual clicker so it spares hands during a big buying session without beating manual play; a plain tap is still exactly one click. Implemented in `hold-repeat.js` (plain DOM JS beside `settings.js`, no Pyodide dependency): it clicks the real buttons, so every cost/disabled/achievement rule in `game.py` still applies. Covers mouse, touch and Enter/Space (native Enter key-repeat is swallowed so it can't outrun the timer), stops on release/leave/blur/tab-hide, and suppresses the release click after a real hold so it doesn't add one more. A "Hold to repeat" checkbox in Settings (on by default, persisted to `localStorage["sol-hold-repeat"]`, restored by Reset to Default) turns it off; it is a browser preference and never part of the save code. 680 → 686 tests (`tests/test_hold_repeat.py`, structural, since the JS has no Python harness); verified live: a 2.1s hold gave 7 repeats, a tap gave 1, none after release, and the checkbox disabled it.

## Research tree (U10, 2026-09-26)

The two flat research bars (Fund Research, 50 Iron a click) are replaced by a real tree. Each distance level is a 20-node graph that splits into branches and rejoins, ending at that level's final node; researching the final node is what unlocks the bodies (`near_bodies` unlocks the Moon and Mars, `far_bodies` unlocks the five Far Bodies, and level 2 is locked until level 1's final node is done). Per the user's answers: costs vary per node but each level still adds up to the old bar's total (Near Bodies 1000, Far Bodies 5000), most nodes carry a small real bonus, and existing saves convert without loss.

- **Data:** `_RESEARCH_LEVEL_ROWS` (id, name, cost, requires, effects) builds `RESEARCH_NODES`, `RESEARCH_NODE_BY_ID` and `RESEARCH_TIERS` (whose `target` is now derived from the node costs and which gains a `final` id). `researched_nodes` is the one piece of research state; `completed_tiers` and `research_progress` are derived from it by `_recompute_research()` (kept as variables for their many readers: achievements, stats, travel).
- **Effects** (percent, summed over researched nodes): `yield_pct` scales manual clicks and automated production through `_yield_multiplier()` (prestige bonus times research), `machinery_discount` scales Auto-Miner and Recycler costs, `route_discount` scales trade routes. The Deep Research prestige perk now makes every node cost a third less (rounded up), replacing its old "1.5x progress per click".
- **UI:** the research section lists the current level's nodes with cost, effect, and what a locked node still needs; a node button buys it (delegated click, `data-node`). The old bar and progress text remain as the level's invested-Iron summary, and the tier diagram cards are unchanged. The tutorial's research step was reworded.
- **Save:** `researched_nodes` (sorted list). On load it is pruned by `_clean_researched_nodes()` to a valid tree (unknown ids dropped, and any node missing a prerequisite or an earlier level's final node is dropped) so a tampered save can't grant an unbuyable node. A save from before the tree (`completed_tiers` + `research_progress`) is migrated by `_migrate_legacy_research()`: every node of completed levels, then as many of the current level's nodes as the saved progress paid for (never the final node), with any leftover Iron refunded to Earth.
- 680 -> 687 tests: `tests/test_research.py` rewritten for the tree (33 tests: shape and sums, splits/joins, buying rules, effects, migration, tampering); four other tests updated. Verified live: 20 rows, buying the root node spent its 20 Iron, unlocked its children, and showed up in `serialize_state()`.

## Community leaderboard (A29, 2026-09-26)
`full_system_completed_tick` records `total_ticks` the first time every world is terraformed (kept for life, saved only once set, strict int validation on load). `_note_full_completion()` runs each tick from `_check_new_achievements_for_toast()` and `_report_full_completion()` hands simulated seconds to `window.NoyvjLeaderboard.report('sol', 'fastest_completion', ...)` once per page load; the shared `shared/leaderboard.js` widget (mounted in the Stats panel) submits only for a signed-in player who ticked the opt-in box. Backend: `/leaderboards/sol/fastest_completion` (see BCM206 log). Tests: `tests/test_leaderboard_completion.py` (7).

## Captain's log (A25, 2026-09-26)
A light narrative thread rather than a new system: `story_log` records `arrive:<world>` on first arrival (`_mark_visited()`; Earth at the start) and `ach:<id>` for every newly earned achievement (`_check_new_achievements_for_toast()`), always, so the history exists whether or not story text is showing. Lines are the achievements' own `label: description` plus one short authored arrival line per world (`STORY_ARRIVAL_LINES`). `render_story_log()` shows the latest as an italic banner under the title and the full log newest-first in a collapsible panel; both element ids are in the story-toggle include's `data-story-selectors`, so the existing per-device Story pill hides or shows them, satisfying 'a story mode toggle' without a second control. Saved as an optional `story_log` list only when non-empty; on load every id must be a known arrival or achievement, unique, capped at `STORY_LOG_MAX` (80). No number or unlock changes. Tests: `tests/test_captains_log.py` (8; 694 -> 702). The user then asked for deeper story modes in the low-story games; that is tracked as TODO section W1 (SOL's own deepening is W1-sol).

## Deeper captain's log beats (W1-sol, 2026-09-26)
Extends A25's log rather than adding a second story panel: `STORY_TERRAFORM_LINES` (one paragraph per world), `STORY_ROUTE_LINE` and `STORY_PRESTIGE_LINE`, noted idempotently by `_note_story_beats()` from the every-tick achievement check (`terraform:<world>` when that world's terraform progress reaches `TERRAFORM_MAX`, `route:first`, `prestige:1`). `story_line()` knows the new kinds and load-time validation drops any unknown or duplicate ids, so the optional `story_log` save key keeps its shape. Same Story pill, same panel. Tests added to `tests/test_captains_log.py` (8 -> 11; 702 -> 705).

## Y11b light-theme polish (2026-09-27)

Method: a computed-style WCAG scan run in a real browser with the light theme on (walks every visible element with text, composites the ancestors' backgrounds including gradients, compares against the computed text colour, flags below 4.5:1 for normal text and below 3:1 for large text; also flags meter/track/tile fills that sit within 1.5:1 of their parent and dark surfaces left under the light theme). Disabled buttons are excluded (WCAG exempts inactive controls) and counted separately. It was run on the fresh game and again after playing, with every panel opened one at a time, and finally with every `[hidden]` element force-shown to catch panels a normal session does not reach. Screenshots in this environment were unreliable, so the scan output is the evidence, not eyeballing.

**Found (before):** about 18 text groups on the fresh game and 5 more after play: pale accent text on light (research status green 1.66:1, ecology and reset-world amber 2.1:1, prestige, epilogue, report and share greens, spark floaters), locked and researched research nodes dimmed to .5-.65 (2.1-3.7:1), the research node name/detail lines, the Governor priority buttons (`button.priority-option`, light text on a translucent-dark fill, 2.4:1), section labels and captions at opacity .6-.7 (4.1-4.3:1), the info "i" (1.23:1), and the selected Global/Local mini button (2.0:1). Forcing every hidden panel visible also caught the "Other Worlds" cross-summary labels (3.66:1, 64 of them).

**Fixed:** a `Y11b` block at the end of `style.css`, all under `html[data-theme="light"]`: deeper greens and ambers, node opacity raised, captions to a deeper slate at full opacity, light Governor buttons (the selected one stays dark blue with white text and its green LED), selected mini button. Locked research is still told apart by its "Locked" status label, not only by dimming.

**(d) Theme toggle moved into Settings.** The Settings panel (Display Settings) has a new "Colour theme" row holding `<button id="theme-toggle" class="secondary theme-toggle">`. No change to `shared/` was needed: `shared/theme.js` already binds every `#theme-toggle` / `.theme-toggle` element (label text, `aria-pressed`, click) after DOMContentLoaded, and the pill is only created when the script tag carries `data-floating-toggle`, which SOL's tag no longer does, so the floating pill is gone. `settings.js` was left untouched (it has no theme code, and the test pins that). Account sync (`shared/site-settings.js`) listens to the same `noyvj-theme-change` event, so it is unaffected. Verified live: the pill is absent, the button reads "Dark mode" in light and "Light mode" in dark, `aria-pressed` follows, `localStorage["theme"]` and `data-theme` change on each click, and the change event fires once per click.

**After:** 0 flagged text and 0 flagged fills on the fresh game, after mining/buying with Overview, Build Plan, Achievements, Stats, Governor Report, What's New, Settings and a priority change open, and with all 83 hidden elements force-shown (1095 text nodes). Exceptions: disabled buttons (exempt), the gradient-clipped `h1`, the achievement toast (dark in both themes). Tests: `tests/test_light_theme.py` (the light-scoping check plus five Settings-control checks: the button sits inside `#settings-panel`, the script tag has no `data-floating-toggle`, load order, the shared binding contract, and no duplicate handler in `settings.js`).

## Welcome-back delta and fastest playthrough (R-9, R-10, 2026-09-27)
R-9: the browser-side welcome-back snapshot gained optional `machines_built` and `manual_clicks` (older snapshots load with None and simply skip them); the toast adds ', +N machine(s) built, +M hand-mined load(s)' when either rose and never shows a negative. R-10: `run_start_tick` (reset by each prestige), `run_completed` and `best_run_ticks` (shortest completed run, kept for life) record the fastest full playthrough per run in `_note_full_completion()`; shown as 'Fastest full playthrough' in the Stats panel; the three save keys are written only when set and validated as non-negative ints below 1e12. R-11 (a never-touched-automation challenge) was already covered by the shipped Manual Labor and Off the Grid achievements. Tests: welcome-back +4 and `tests/test_best_run.py` (5); 713 -> 722 tests.

## Desktop boot (PC version, 2026-10-07)

`games/sol/pc.html` is the Desktop boot: the same game over the same `game.py` and saves (same `game_id`), laid out for a wide window with a mouse. **Never edit it by hand**: it is generated from `index.html` plus `pc-config.json` by `scripts/generate-pc-pages.py` (run it after changing either; `--check` and `shared/tests` fail if it is stale). No rule, state or save change, and `game.py` is untouched. Per-game files: `pc-config.json` (what moves where), `pc.css` (layout, all under the pc layout), `pc.js` (`window.SOL_PC_TUTORIAL_STEPS`, which `index.html` uses when present, plus the hero-grouping, chip-visibility and Escape helpers described below). Classic (`index.html`) only gained the `shared/layout-pref.js` tag and the `window.SOL_PC_TUTORIAL_STEPS ||` fallback on the tutorial init. `MobileHud` still runs but is hidden by `pc.css`. SOL's tests were unchanged by the Desktop boot itself (the changelog test's cap of 30 entries has room for the new entries).

- **Layout.** No page scroll. Top bar: back link, title, four icon buttons (Overview, Achievements, Stats and Share, Settings) and the Menu (Esc). Under it one chip per world you have unlocked showing that world's resource (Iron, Water Ice, Regolith, Sulfur, Platinum, Tholins, Helium-3, Methane); the game updates every world's count every tick, so the chips keep counting for worlds you are not on. The stage is the current world's view. A world's view is one hidden-or-shown block (the game hides and shows whole `*-view` divs), so it cannot be split between a stage and a side column from outside; the view itself is the grid and the shell's side column is unused. Left: the "hero" (planet picture scaled up, resource name, count, Mine button; `pc.js` wraps these nodes in a `.pc-hero` div, nodes are moved not copied). Right: that world's cards, Auto-Miner and Trade Routes on the first row, Ecology and Terraforming on the second, Travel (Earth only, destinations in a grid), Sky Cities (gas giants only), Other Worlds and Reset This World, then Return to Earth on the other worlds. Above the stage a strip holds the captain's-log line, the away report and the win banner (Prestige / Epilogue / Sandbox), each only while shown.
- **Windows from the Menu or the icons.** How to Play, Overview, Achievements, Stats and Share, Governor Report, Build Plan, Prestige Tree (button appears once a prestige has been done), What's New, Settings, Epilogue (opened by its button in the win banner), plus composites Research tree (the whole Research section, nodes in two columns), Governor (priority and budget) and Captain's log. Research and the Governor live in Earth's view in Classic and so only exist there; here they are windows, so they open from any world (buying a node still spends Earth's Iron, and the Governor dial is the same global setting the Overview and Governor Report already expose from anywhere).
- **Desktop tutorial.** `pc.js` sets 9 steps (Mine, resource chips, Auto-Miners, Ecology, Terraforming, Travel, icons plus the Menu where Research and the Governor now live); every selector exists on `pc.html`.
- **Notifications and hotkeys.** `notify` is null: the only log (`#captains-log-list`) is the Story panel, which the Story pill can turn off, and achievements already have their own toast. The only real hotkeys are `?` (shared shortcuts list) and Esc, so those are the hints; `pc.js` stops an Escape that closes the `?` list from also opening the Menu.
- **Research node buttons (fixed, PC-17).** `game.py` used to redraw the research node buttons (and whether each is affordable) only when something called `update_research_display()`, so on both layouts the first node stayed greyed out as Iron accumulated; `pc.js` used to patch it for Desktop only. Now `tick()` calls `update_research_node_flags()`, which walks `_research_node_buttons` (the buy buttons of the available nodes, recorded when the list is built) and sets only each button's `disabled` flag from the current Iron; the rows are never rebuilt per tick, because replacing the buttons every 100 ms would swallow a click between mousedown and mouseup. The `pc.js` workaround is removed.
- **Layout notes.** `pc.css` clears the ad-bar body padding, hides the mobile HUD, lifts the achievement toast clear of the ad strip, and at 1280px wide or less drops the chip labels and shrinks the hero; at 780px tall or less the planet shrinks and the terraform legend is hidden.
- **Known limits.** The stage scrolls on its own on the tallest worlds (gas giants with Sky Cities, many unlocked cross-summaries) at 1024x700. The "Other Worlds (Governed)" list opens within a 38vh scroll box. Scripted play only (mine, buy, research to Far Bodies, travel to Mars, Overview, Governor), no full human playthrough or prestige / epilogue run in the Desktop layout.

## Round-3 batch (2026-10-08: A-22, A-24, A-25, A-26, A-30, A-31, PC-17)

All new state is optional in the save and defensively typed on load (`_load_session_additions()`); nothing changes a cost, a cap or an unlock. Tests 722 -> 790 (`tests/test_round3.py`; the shared `game_env` fixture now starts with the two gameplay switches below OFF in `localStorage` so every older test keeps its exact numbers, and the new tests switch them on). Achievements 24 -> 26 (`in_rhythm`, `chain_reactor`).

- **A-26 rhythm streak.** Manual clicks within `STREAK_WINDOW_TICKS` (15 ticks, 1.5 s of game time) of each other build `click_streak`; every 10 adds +1% to a manual click's yield, capped at +5% (`_streak_click()`, called from `_mine`). Automation is never touched. Shown as plain text in `#click-streak` (hidden under 3 clicks, no moving meter, so Reduce motion needs no special case). Only `best_click_streak` is saved (lifetime; 40 earns In Rhythm). Off switch: Settings "Rhythm bonus" (`localStorage["sol-click-streak"]`, read by `game.py` through `_setting_on()`).
- **A-25 chain reactions.** `CHAINS` (7: Spin-Up, Whistle-Stop, Closed Loop, Mars Landing, Spread Thin, Skyward, Scholar's Dash). Every player action goes through `_player_action(kind, planet)` (mine/gen/rec/route/sky from the `_buy_*` and `_mine` functions, travel from `_travel_to`, research from `research_node_action`; the Governor never calls it) into `_action_log`; a chain fires when its steps appear in order (not necessarily adjacent) among the last `CHAIN_WINDOW_TICKS` (600 = 60 s) with the newest action as its last step (`_chain_match()`; a step's world is a name, None or "*" = distinct from the other "*" steps). Reward `(40 + 4 per generator on that world) * yield multiplier` of that world's resource, toast via `_display_toast()`; each chain has a `CHAIN_COOLDOWN_TICKS` (1200) cooldown, so the page is a collection, not a farm. `chain_counts` (id -> times fired, for life) is the only saved part; prestige clears the live log and cooldowns, not the counts. Page: toolbar button / Desktop window "Chain Reactions (n/7)", a hint card per unfound chain, the recipe once found. Off switch: Settings "Chain reaction bonuses" (`sol-chain-bonus`). Collector achievement Chain Reactor = all seven found.
- **A-31 trophy shelf.** `recent_trophies` (newest last, up to 12 saved) is appended in `_check_new_achievements_for_toast()`; `#trophy-shelf` shows the 5 newest that are still earned, as labelled badges (`role="list"`/`listitem`, name as text, glyph `aria-hidden`). Only a badge earned this session carries `trophy-badge--new` (a CSS glow, off via Settings "Glow on a newly earned trophy" -> `html[data-trophy-flourish="off"]`, and under Reduce motion / `prefers-reduced-motion`). A save from before the shelf seeds it from the achievements already earned.
- **A-30 splits.** `run_splits` (world or "full" -> game ticks since this run began, recorded when a research level unlocks its worlds and when the whole system is terraformed) and `pb_splits` (the splits of the fastest completed run, replaced only when a run beats `best_run_ticks`); prestige clears `run_splits` only. Page "Speedrun splits" with signed text deltas (`+30s`, `-20s`, `same as best`), reachable like the others but hidden by CSS (`html:not([data-show-timing="on"]) #splits-toggle-button`) until Settings "Show timing" is on (`sol-show-timing`, off by default).
- **A-22 Governor mood.** `planet_state[...]["player_actions"]` counts a world's hand-mined clicks and purchases (not travel, research or Governor buys; reset with the world and the prestige); `governor_mood()` picks one of 3 lines per personality (Global follows the global priority) by 0-9 / 10-99 / 100+ actions; shown as "Mood: ..." on each Governor Report card.
- **A-24.** Build Plan has "Copy as spreadsheet text": `build_plan_tsv()` (header `Step\tWhat\tDone`, tabs and line breaks in a step flattened) to the clipboard, falling back (also on an async clipboard rejection) to a readonly textarea plus a status line.
- **Desktop reachability.** `pc-config.json`: `chains-panel` and `splits-panel` are windows opened from the Menu (Game and Records groups); `#trophy-shelf` and `#click-streak` sit in the stagebar strip; the four new Settings checkboxes live in the existing Settings window; the copy button is inside the Build Plan window. `settings.js` gained a `TOGGLES` table for the four switches (Reset to Default restores them); no new JS file.
- **Not built from the Round-3 SOL list** (larger or needs a design call): A-2 anomalies + forecast, A-3/A-4 prestige mutators, A-5/A-6 Mission Board, A-7/A-8 Doctrines, A-9/A-10 Observatory, A-11/A-12 Scarcity Run (needs the shared seeded-daily pattern), A-13/A-14 Megaprojects, A-15/A-16 Rival Colonies, A-17/A-18 Time Capsules, A-19/A-20 Codex, A-21 prestige Eras, A-23 Blueprint Swap (needs A-3/A-7), A-27/A-28 Stress Test, A-29 Ghost Run (needs A-23).

## Pause, fast-forward and pause-when-hidden (W-2, Z-28, 2026-10-08)
- A Pause / 1x / 2x / 4x control (`#time-controls`, built by `shared/time-controls.js`) sits under the toolbar (Desktop: first item in the stage bar). Keys: Space pauses or resumes (only when no button, link or tile has the focus), `[` slower, `]` faster; both are in the `?` help and the Desktop hint bar.
- `setup()` ends with `_start_tick_loop()`: it hands `tick` to `NoyvjTime.start("sol", tick, TICK_INTERVAL_MS)`. Speed only changes how often `tick()` is called (100 ms, 50 ms, 25 ms); the tick body never reads the speed and a test pins that only `_start_tick_loop` mentions `NoyvjTime`. Paused means no tick runs and no time is banked (no catch-up burst on resume). Clicks, buying and travel are player actions, not ticks, so they still work while paused. Without the shared script (or in the fake-js tests) the old `setInterval` is used.
- Away report: A5's "while you were away" report counts game ticks (`TICK_INTERVAL_MS` each), not wall-clock time. Hidden or paused time adds nothing to it; at 4x it reports more game time per real second. Tested in `tests/test_time_controls.py`.
- Setting: "Pause when this tab is hidden" (`#pause-hidden-checkbox`, `localStorage` `sol-pause-hidden` on/off, default on, wired by `shared/pause-hidden.js`, reset by Reset to Default). Hidden = the controller is held with the reason "hidden" (the player's own pause or speed is kept); on return a one-line note says "Paused while the tab was hidden". Off keeps the old behaviour (the browser throttles the timer but it keeps running).
- Wiring pass 2026-10-08: the Epilogue panel and the Stats & Share panel carry the shared Copy result button (`copy_result_fields()` in game.py feeds `shared/copy-result.js`; mounted by the inline script at the end of index.html), earned achievement cards get a Share button (`shared/achievement-share.js`), the head carries the Open Graph/Twitter block and JSON-LD from `share/meta/sol.html` and `share/jsonld/sol.json`, and the How to Play panel ends with a Credits link. Pins: `tests/test_wiring_oct8.py`.

## Round-4 batch (2026-10-10: FY-53, A-2, A-3/A-4, A-5/A-6, A-7/A-8, A-13/A-14, A-19/A-20, A-21, A-23, A-27/A-28, FY-49, FY-50)

Every new save key is optional, written only when non-default and cleaned on load (`_load_session_additions()`); an old save loads unchanged. Tests 815 -> 950 (`tests/test_goals.py`, `test_mutators.py`, `test_anomalies.py`, `test_charter.py`, `test_codex.py`, `test_eras.py`, `test_doctrines.py`, `test_blueprint.py`, `test_stress.py`, `test_round4_achievements.py`); achievements 26 -> 30; the changelog test's cap rose from 30 to 60 entries. Live-checked in the browser pane at 1440x900 (Desktop) and 360x740 (Classic): goals, anomaly strip, Charter, Doctrines, Blueprint, stress test and eras render with no layout overflow and no console errors apart from the sandbox's own service-worker registration failure. Not built from the Round-3 SOL list: A-9/A-10 Observatory, A-11/A-12 Scarcity Run (needs the backend leaderboard and shared daily seed), A-15/A-16 Rival Colonies (needs A-9), A-17/A-18 Time Capsules, A-29 Ghost Run. The `game_env` fixture now also switches Timed anomalies off (so older tests' numbers hold) and its fake document has a `documentElement`. New game code lives in one block of `game.py` headed "Round-4 batch", just above `_start_tick_loop()`.

- **FY-53 goals panel.** `goals_list()` is the ordered queue (first miner, first Recycler, Near Bodies research, visit Mars and the Moon, Far Bodies research, first trade route, then a "Terraform X to 100%" and Sky City goal per world that is available); everything is derived from existing state, nothing new is saved. `goals_json()` is read by `shared/goals-panel.js` (mounted at the end of `index.html`, `#goals`, once a second via `_refresh_goals_panel()` from `tick()` and on `_full_render()`). Settings has a "Show the three goals panel" checkbox (`#goals-checkbox`, the shared panel keeps its own `noyvj-goals:sol` key; Reset to Default turns it back on). Desktop: `#goals` sits in the stage strip as one row of three (`pc.css`), rewards hidden under 860px of height. Tests: `tests/test_goals.py`.
- **A-3 / A-4 / FY-49 prestige mutators.** Four opt-in rule twists in `MUTATORS` (Thin Atmosphere: ecology decays 40% faster; One-Way Trade: trade routes restore half as much ecology; Blind Governor: the Governor ignores priority and personalities, alternates its buys and spends at most 25% of a world's stock; Costly Machinery: Auto-Miners and Recyclers cost 15% more). Pick 0 to 3 in the Prestige Tree panel (`mutators_next`, which now opens as soon as a prestige is available); the picks lock in as `mutators_run` the moment the next run starts and each twist pays +1 Prestige Point when you prestige out of that run, so a twist cannot be dropped mid-run to keep the reward. All four are plain multipliers read in `_simulate_planet`, `_incoming_trade_restore`, `governor_step` and `_machinery_discount`; none is luck and none can lock a world. A-4: a glyph per active twist next to the title badge (`Prestige 2 ☁ ⚙`, the full names in its tooltip), a "Run rules:" line on the Stats & Share card text and in the Copy result stats. Save keys `mutators_next` / `mutators_run` (id lists, unknown ids dropped, capped at 3). Owner balance call (FY-49): every twist is worth exactly 1 point. Tests: `tests/test_mutators.py`.
- **A-2 / FY-50 System Anomalies.** Fixed schedule on the run clock (`total_ticks - run_start_tick`, so a pause, a hidden tab and a new prestige run all behave): calm for `ANOMALY_FIRST_AT` (3000 ticks = 5 minutes), then one anomaly of `ANOMALY_LENGTH` (600 = 1 minute) every `ANOMALY_PERIOD` (3000), always the same six in the same order, boon / strain alternating: Comet Pass (+25% Auto-Miner output), Solar Flare (ecology decay x1.5), Meteor Shower (hand-mined clicks x2), Magnetic Storm (trade restore x0.5), Clear Skies (Recycler restore x1.5), Dust Cloud (terraforming at half speed, never backwards). `anomaly_schedule(run_ticks)` is a pure function; `tick()` calls `_update_anomaly()` first, which sets `_active_anomaly` for that tick, and the effects are plain `anomaly_factor(key)` multipliers in `_simulate_planet`, `_incoming_trade_restore`, `terraform_rate` and `_mine`. The forecast is `#anomaly-strip` (text only, `role="status"`, boon / strain also written as words and marked by border style, never colour alone): "Next anomaly: Comet Pass in 4:12 (a boon: ... for 1:00)" or "Boon: Comet Pass for 0:41 more, ...". Off: Settings "Timed anomalies" (`localStorage["sol-anomalies"]`, default on; the test fixture sets it off so older numbers hold); not applied in the post-win sandbox. Only `anomalies_seen` (lifetime collection of ids) is saved, when non-empty. Desktop: the strip sits in the stage strip. Tests: `tests/test_anomalies.py`.
- **A-5 / A-6 Charter and Mission Board.** One new panel, "Charter" (`#charter-toggle-button` / `#charter-panel`, toolbar and Desktop window opened from the Menu "Game" group), holds the Mission Board, the megaprojects below, the stamp tally and "Anomalies seen n/6". `MISSIONS` (15, each with world, target and a `measure()` read live off state: Earth crew, Iron hoard, Recyclers-only terraform, Mars routes, Moon and Venus terraform conditions, Belt bank and routes, Pluto, two Sky City ones, and two world-spanning ones) post three at a time (`mission_slots`); `_check_missions()` (every tick) stamps a finished mission automatically, toasts it and posts the next, offered in catalogue order with worlds you can reach first. A stamp (`mission_stamps`, lifetime, never reset by a prestige) is a permanent +1% yield on its world (+0.5% everywhere for the "all" missions), applied in `_simulate_planet` and `_mine` through `stamp_bonus(planet)` and shown as "Charter stamps: ★★ (+2% yield)" on the world's Overview card. A-6: "Swap for another mission" costs 100 of whichever resource pile is biggest right now (`reroll_source()`), moves to the next mission in catalogue order (no randomness) and is disabled with the need written out when nothing is banked. The panel is built once per structure signature and updated in place (progress bars, button text), so a click is never swallowed by a rebuild. Save keys `mission_stamps`, `mission_slots` (known ids only, no duplicates, stamped ids never on the board, at most 3).
- **A-13 / A-14 Megaprojects.** `MEGAPROJECTS`: Orbital Mirror (terraforming +25% everywhere), Ring Habitat (Sky Cities count double, via `sky_city_bonus_per_city()` which the simulation and the Sky City readout both use), Dyson Sail (Auto-Miners +20%), Deep Core Tap (Recyclers restore +50%). Each needs 3 to 5 lines of banked resources from different worlds (4000 Iron + 2500 Water Ice + 1500 Platinum for the Mirror, and so on); "Send what you can" moves what that world has banked (never over the line, only from a world you can reach; lines for locked worlds say "reach X first"), the ring (a conic-gradient span with the percent as text and an `aria-label`, in the Charter panel and as a small row on the Overview) fills by whichever worlds have contributed. Perks and progress are per run (a prestige clears `megaproject_progress` and `megaprojects_built`); `megaprojects_all_ever` (lifetime) keeps the secret epilogue paragraph about the four great works once all four stood in one run. Save keys `megaproject_progress` (id -> planet -> amount, clamped to the need), `megaprojects_built`, `megaprojects_all_ever`, all only when non-default. Tests: `tests/test_charter.py` (26).
- **A-19 / A-20 hidden Codex.** `WORLD_NOTES` (a plain line plus one odd trailing sentence for the seven worlds other than Earth) shows as a note on each Overview card, with one line at the top of the Overview saying some notes end oddly. `CLUES` (seven, one per world) are live conditions: 13 Auto-Miners on one world (Moon), 7 trade routes delivering to Earth (Mars), Venus finishing terraforming after every other world (watched in `_check_codex()` through the transient `_terraform_done_seen`; a loaded save counts finished worlds as earlier), one Recycler fewer than 5+ Auto-Miners on the Belt, Pluto at 0% ecology with machines, 3 Sky Cities and no Recycler over Jupiter's Moons, 10,000 Methane banked on Saturn's Moons. Finding one records a silly curio line (`codex_found`, lifetime, saved when non-empty) and toasts it. The Codex section of the Charter and its "n of 7 clues found" count do not exist until the first clue is found; after that each open clue shows its world's odd sentence and a "Show a hint" button (hints are never pushed; `_codex_hints` is per session). Tests: `tests/test_codex.py`.
- **Round-4 collector achievements** (26 -> 30): Codex Keeper (all 7 clues), Weather Watcher (all 6 anomalies seen), Charter Member (5 stamps, with progress), The Great Works (all four megaprojects in one run, `megaprojects_all_ever`). All lifetime, so a prestige never un-earns them. Tests: `tests/test_round4_achievements.py`.
- **A-21 prestige Eras.** `ERAS` names the level bands (Pioneer 0, Steward 1-2, Architect 3-5, Custodian 6+) and `era_for_level()` picks one; the title badge reads "Architect · Prestige 3" (the level counter stays, now with a name). `_apply_era()` (from `update_win_display()`) sets `data-era` on `<html>` and fills `#era-tagline` (one line under the title, Desktop: in the stage strip). From Steward on, `style.css` (A-21 block, before the Y11b region, light theme untouched because only the starfield nebula is tinted and the dim stars quieted) hue-shifts `.space-bg-nebula` and tints the badge border: all static, no animation or transition, so Reduce motion needs no special case. Settings "Era look" (`sol-era-look`, default on, `html[data-era-look]`, restored by Reset to Default) turns the colour shift and the tagline off; the name stays in the badge either way. The settings script avoids the word "theme" on purpose (a light-theme test pins that). No rule or number changes. Tests: `tests/test_eras.py`.
- **A-7 / A-8 Governor Doctrines.** A "Doctrines" panel (`#doctrine-toggle-button` / `#doctrine-panel`, hidden until the Near Bodies node Automation Basics is researched; Desktop: window in the Menu's Game group) edits up to 3 per-world if/then rules (5 with the new tier-2 Prestige Tree node Standing Orders, 2 points). A rule is a world, a condition (ecology below 30/50/70%, or the world's stock above 500/2,000/5,000) and an action (pause the Governor's own buying, buy a Recycler, buy an Auto-Miner, ship relief: +10% ecology for 100 of the biggest other pile with a 200-tick cooldown, or start a trade route to the lowest-ecology world). `governor_step()` calls `_doctrine_step(planet)` for each governed world before its normal buying; rules run in order, a holding pause rule makes the Governor skip its own buy that tick, the rest buy or ship only when affordable (so a rule never overspends), nothing runs in the sandbox, and a world you are standing on is never governed. The Governor Report card of each world gains "Doctrine fired 12s ago: On Mars, if ecology is below 30%, buy a Recycler." (or "no rule has fired here yet."). A-8: "Try for 30 ticks" (`doctrine_dry_run()`) snapshots planet_state, the Governor and lifetime counters, runs 30 ticks of simulate plus governor with the DOM refresh calls skipped (`_dry_run`), restores everything in a `finally`, and prints "Over the next 30 ticks (3 seconds) these rules would have fired N times: rule 1 x4. Nothing was changed." Rules (`doctrine_rules`, saved when non-empty, each field validated against the allowed levels and ids, absolute cap 5) survive a prestige but sleep until Automation Basics is researched again; per-rule fire counts and the last-fired line are per session. Tests: `tests/test_doctrines.py` (22).
- **A-23 Blueprint Swap.** The Build Plan panel (so also its Desktop window) gains "Make a blueprint code" (`SOLPLAN1:` + base64 JSON through `shared/export_progress.py`: the step texts, never the ticks, the Doctrine rules and the next-run mutator picks; copied to the clipboard with the readonly box as the fallback) and a paste box that loads a code as a faint "ghost" list under the plan (`#blueprint-ghost`). Importing changes nothing; each part is adopted with its own button: add one step or every step (never a duplicate, never past 30), add the rules (never a duplicate, never past the absolute cap of 5; the Doctrine limit still decides how many run), or use the mutator picks. `parse_blueprint()` never raises and cleans everything it reads (length caps, known ids, the same rule and mutator validators the save uses); an empty or foreign code gets a one-line message. The ghost and the codes are not saved and no backend is involved. Tests: `tests/test_blueprint.py`.
- **A-27 / A-28 Ecology Stress Test.** A section of the Charter, open once every world is terraformed (otherwise a disabled button saying so). `run_stress_test()` uses `_run_headless()` (the same copy-run-restore machinery as the Doctrine dry run, now shared: snapshot of planet_state, Governor and lifetime counters, total_ticks, current_planet, sandbox flag and the live anomaly; DOM never touched; everything put back in a `finally`): 1800 ticks (3 minutes of game time) with nobody standing anywhere (`current_planet` = "Deep space", so the Governor and Doctrines run all eight worlds, sandbox off) under a three-phase cascade (`STRESS_PHASES`: ecology decay x1.5, then x2 with trade restore halved, then x2.5, applied through `_stress_factors` inside `anomaly_factor()`). Score = the worst moment of the all-world average ecology minus the line (`STRESS_LINE` 40%), shown as "+12.3 points from the line" with "held the line" / "dipped under the line"; the best margin is the only thing saved (`stress_best_margin`, lifetime, validated as a finite number within -100..100). A-28: one monospace strip per world, 12 blocks (the lowest ecology in each 15 seconds), height by level plus "!" under 10% and "x" at 0% and the lowest percentage as text, with a legend sentence, so nothing relies on colour. No clicking, achievements, boards or save data are touched. Tests: `tests/test_stress.py` (11).

## Round-5 batch (2026-10-11: A-9/A-10, A-15/A-16, A-17/A-18)

Every new save key is optional, written only when non-default and cleaned on load; an old save loads unchanged. All new game code lives in one block of `game.py` headed "Round-5 batch", just above `_start_tick_loop()`. Not built from the SOL list: A-11/A-12 Scarcity Run (needs the backend leaderboard and a shared daily-seed pattern that does not exist yet) and A-29 Ghost Run (needs a recording of terraform percent every 25 ticks, i.e. replay infrastructure).

- **A-9 / A-10 Observatory.** Panel "Observatory" (`#observatory-toggle-button` / `#observatory-panel`, toolbar and a Desktop window in the Menu's Game group). Survey Data (`survey_data`, lifetime) comes from a prestige (2), a Charter stamp (1) and a Codex clue (1); each region of the fixed `CHART` (4 Lagrange Points and 4 rogue comets, costs 1,1,2,2,3,3,4,4, alternating comet / point, no randomness) is uncovered in order by `survey_region()` (`chart_revealed`, lifetime). Masked regions say only "Unmapped region N", so nothing leaks. Buildings have no slot limit in SOL, so the spec's "bonus building slots" became a **relay**: claiming an open Lagrange Point (`claim_point()`, 200 of the biggest pile through `_pile_source()`, the same payer the mission swap uses) adds +1% yield on every world for good (`relay_bonus()`, folded into `stamp_bonus()`, so clicks and automation both get it). `point_claims` (id -> "yours") is lifetime. Comets (A-10): an uncovered comet not yet caught this run is "overhead" as `#comet-strip`, a real `<button>` in the stage strip on both pages (the spec said "on the Overview"; a strip at the top is reachable from every screen and the Overview panel is closed by default). It is bright for 900 ticks, fading until 1800, then faint, and never goes away or loses value (text states bright / fading / faint, so nothing relies on motion or colour; the one CSS transition is covered by the Reduce motion override). `catch_comet()` pays every world you have `max(150 x rank, 60 s of that world's output)` of its own resource, once per comet per run (`comets_caught_run`, cleared by a prestige; `comets_caught_total` is lifetime). Achievements 30 -> 32: Star Cartographer (whole chart, progress n/8) and Comet Catcher (4 catches). Save keys `survey_data`, `chart_revealed`, `point_claims`, `comets_caught_run`, `comets_caught_total`. Tests: `tests/test_observatory.py`.
- **A-15 / A-16 Rival Colonies.** Three non-hostile corporations (`RIVALS`: Helios Combine, Ceres Freight Guild, Outer Reach Syndicate) each already hold one of the four Lagrange Points (`CHART` entries carry `rival`; the first point, Harbour Light, is open) the moment the Observatory uncovers it, so rivals only exist for a player who chose to survey that far. A rival-held point is state "rival" (the default for a point with a rival; saved states are only "yours" and "partner", and "partner" is dropped on load for a point with no rival). `rival_pressure(planet)` = `RIVAL_PRESSURE_PER_POINT` (8%) per rival-held uncovered point, at most three, and it multiplies `_incoming_trade_restore()` by `1 - pressure`, so trade routes restore that much less ecology; a world with a Focus (`_specialization()`, the Output or Stability choice from the Overview) is never pressured, nothing else is touched, and it is off in the post-win sandbox and by Settings "Rival colonies" (`sol-rivals`, default on; `rivals-checkbox` in `settings.js` TOGGLES, restored by Reset to Default). The player may ignore it (nothing changes on its own, no timers), **share** the point (`partner_point()`, 300 of the biggest pile: pressure from that point ends, half a relay, +0.5% yield) or **take it over** (`contest_point()`, 800 from a rival or 500 from a partner: a full relay), all through the same biggest-pile payer as claiming (`_pay()`). `relay_bonus()` is 1% per "yours" point plus 0.5% per "partner" point. The Observatory panel gains a Rival colonies section (names only for rivals already met, what each holds, a plain pressure sentence naming the worlds a Focus already protects) and each world's Overview card says "Rival pressure: trade restores 8% less" while it applies. A-16: `RUMORS` (12 one-line lines: meeting each rival, sharing, taking over, and each rival's "record" line when its home world, Mars / the Belt / Jupiter's moons, finishes terraforming) are noted once each into the captain's log as `rumor:<id>` (`story_line()` prefixes "Ticker: "; never when rivals are off), and `render_story_log()` keeps them out of the headline "Captain's log:" line. They change no number (a test pins it). Achievement Relay Network (all four points held or shared; 32 -> 33). Tests: `tests/test_rivals.py`.
- **A-17 / A-18 Time Capsules.** Panel "Time Capsules" (`#capsules-toggle-button` / `#capsules-panel`, toolbar and a Desktop window in the Menu's Game group). `freeze_capsule(name)` keeps up to `CAPSULE_MAX` (3) named copies of every world (`planet_state` deep-copied, the open worlds, the game tick and prestige level, plus the few numbers shown on the card: `capsule_metrics()` = average terraform, average ecology, machines, banked). Capsules live in this browser only (`localStorage["sol-capsules-v1"]`, JSON, written by `_save_capsules()` and read back by `_load_capsules()` in `setup()`), **never in the save code**, because a save travels between devices and three copies of every world would triple its size; `_clean_capsule()` validates every field on read (ids and ticks non-negative ints, every number finite and non-negative, trade routes only to real worlds, anything missing falls back to a fresh world, duplicates and extras dropped, never raises). A-17 branch: `branch_from_capsule(capsule, ticks)` swaps the capsule's worlds into the live dicts, runs `_run_headless(ticks, all_governed=True)` (the copy-run-restore machinery shared with the Doctrine dry run and the Stress Test: nobody standing anywhere, so the Governor and Doctrines run every world; DOM, lifetime counters, anomalies and achievements never touched) and puts the live game back in a `finally`, so even an exception leaves nothing changed (tested by making the Governor raise). It uses your current research, Doctrines and perks, which the panel says. "Replay 3 minutes without you" prints the change in terraform, ecology, machines and banked stock over `CAPSULE_BRANCH_TICKS` (1800). A-18 "Compare with now" (`capsule_diff()`) prints your change since the capsule and, when you have played at most `CAPSULE_DIFF_CAP` (3000 = 5 minutes) since, replays exactly that long from the capsule and adds the gap (you minus the Governor alone); a capsule from another prestige level, or frozen at a later tick (a different save), says it cannot be compared. About 0.4 s in Pyodide for a replay. The name field keeps a half-typed name across panel rebuilds and clears after a freeze. Tests: `tests/test_capsules.py`.
- **Desktop and pages.** New ids on both pages: `observatory-toggle-button`, `observatory-panel`, `comet-strip`, `capsules-toggle-button`, `capsules-panel`, `rivals-checkbox`; `pc-config.json` gained the two windows (Menu, Game group) and `#comet-strip` in the stage strip; `pc.html` regenerated for SOL only. New files fetched at load: none. Tests 950 -> 1024 (new files `test_observatory.py`, `test_rivals.py`, `test_capsules.py`); achievements 30 -> 33; `changelog.json` has four new 2026-10-11 entries.

## Round-6 batch (2026-10-11: A-11/A-12 Scarcity Run, A-29 Ghost Run)

Every new save key is optional, written only when non-default and cleaned on load; an old save loads unchanged. Pure helpers (dates, word lists, the day's rules, record and recording validators) live in a new `challenges.py` (written into Pyodide's filesystem by `index.html` next to `game.py`, together with `shared/seed.py`, whose `Rng` it uses); the simulation and panels are one block of `game.py` headed "Round-6 batch", just above `_start_tick_loop()`. Tests 1024 -> 1096 (`tests/test_scarcity.py`, `tests/test_ghost.py`); achievements 33 -> 36 (cap test is 40); `changelog.json` has two new entries. New files fetched at load: `games/sol/challenges.py` and `shared/seed.py`. Live-checked in headless Chromium at 1440x900 and 360x740 on both pages (panel, calendar, run, finish, leave, ghost strip and split track); the only console error was the sandbox's own blocked ad script.

- **A-11 Scarcity Run.** One challenge per UTC date, made from the date text alone (`challenges.make_spec(date, attempt)`; the view passes today's date in through `_today_utc()`, the engine never reads the clock). Worlds are Earth, the Moon and Mars after the Near Bodies research; a day picks 2 or 3 of them to terraform to 30-60%, an ecology decay factor (1.5-3x), a machine cost factor (2-4x), a yield factor per world (the resource mix: always one thin pile and one rich), a starting loadout per world, and terraforming runs 4x faster (so a day is decided by how fast you stabilise ecology, not by waiting; a first draft with normal-speed terraforming made the reference plan equal to the theoretical minimum, so nobody could beat it). **Played on a copy:** `start_scarcity_run()` stashes the exact dict `get_state()` returns, swaps in a fresh game (`_PRISTINE_JSON`, taken just before `setup()`) with the day's loadout through `deserialize_state()`, and `leave_scarcity_run()` loads the stash back; while a run is on `get_state()` returns the stash plus the run records, so the save widget and autosave never see the run. Inside a run: no achievements, story log, leaderboard report, prestige, capsules, stats codes or compare (guards in `_check_new_achievements_for_toast`, `_report_full_completion`, `_prestige_available`, the capsule functions, the stats-code functions); timed anomalies, the rhythm bonus, chain bonuses and rivals are off through `_setting_on()` so every player has the same rules; loading a save ends a run (the stash is restored first, then the save is loaded over it). Tests pin a byte-identical `get_state()` before, during and after (with a rich mid-campaign state) and after a restart. **Fairness:** `scarcity_spec(date)` accepts the first attempt whose reference plan (`_scarcity_headless`: the Governor on its Ecology setting with a full budget, nobody standing anywhere, plus a hand clicking 3 times a second on the world furthest from the goal, so a collapsed world is never a dead end) reaches the goal within `SCARCITY_BOUND_TICKS` (9000) and not under `SCARCITY_MIN_TICKS`; a stalled candidate is cut off early. Its time is the par. A test proves 300 consecutive dates (all succeed, nearly always on the first candidate); the median par is about 1.4 times the theoretical minimum, so a hand-played run can beat it. **Result:** the goal is checked each tick; the time is in game ticks (never wall-clock) and kept in `scarcity_days` (date -> `{"ticks", "tries", "under_par"?}`, best time kept, validated entry by entry by `challenges.clean_days`, the only new save key, written only when non-empty). No streak exists anywhere: the panel shows a tally ("days played: n of the m open") and a small symbol grid (played, under par, not played, with a legend), any date from 2026-10-01 up to today is playable from a month calendar, and a missed day costs nothing. A run is not saved: closing the page ends it (the panel says so). **Leaderboard hook:** `challenges.leaderboard_entry()` / `scarcity_leaderboard_entry(date)` shape the entry a future opt-in board `sol-scarcity-daily` would take; nothing is sent (no backend change in this pass).
- **A-12 seed words.** `challenges.seed_words(date)` gives a short pronounceable triple such as `amber-orbit-7` (40 adjectives x 40 nouns x 8 digits as plain data, indexed through a fixed shuffle of 0..12799 by the date's ordinal, so two dates less than 12,800 days apart never share one; tested over 300 dates and the whole cycle). Shown on the Scarcity Run card, on the strip while a run is on, and on the Stats & Share card ("Today's seed: ..." plus today's result when there is one; while a run is on the card describes the run instead). The Copy result fields do the same.
- **A-29 Ghost Run.** A recording is the average terraform percent (tenths of a point) sampled every 25 ticks (`challenges.GHOST_STEP`). Normal play records the run automatically (`_ghost_tick()`, whole-system average, on the run clock so a prestige starts a fresh one); the in-progress samples are written to `localStorage["sol-ghost-live-v1"]` every 8 samples and picked up again after a load if they belong to the same run (a run joined mid-way, or with a gap, is marked partial and can never become the best); at the moment a whole-system run finishes (`_note_full_completion`) the recording is kept as `sol-ghost-pb-v1` **only when it is a new fastest playthrough**. Everything is local: never in the save code, validated whole-or-dropped on read (`challenges.clean_recording`). The existing Speedrun splits panel (hidden until Settings "Show timing" is on) gained a Ghost Run section: a switch (`sol-ghost-on`), your best recording's time and the split track (the latest 12 checkpoints, each "0:25: you 12.4%, ghost 11.9%, +0.5 (ahead)", plus a summary of checkpoints ahead/behind/level); `update_splits_display()` now builds the panel once and updates rows in place so the switch is never swallowed by a rebuild. `#ghost-strip` (a stage-strip line on both pages) shows the current lead or lag in words ("+0.5 points ahead", "-0.5 points behind", "level (+0.0)"). In a Scarcity Run you can choose a ghost before starting: your best recording for that day (`sol-ghost-daily-v1`, one per date, kept only when faster, 40 days kept), the reference plan (par), or a friend's blueprint: a pasted `SOLPLAN1:` code (Blueprint Swap) is played by the same reference plan on that day with the code's Doctrines and rule twists (`make_friend_ghost()`; a code with only build-plan steps is refused kindly, since steps are free text and cannot be played). The run's own track is in the Scarcity panel. The campaign recording pauses during a run and resumes after. No colour carries any meaning: every lead is "+"/"-" text plus the words ahead/behind/level.
- **Desktop and pages.** New ids on both pages: `scarcity-toggle-button`, `scarcity-panel`, `scarcity-strip`, `scarcity-strip-text`, `scarcity-leave-button`, `ghost-strip`; `pc-config.json` has the Scarcity Run window (Menu, Game group) and both strips in the stage strip; `pc.html` regenerated for SOL only; Esc/`?` shortcuts list the panel. Achievements: Scarcity Survivor (any day finished), Outplayed the Governor (any day under par), Seven Scarce Days (seven different days, any order; progress n/7), all derived from `scarcity_days`, so a prestige never un-earns them.

## Shared daily record (Z-5b, 2026-10-12)
Finishing TODAY's Scarcity Run (`_scarcity_finish`, date equal to `_today_utc()`) calls `NoyvjSeed.daily.markCompleted("sol", {text})` through `_record_shared_daily` (once per day, never for a calendar date, fails soft without `shared/seed.js` or on any error), so the hub's Today strip can list SOL's daily. The Scarcity panel itself still shows no streak. Tests: `tests/test_scarcity.py` (four new). `index.html` and `pc.html` now load `shared/seed.js` (already precached).

## Shared ghost (Z-3d3, 2026-10-12)
The Ghost Run (A-29) now also runs through `shared/ghost.py` (written to the Pyodide filesystem as `ghost.py` in `index.html`; `pc.html` regenerated). **Measure:** the average terraform percent over all worlds, one number per checkpoint (every `challenges.GHOST_STEP` = 25 ticks; "turn" in the shared wording is a checkpoint, so `ghost_sentence` writes "checkpoint"). Higher is ahead; the best run is still the fastest full playthrough. **No new storage:** the stored recordings (`sol-ghost-pb-v1`, `sol-ghost-daily-v1`, tenths of a percent at full resolution, validated by `challenges.clean_recording`) stay the source; `ghost_trace(recording)` turns any of them (the personal best, a day's best, the Governor's par, a friend's blueprint run) into a shared trace through `ghost.Recorder` (thinned to 120 numbers, cached per recording), so every older recording works with no migration and the split track keeps its full resolution. `ghost_sentence(samples, recording, label)` runs `ghost.compare` and `ghost.summary(unit=" points")` and fills `#ghost-sentence` (a visually hidden `role="status"`, in `index.html` and `pc.html`) from `_refresh_ghost_strip`; it refreshes every `GHOST_SENTENCE_EVERY` (8) checkpoints so a screen reader is not chatty, is empty when nothing is raced, and is empty (not an error) for a run longer than the shared cap of 5000 checkpoints. SOL has no chart for this, so it is words only: the visible strip and split track are unchanged. Switch: the existing "Ghost run: On/Off" button (default off) and the Scarcity "No ghost" choice hide strip and sentence alike; the stored ghost is never deleted by hiding. Tests: `tests/test_shared_ghost.py`.


## Design specs (LA-13)

Written 2026-10-22 (LA-13 design pass, batch 2). Steps: `local-ai/incoming/sol-design.txt`. Standing rules hold:
nothing timed, nothing lost, no luck needed for 100%, no audio files, saves load unchanged. Of the SOL items in this
batch only R4-SO-4 is designed; R4-SO-2 (depot) and R4-PS-26 (transfer windows) wait on one owner question (what a
transfer moves), and R4-PS-12, R4-PS-22 and R4-PS-29 are larger than one design pass (see the batch report).

### R4-SO-4: research forks (pick one of two, swap later for a small fee)
- **Rule.** Three optional fork points hang off the research tree. At each you research ONE of two upgrades; the other
  side then shows "Swap to this" for 25% of its price (rounded up), which drops the old side and takes the new one, so
  no choice is permanent and nothing is ever stuck. Forks are never required by any node and are NOT part of a level's
  Iron target, so they cannot block or slow the path to new worlds. They stay on screen after their level is done (a
  "Forks" list under the node list), so a swap is always possible.

| Fork | Opens after | Level | Price | Side A | Side B |
|---|---|---|---|---|---|
| `drills_or_machines` | Automation Basics | Near Bodies | 120 Iron | Deep Drills: +3% yield | Lean Machines: Auto-Miners and Recyclers 8% cheaper |
| `freight_or_survey` | Long-Haul Logistics | Far Bodies | 400 Iron | Freight Lanes: trade routes 10% cheaper | Survey Rigs: +3% yield |
| `fusion_paths` | Fusion Research | Far Bodies | 500 Iron | Fusion Mining: +4% yield | Fusion Fabrication: machinery 10% cheaper |

  Scale check: the ordinary nodes give +1 to +2% yield or 5% discounts for 40 to 340 Iron, so a fork is a little
  stronger than its neighbours (it costs a choice) and far below a tier's total (1,000 and 5,000 Iron). All forks
  together add at most +10% yield, against the tree's existing +25%.
- **Data.** Fork nodes are ordinary research nodes with two extra keys, `fork` (the fork id) and `fork_other` (the
  other side). They go into `RESEARCH_NODE_BY_ID` (so `research_effect`, `research_node_status`, saves and
  `_clean_researched_nodes` handle them) but NOT into `RESEARCH_NODES` (so every per-level list, the tier targets, the
  progress sum and the old-save migration stay exactly as they are).
- **Saves.** None new: fork ids are kept in `researched_nodes` like any node. `_clean_researched_nodes` also keeps at
  most one side of each fork (side A when a tampered save holds both). Old saves load unchanged.
- **Engine code.** `sol_rules.py`, directly after the line `RESEARCH_NODE_BY_ID = {node["id"]: node for node in RESEARCH_NODES}`:

```python
# R4-SO-4: research forks. At each fork the player researches one of two upgrades and may swap to the other later
# for RESEARCH_FORK_SWAP_SHARE of its price. Fork nodes are in RESEARCH_NODE_BY_ID (effects, status, saves) but not in
# RESEARCH_NODES, so no level's node list, Iron target or old-save migration changes; nothing requires a fork node.
RESEARCH_FORK_SWAP_SHARE = 0.25
RESEARCH_FORKS = [
    {"id": "drills_or_machines", "requires": "automation_basics", "tier": 0, "cost": 120,
     "sides": [("deep_drills", "Deep Drills", {"yield_pct": 3}),
               ("lean_machines", "Lean Machines", {"machinery_discount": 8})]},
    {"id": "freight_or_survey", "requires": "long_haul_logistics", "tier": 1, "cost": 400,
     "sides": [("freight_lanes", "Freight Lanes", {"route_discount": 10}),
               ("survey_rigs", "Survey Rigs", {"yield_pct": 3})]},
    {"id": "fusion_paths", "requires": "fusion_research", "tier": 1, "cost": 500,
     "sides": [("fusion_mining", "Fusion Mining", {"yield_pct": 4}),
               ("fusion_fabrication", "Fusion Fabrication", {"machinery_discount": 10})]},
]
FORK_NODES = []
for _fork in RESEARCH_FORKS:
    for _side, (_id, _name, _effects) in enumerate(_fork["sides"]):
        _node = {"id": _id, "name": _name, "cost": _fork["cost"], "requires": [_fork["requires"]],
                 "effects": dict(_effects), "tier": _fork["tier"], "fork": _fork["id"],
                 "fork_other": _fork["sides"][1 - _side][0]}
        FORK_NODES.append(_node)
        RESEARCH_NODE_BY_ID[_id] = _node
```

  `sol_econ.py` (import `RESEARCH_FORK_SWAP_SHARE` from rules), directly after `research_node_cost`:

```python
def fork_swap_cost(node):
    """R4-SO-4: the fee to swap a fork to this side (free in the sandbox)."""
    if _sandbox_active():
        return 0
    return math.ceil(node["cost"] * RESEARCH_FORK_SWAP_SHARE)
```

  `_clean_researched_nodes`: directly before its `return wanted` add (import `RESEARCH_FORKS` from rules):

```python
    for node_id in [n for n in wanted if RESEARCH_NODE_BY_ID[n].get("fork_other") in wanted]:
        node = RESEARCH_NODE_BY_ID[node_id]
        fork = next(f for f in RESEARCH_FORKS if f["id"] == node["fork"])
        if node_id != fork["sides"][0][0]:
            wanted.discard(node_id)  # R4-SO-4: a tampered save with both sides keeps side A only
```

  `sol_actions.py` `research_node_action`: directly after the line
  `earth = planet_state["Earth"]` add:

```python
    if node.get("fork_other") in researched_nodes:  # R4-SO-4: swap a fork to this side for a small fee
        fee = fork_swap_cost(node)
        if earth["resource_count"] < fee:
            return False
        earth["resource_count"] -= fee
        researched_nodes.discard(node["fork_other"])
        researched_nodes.add(node_id)
        _player_action("research", "Earth")
        return True
```

  (import `fork_swap_cost` from `sol_econ`).
- **Engine tests, NEW file `tests/test_research_forks.py`:**

```python
"""LA-13 / R4-SO-4: research forks, one side at a time, swappable for a quarter of the price."""


def _ready(game_env, node_id):
    """Researches every prerequisite of `node_id` (not the node itself) with plenty of Iron."""
    m = game_env.module
    order = []

    def visit(nid):
        if nid in order or nid in m.researched_nodes:
            return
        for req in m.RESEARCH_NODE_BY_ID[nid]["requires"]:
            visit(req)
        order.append(nid)

    for req in m.RESEARCH_NODE_BY_ID[node_id]["requires"]:
        visit(req)
    for nid in order:
        game_env.earth["resource_count"] = 100_000
        assert m.research_node_action(nid) is True


def test_forks_are_not_in_any_level(game_env):
    m = game_env.module
    assert [t["target"] for t in m.RESEARCH_TIERS] == [1000, 5000]
    assert not any(n.get("fork") for n in m.RESEARCH_NODES)
    assert len(m.FORK_NODES) == 6 and all(n["id"] in m.RESEARCH_NODE_BY_ID for n in m.FORK_NODES)


def test_choose_one_side_then_swap_for_a_quarter(game_env):
    m = game_env.module
    _ready(game_env, "deep_drills")
    game_env.earth["resource_count"] = 120
    assert m.research_node_action("deep_drills") is True and game_env.earth["resource_count"] == 0
    assert m.research_effect("yield_pct") * 100 >= 3
    game_env.earth["resource_count"] = 29
    assert m.research_node_action("lean_machines") is False
    game_env.earth["resource_count"] = 30
    assert m.research_node_action("lean_machines") is True and game_env.earth["resource_count"] == 0
    assert "deep_drills" not in m.researched_nodes and "lean_machines" in m.researched_nodes


def test_a_fork_needs_its_branch(game_env):
    m = game_env.module
    game_env.earth["resource_count"] = 100_000
    assert m.research_node_action("deep_drills") is False


def test_a_tampered_save_keeps_one_side(game_env):
    m = game_env.module
    _ready(game_env, "deep_drills")
    kept = m._clean_researched_nodes(set(m.researched_nodes) | {"deep_drills", "lean_machines"})
    assert "deep_drills" in kept and "lean_machines" not in kept


def test_forks_survive_a_save(game_env):
    m = game_env.module
    _ready(game_env, "lean_machines")
    game_env.earth["resource_count"] = 500
    m.research_node_action("lean_machines")
    m.load_state(m.get_state())
    assert "lean_machines" in m.researched_nodes
```

- **Page** (second and third steps). `sol_econ.py`, directly after `update_research_node_list`:

```python
def update_research_fork_list():
    """R4-SO-4: every fork whose branch is researched, with Choose / Swap buttons (shown after its level too)."""
    container = document.getElementById("research-fork-list")
    container.innerHTML = ""
    earth_iron = planet_state["Earth"]["resource_count"]
    shown = 0
    for node in FORK_NODES:
        if node["requires"][0] not in researched_nodes:
            continue
        shown += 1
        owned = node["id"] in researched_nodes
        swap = node["fork_other"] in researched_nodes
        row = document.createElement("div")
        row.className = "research-node research-fork " + ("research-node--researched" if owned else "research-node--available")
        title = document.createElement("p")
        title.className = "research-node-name"
        title.innerText = node["name"] + (" (chosen)" if owned else "")
        row.appendChild(title)
        detail = document.createElement("p")
        detail.className = "research-node-detail"
        detail.innerText = _research_effect_text(node) + (" — or " + RESEARCH_NODE_BY_ID[node["fork_other"]]["name"] if not owned else "")
        row.appendChild(detail)
        if not owned:
            cost = fork_swap_cost(node) if swap else research_node_cost(node)
            button = document.createElement("button")
            button.type = "button"
            button.className = "secondary research-node-button"
            button.innerText = f"{'Swap to this' if swap else 'Choose'} ({cost} Iron)"
            button.setAttribute("data-node", node["id"])
            button.disabled = earth_iron < cost
            row.appendChild(button)
        container.appendChild(row)
    container.hidden = shown == 0
```

  (import `FORK_NODES` from rules), and `update_research_fork_list()  # R4-SO-4` as the FIRST line of
  `update_research_node_list()` (that function returns early once every tier is done, and both research redraw paths
  call it, so the forks are rebuilt on every research redraw).
  `index.html`: directly after `<div id="research-node-list" class="research-node-list"></div>` add
  `<div id="research-fork-list" class="research-node-list research-fork-list" hidden></div>`. `game.py` `setup()`:
  directly after the `research-node-list` click listener, the same line for `research-fork-list`
  (`on_research_node_click` already reads `data-node`). After a successful click the handler re-renders the research
  display, which rebuilds both lists. `tests/conftest.py` `ELEMENT_IDS`: `"research-fork-list",` after
  `"research-node-list",`. CSS (the stylesheet part that holds `.research-node-list`): `.research-fork { border-left: 3px double currentColor; padding-left: 0.5rem; }`
  (a shape cue, not a colour). Fake-DOM test: `test_the_fork_list_appears_after_its_branch` (hidden at start; after
  `_ready(game_env, "deep_drills")` and `m.update_research_display()` it is not hidden and has 2 children; clicking
  through `game_env.panel_click("research-fork-list", node="deep_drills")` with 120 Iron researches it). Browser test
  NEW `tests/test_research_forks_browser.py`: research the Automation Basics path through
  `window.pyodide.globals.get("research_node_action")` with Iron set by `load_state` (or by clicking), open the research
  panel, `#research-fork-list` is visible and has a button "Choose (120 Iron)"; `page.errors == []`.
