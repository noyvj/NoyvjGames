# BCM114 Dev Log — Game Content & Style

This log tracks the game-making side of the DA for BCM114: individual game concepts, mechanics, narrative/thematic style, and iteration on the games themselves (as distinct from the site infrastructure they live on — that's `BCM206-DEV-LOG.md`). This is the weekly proof-of-work trail that backs the LinkedIn post log and the Round 1/Round 2 contextual reports.

**This file is a running log, not a report.** Keep entries short and factual.

---

## Instructions for Claude Code

> Claude: at the end of any session where you work on an individual game's content — mechanics, level/scenario design, narrative or thematic framing, visual/audio style, playtesting notes, or GenAI prompt iteration used to build the game — append a new entry to the **Log** section below, in this exact format:
>
> ```
> ### YYYY-MM-DD
> **Game:** [which game — SOL, Grid, Canopy, Tide, Aftermath, etc.]
> **Did:** [2-4 sentences — what changed and why]
> **Result:** [what's playable/different now, or what's still open]
> ```
>
> Append below the most recent entry — never edit or delete a past entry. If a session touches both game content and site infrastructure, split it: log the game-content part here and the infra part in `BCM206-DEV-LOG.md`.

---

## Log

*(entries appended below, most recent last)*

### 2026-08-01
**Game:** Canopy, Grid, Tide, Aftermath
**Did:** Built the first BCM114 climate quartet from scratch, one game per subject: Canopy (deforestation & carbon sinks — a clear-vs-preserve plot grid where standing value compounds over time), Grid (energy transition — plant build-out against a rising emissions meter, with renewable costs that fall the more you invest in them), Tide (ocean acidification & sea-level rise — a deliberately delayed fish-stock consequence plus a tile-grid coastline that visibly floods), and Aftermath (climate adaptation & resilience — repeated short runs against a fixed disaster schedule, with a persistent cross-run skill tree). Each was built milestone-by-milestone (Python/Pyodide, no build step, fake-DOM pytest harness, git-tagged per milestone) through core loop, meter/consequence system, a "hope angle" scoring payoff, an in-game feedback prompt wired to the shared Neon backend, and a final visual/hub-integration pass.
**Result:** All four games fully playable, linked from the hub, and backed by a live star-rating/feedback widget. Each proves its hope angle mechanically — e.g. Grid's clean-grid trend comparison, Tide's `damage_saved` early-adaptation payoff, Aftermath's run-1-vs-latest skill-tree comparison. First BCM114 climate quartet complete (Canopy/Grid/Tide/Aftermath, 6-7 milestones each).

### 2026-08-07
**Game:** Herd, Thaw, Loop, Drift
**Did:** Scaffolded and built a second climate-quartet set, explicitly tagged by function (Causes / Futures-on-current-path / Systems-to-combat) and sharing one build-priority queue with the first quartet: Herd (industrial agriculture & methane — herd growth and emissions coupled by default, decoupled only through deliberate feed/cap/capture investment), Thaw (permafrost feedback loop — a background warming trajectory the player only partly controls, which visibly accelerates once melt crosses a threshold), Loop (circular economy — an extract→manufacture→use→discard chain that can be closed into a real loop via circularity investment), and Drift (climate migration & displacement — a receiving region balancing capacity against arrival pressure, with integration modeled as eventually net-positive). Same milestone-by-milestone build pattern as the first quartet. Herd's methane-penalty constants were rebalanced mid-build after a direct simulation showed the decoupling payoff was landing far too slowly (25-30 rounds) to read as a real in-session reward.
**Result:** All four games complete (7 milestones each) and hub-integrated; work carried from 08-07 into 08-08 to finish Loop and Drift. Both climate-quartet sets (8 games total) now fully built, tested, and live on the site.

### 2026-08-11
**Game:** Grid, Canopy, Tide, Aftermath, Herd, Thaw, Loop, Drift
**Did:** Ran a design-review iteration pass across all 8 climate games from an external notes document: merged its anticipated-issue/addition/testing-focus notes into each game's own `CLAUDE.md`, then implemented the concrete additions per game — a two-line emissions/renewable-cost trend graph and a renewable-unlock blurb (Grid); a continuous plot-maturity color gradient plus a recovery flash (Canopy); a delayed-effect ticker log and a visually separate sea-level meter (Tide); deterministic per-event severity variation (deliberately locked off on a game's first run so it doesn't undermine the existing run-comparison hope angle) plus real-practice grounding text on each skill (Aftermath); a prominent coupling-ratio dial gauge and an ambient haze overlay (Herd); a one-tick tipping-point screen flash (Thaw); animated chain-flow particles, goods-flavor naming, and a real-world circularity comparison (Loop); and a three-bar wellbeing dashboard with a plain-language checkpoint and an institutional case-study blurb (Drift). Every game also got a short factual real-world context blurb.
**Result:** All 586 tests across the 8 games pass with no regressions; every addition verified live in-browser (screenshots taken) before commit. Both quartets now carry this second layer of design-review polish on top of their original 7-milestone builds.

### 2026-08-18
**Game:** Grid, Canopy, Tide, Aftermath, Herd, Thaw, Loop, Drift
**Did:** Merged a second external design-review pass (`climate-games-iteration-pass-2.md`) into each of the 8 climate games' `CLAUDE.md` files as a new "Iteration Notes — Pass 2" section — documentation only, not yet built. Selections: global comparison + infrastructure aging (Grid); biodiversity sub-meter + stakeholder tension decisions (Canopy); an in-run adaptation tech tree (Tide); diversified event types + a stretch-goal legacy system (Aftermath); market dynamics with an alternative-protein-pivot fallback (Herd); a 2-3 region side-by-side comparison (Thaw); a trade network + single-item vignette (Loop); a long-horizon descendants coda (Drift). Two cross-cutting notes that apply to all eight (deferred cross-game/hub-wide connections, a standing visual-polish requirement) were recorded once each in `climate-quartet-plan.md` and `climate-quartet-2-plan.md` instead of being repeated per game. While in each file, also cleaned up the existing Pass 1 "Iteration Notes" sections, which were still phrased as forward-looking plans despite having actually been built and logged on 2026-08-11 — reworded to reflect what shipped, so the files match reality.
**Result:** All 8 games now carry an accurate build history (Pass 1 marked implemented, Pass 2 scoped but unbuilt) in their own `CLAUDE.md`. Pass 2 is design-only for now — sizeable enough (several are systemic gameplay additions, not just visual tweaks) that implementation is deliberately left for a dedicated future session per game rather than rushed through in this one.
