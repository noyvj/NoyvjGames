# Continuum — A Sustainable City Across the Ages

**Working title — rename freely.** This is the single flagship Digital Artefact for BCM114 Round 2, built around SDG 11 (Sustainable Cities and Communities), framed as speculative/fictional media (a city's story across eras) without being story-first — the mechanics carry the weight, the narrative is seasoning. Unlike the Round 1 climate quartet (many small games), this is one deep game built iteratively over several weeks. Read this whole file before starting any milestone — it's long because the system is genuinely one interconnected thing, not eight independent prototypes.

**Explicitly standalone:** no narrative or systemic connection to SOL or any other hub game. Shares only the hub's general conventions (testing, tech stack, hosting), not lore or world-state.

## Concept

The player grows a single settlement from a small tribal community into a space-age civilization, across seven eras, developing infrastructure, technology, and culture along the way — all while a visible sustainability/livability score tracks whether that growth is actually good to live inside, not just big. The throughline across every era is the same question SDG 11 asks: what makes a city sustainable and livable, not just large?

## Eras (proposed list — edit as needed)

1. **Tribal** — small settlement, subsistence, earliest social organization
2. **Agrarian** — settled agriculture, early surplus and trade
3. **Classical** — early urbanization, civic institutions, early infrastructure
4. **Medieval** — denser urban centers, guilds/specialization, early public works
5. **Industrial** — mechanization, rapid growth, the era where sustainability tension becomes most visible historically
6. **Current/Digital** — modern city systems, information infrastructure, present-day sustainability challenges
7. **Space Age** — speculative future era, off-world or post-scarcity infrastructure questions

**Build order (dev milestones) runs Tribal → Space Age**, matching play order, per your call to build the simplest era first. This is different from the earlier plan to "build current era first" — going in chronological build order instead, since it's simpler to build the foundational systems on the least complex era.

## Core systems (apply across all eras)

### 1. City simulation core
Population, resources, infrastructure, and production, scaled appropriately per era (a tribal settlement's "resources" are food/shelter/tools; a space-age city's are wildly different) but built on the same underlying simulation engine so eras share code rather than being seven separate games stitched together.

### 2. Research tree (one continuous tree spanning all eras)
A single tree that grows across the whole game — later eras unlock deeper branches rather than replacing the tree each era. Early-era research choices should have visible echoes in what's available later (e.g., an early emphasis on communal infrastructure vs. individual property might open different mid-tree branches). This is the "big research tree" you asked for — treat it as the game's backbone, not a side system.

**Design implication:** since this tree needs to span seven eras of wildly different technology (fire-keeping to space infrastructure), design it in tiers/layers from the start rather than a flat list — Claude Code should propose a tier structure at Milestone 3 (see below) before populating individual nodes, so later eras don't require retrofitting the whole tree's shape.

### 3. Sustainability/Livability score (explicit, continuous, from era 1 onward)
A visible score tracked from the very first era, not introduced later — this was your explicit choice, echoing the hope-angle metric pattern from the climate games but reframed for SDG 11 specifically (livability, equity, resource balance, resilience — not just raw growth). This score should meaningfully respond to research-tree choices and infrastructure decisions, not just tick up passively with population growth. A tribal settlement can be more "sustainable" than a poorly-planned industrial one — the score needs to reflect that kind of nuance, not just scale with city size.

### 4. Story system (mix: light ongoing logs + bigger era-transition beats)
- **Ongoing logs:** short flavor text tied to milestones within an era (a research unlock, a population threshold, a livability shift) — lightweight, non-blocking, skippable.
- **Era-transition beats:** a slightly larger narrative moment when the city crosses into a new era — this is where the "fictional media" framing gets its clearest expression, since it's the natural point to reflect on what kind of city has been built so far.
- Keep the fictional framing generic enough to be edited for tone later — better to build the system first and refine prose during a dedicated pass than to write final narrative text this early.

### 5. Save system (continuous save, revisit completed eras)
One continuous save spanning the whole arc, with the ability to revisit/replay completed eras without losing forward progress — this is more involved than a simple linear save, since it needs to preserve both "current state" and a snapshot of each completed era. Use the existing Neon/FastAPI backend for this rather than browser storage. Plan the save schema early (Milestone 2 or 3) since retrofitting a revisit-capable save system after building several eras linearly would be painful.

## Milestones

Given the multi-week scope, milestones are grouped into phases rather than a single flat list. Treat each phase as several sessions' worth of work, not one sitting.

**Phase 1 — Foundation (Tribal era + core systems)**

| # | Milestone | Status |
|---|-----------|--------|
| 1 | Core city simulation loop, Tribal era only (population, basic resources, simple production). Tests: resource/population update logic. | **DONE** |
| 2 | Sustainability/livability score system, integrated from the start, responding to Tribal-era decisions. Tests: score calculation across sample decision sequences. | **DONE** |
| 3 | Research tree engine — generic, extensible tier/layer structure first, then just enough Tribal-era nodes to prove it. Tests: unlock logic, prerequisite checking. | **DONE** |
| 4 | Save system schema — continuous-save-with-revisit structure, even though only one era exists yet. Tests: save/load round-trip, era-snapshot logic. | **DONE** |

**Phase 2 — Story & era transition framework**

| # | Milestone | Status |
|---|-----------|--------|
| 5 | Ongoing log system — lightweight, milestone-triggered flavor text, skippable. Tests: trigger conditions for log entries. | Pending |
| 6 | Era-transition beat system — generic framework reusable for all six transitions rather than rebuilt each time. Tests: transition-trigger logic. | Pending |
| 7 | First full era transition: Tribal → Agrarian, exercising the full save/revisit and transition-beat systems end to end. | Pending |

**Phase 3 — Content expansion (repeat per era)**

For each remaining era (Agrarian through Space Age), repeat this pattern:
- Era-specific city simulation additions (new resource/production types appropriate to the era)
- Research tree expansion for that era's tier
- Sustainability score adjustments (what "livable" means shifts somewhat per era — a space-age city's sustainability concerns aren't identical to a tribal settlement's, even though the same score system tracks both)
- Ongoing logs + transition beat for entering the next era
- Tests for all of the above, same standard as Phase 1

| Era | Status |
|-----|--------|
| Agrarian | Pending |
| Classical | Pending |
| Medieval | Pending |
| Industrial | Pending |
| Digital | Pending |
| Space Age | Pending |

**Phase 4 — Polish & hub integration**

| # | Milestone | Status |
|---|-----------|--------|
| — | Visual pass across all eras (large scope — consider whether one consistent visual language across all seven eras is more achievable than era-specific art) | Pending |
| — | Full playthrough testing (tribal through space age) for save/revisit integrity | Pending |
| — | Hub integration (GitHub Pages route, linked from main hub nav, added to root CLAUDE.md's Current games table) | Pending |

## Phase 1 build decisions

Concrete calls made while building Phase 1 that the doc left open. Revisit freely — these are decisions, not constraints.

- **File layout: separate engine modules, still no build step.** The tech notes ask for the simulation core, research tree and save system to be "clearly separated modules from the start," so Continuum is split into `sim.py` / `sustainability.py` / `research.py` / `save.py` with `game.py` as a thin browser layer that owns the DOM and nothing else. Every other hub game is a single `game.py`; this is the documented exception. `index.html` fetches each engine module and writes it into Pyodide's virtual filesystem before running `game.py`, which imports them normally — more fetches, still no bundler.
- **The simulation is fully deterministic.** No RNG anywhere in the season loop. Randomised events are a Phase 2/3 question; determinism is what keeps era snapshots and revisits testable.
- **Research reaches the simulation through exactly one seam.** `sim.NEUTRAL_EFFECTS` defines every modifier key the tree is allowed to touch, and `advance_season(effects)` applies them. Milestone 1 always passes the neutral dict, so the tree could be added in Milestone 3 without editing the season loop.
- **Era list confirmed as proposed** (Tribal → Agrarian → Classical → Medieval → Industrial → Digital → Space Age), and lives in `sim.ERA_ORDER`. The research tree's tier map and the save file's era-snapshot dict both key off that one list, so changing an era later means editing one constant.
- **Tribal-era shape.** Four worker roles (foragers / gatherers / crafters / keepers) and four buildings (shelter / storage pit / fire circle / knapping site). Keepers produce `knowledge`, which is the research currency for all seven eras — one currency across the whole tree rather than an era-specific one.
- **The score is built from ratios only, never counts.** Every input to `sustainability.py` is a per-capita or per-limit ratio, which is what mechanically guarantees the doc's requirement that a small well-run settlement can beat a large badly-run one. Scaling a settlement up while scaling what it needs up with it is score-neutral by construction; there is a test that asserts exactly that.
- **Four equally-weighted components** — livability, equity, resource balance, resilience — matching the doc's SDG 11 framing. Equal weighting is a judgement call, not a finding; `sustainability.COMPONENT_WEIGHTS` is the one place to revisit it.
- **Equity is bounded by the least-met need, not the average.** A settlement with grand shelters and empty stomachs scores badly on equity even where its average provision looks fine. This is what keeps equity from being a restatement of livability.
- **The score is a pure function of state.** Nothing in `sustainability.py` mutates anything or accumulates hidden history, so any era snapshot can be re-scored at any time — which is what makes Milestone 4's revisit feature cheap. The score *history* is state and lives on `CityState`.
- **Research tier structure: two tiers per era, 14 global tiers.** This is the tier proposal the doc asks for at Milestone 3. Tier numbers are global and ascending (`research.era_tiers(era)` / `research.tier_era(tier)`), so a node never gets renumbered when a later era is written. A tier opens once `TIER_UNLOCK_REQUIREMENT` (currently 2) nodes in the tier below are researched — a soft gate, so a player can specialise and still progress. Era gating sits on top: nodes from an era the settlement hasn't reached are never available.
- **Three branches spanning all seven eras** — provision / community / craft — rather than per-era categories, which is what makes "early choices echo later" mechanically real. Two mechanisms carry an emphasis forward: ordinary `prerequisites`, and `min_affinity`, which gates a node on how many nodes in a branch have been researched at all. `elders_council` is the shipped proof of the second one.
- **Node effects are always deltas.** `{"food_yield_mult": 0.2}` means +20%; the tree sums deltas onto `sim.NEUTRAL_EFFECTS` (multiplicative keys based at 1.0, additive at 0.0). Uniform aggregation, no per-key special cases as the tree grows to 14 tiers.
- **Knowledge is one currency for the whole tree**, produced by the Keeper role in the Tribal era and by whatever the equivalent is later. Research is never bought with era-specific resources.
- **The shipped tree is asserted structurally valid in tests.** `ResearchTree.validate()` catches unknown prerequisites, prerequisites from later tiers, prerequisite cycles, unknown effect keys, and tiers that don't belong to their era. Content bugs in a 14-tier tree are cheap to make and expensive to find by playing.
- **The research panel is rendered in code, not written into `index.html`.** Locked nodes are listed too, with the reason they're locked, so the tree reads as a tree rather than a queue.
- **Land health is the sustainability engine, not a decoration.** The land has a finite sustainable yield per season; harvesting past it degrades land health, which cuts every future yield, and staying under it lets the land recover. This is the mechanism that makes a small well-run settlement able to out-score a large badly-run one.
- **Saving goes through the shared hub widget, not a bespoke bridge.** This supersedes the doc's Milestone 4 wording above: the backend is still the existing FastAPI/Neon save system, but it's reached via `shared/save-widget.js` (see `planning/SAVE-BUTTON-INTEGRATION.md`), which every hub game includes unchanged. Continuum's whole per-game obligation is `get_state()` / `load_state(data)` in `game.py`; the widget never looks inside the dict, so the entire era-snapshot/revisit structure lives *inside* that one dict and needs no widget changes.
- **Save schema.** `{save_version, game, era_order, current_era, furthest_era, revisiting, current_state: {city, research}, parked_state, era_snapshots: {era: {...}}, ui}`. `current_state` is always whatever is being played; entering a revisit parks live forward progress in `parked_state` and loads the requested era's snapshot; leaving puts the parked state back. `furthest_era` never moves backwards.
- **A revisit is a look back, not a rewrite.** Leaving a revisit discards what happened during it, and a completed era's snapshot is never overwritten by a replay — the record of how an era actually went the first time is what the game's "what kind of city did you build" framing rests on. Worth reconsidering in Phase 2 if replaying an era should be able to *change* the arc.
- **The save system restores in place.** `Campaign` mutates the `CityState` and `ResearchTree` it holds rather than replacing them, so `game.py`'s module-level `state`/`tree` aliases survive a load.
- **`Campaign.advance_to_era()` exists but nothing calls it yet.** Phase 2's era-transition beat system is what will drive it; only the save-side bookkeeping (snapshot the era being left, move `furthest_era`, retarget the research tree) is built and tested now, since that's the part that would have been painful to retrofit.
- **`CITY_FIELDS` in `save.py` is an explicit list, not a `__dict__` sweep.** Adding a field to `CityState` is therefore a deliberate save-schema decision. If a future field doesn't persist, that list is the first place to look.
- **A save carries values, not shape (audit fix).** `CITY_KEYED_DICTS` in `save.py` names the three fields — `resources`, `allocation`, `buildings` — whose *key set* belongs to `sim.py` rather than to the save file. They are now restored key by key into the live dicts instead of replacing them. Before this, a save written today and loaded by a build that had since added a role, a building or a resource left the settlement with no entry for it, and the next season or render died on a `KeyError` — *after* the save widget had already reported a successful load, which is the worst version of that failure. The same pass gave the live half of the save the type-guarding `parked_state`/`era_snapshots`/`ui` already had, made `ResearchTree.restore()` tolerate a non-list, and made `game.py`'s `season_report_message()` read `last_report` with `.get()`, since a saved report can predate whatever keys the current season loop writes. This is the "old save, newer build" half of the forward compatibility the schema was designed early for; the "newer save, older build" half was already handled by the `save_version` refusal.
- **A second audit pass (three follow-up fixes left out of scope the first time).**
  - `render_research()` minted a fresh `create_proxy()`-wrapped click handler for every unresearched node's Study button on *every* render, and never destroyed the one it was replacing — a real Pyodide proxy isn't garbage-collected on its own, so this was a slow memory leak over a play session. `game.py` now tracks the live proxy per `node_id` in a module-level dict and `.destroy()`s the previous one before installing its replacement (and destroys it outright once a node no longer needs a button at all, i.e. once it's researched). Verified by a test against the fake-DOM harness — `tests/fakes.py`'s `create_proxy()` fake now attaches a real `.destroy()`/`.destroyed` onto the wrapped function so a test can assert this without a real Pyodide runtime.
  - `sim.ROLE_LABEL`/`ROLE_BLURB`/`BUILDING_LABEL`/`BUILDING_BLURB` were dead tables — `index.html` hard-coded the identical strings as static markup instead of reading them, left that way deliberately until "the moment a second era ships." Wiring them up turned out to be small and safe (index.html already showed the identical text, so the two per-role/per-building loops already in `render()` just needed two more lines each, plus new `id`s on the name/blurb elements — no visible change, verified against the pytest suite and a rendered-page text diff). Done now rather than left staged: `game.py`'s `render()` is the one place this text comes from, matching how the research panel already reads `research.BRANCH_LABEL`.
  - `Campaign.load_dict()` restored `revisiting` by checking only that it named a valid era, not that `era_snapshots` actually had a snapshot for it — non-exploitable today because `enter_revisit()` is the only normal path that sets `revisiting`, and it never does so without a matching snapshot, and because the existing `parked_state`-is-missing guard already catches a save that drops both fields together. But that guard doesn't fire when a hand-edited save keeps a `parked_state` while pointing `revisiting` at an era `era_snapshots` has no entry for. Added a defensive cross-check (`revisiting not in self.era_snapshots` clears both fields) — belt-and-suspenders, asserted by a test but shouldn't change behaviour for any currently-reachable state.
  - Also removed `sustainability.COMPONENT_BLURB`: unlike the role/building tables above, it had no static-markup counterpart anywhere and no comment explaining why it was kept — genuinely dead, so it went rather than staying unexplained.

## Verified in a real browser

Phase 1 was checked running under Pyodide (not only under the pytest fake-DOM harness): the page boots, the four engine modules load from the virtual filesystem, seasons advance, the research panel renders (including locked nodes' reasons), researching a node feeds back into the next season, and `get_state()` converts through `toJs` into a plain JSON-serialisable object with the documented schema which `load_state()` takes back through `toPy` unchanged. Worth repeating after any change to the module-loading block in `index.html`, since no test covers that seam.

Re-verified after the audit pass above, including loading a deliberately short save through the widget's own `toPy` path and then advancing a season on it. The only console error is the service-worker registration failing inside the preview browser's sandbox; `sw.js` serves fine over HTTP and the registration line is identical in all eleven hub games, so it isn't Continuum's.

## Tech notes

- Python/Pyodide, per hub conventions.
- This game is significantly larger in scope than any single climate-quartet game — plan for the city simulation core, research tree engine, and save system to be built as clearly separated modules from the start, since seven eras' worth of content will get unwieldy fast if simulation/story/save logic are tangled together.
- Testing is mandatory per hub conventions — given the scope, prioritize testing the shared engines (simulation core, research tree, save system) most heavily, since bugs there compound across all seven eras.
- **Space-theme visual pass (matching hub/SOL).** `index.html` now includes `shared/space-bg.css` and the standard `<div class="space-bg">` markup right after `<body>`; `style.css` turned `body`/`#game` transparent so the starfield/nebula shows through, and every `.section` (status, sustainability, work, buildings, research) became its own glass panel — translucent gradient background, `backdrop-filter: blur(14px)`, violet-tinted `rgba(140,160,255,0.14)` border, soft drop shadow — rather than one giant card, matching this game's already-panelled layout. `.row` dividers and the h1 title's gradient-glow treatment followed the same pattern as SOL/the hub, but the warm amber/bronze accent (buttons, era-line, primary CTA) was kept rather than switched to SOL's blue, since that hue is Continuum's own identity. `button.secondary`/`button.primary` moved from flat fills to two-stop gradients of the same hue with a glossy top highlight and a `brightness(1.1)` hover; every existing `:disabled`/`.research-row--done`/`.research-row--locked` state and the locked-node reason text were re-skinned in place, not restructured — no CSS class/id was renamed, and no state-encoding color (land health, the four sustainability components, the weakest-component call-out, the warning/locked-reason amber) was touched, only chrome around them. `.meter-fill--land`/`.meter-fill--score` kept their exact hues and gained a matching-color glow. Verified against the pytest suite (99 passed, unchanged before/after) and live under Pyodide: starfield/nebula render, all four hub panels read as glass, season data and the research tree (including locked-reason text) render correctly, only console output is the pre-existing service-worker-registration error common to every hub game in the preview sandbox.

## Open items to revisit

- Exact era list (proposed above) — confirm or edit before Phase 1 wraps up.
- Visual style across eras — likely worth a dedicated decision once Phase 1's Tribal era is playable and you have a feel for the system's shape.
- How the Contextual Report Blog will discuss this single large DA vs. the Round 1 quartet's eight-small-games framing — worth thinking about once there's enough built to write about.
