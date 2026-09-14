> **Archived 2026-09-14.** Every answer here has been triaged into `planning/TODO.md` (yes) or `planning/LATER.md` (later/maybe/needs clarification); "no" answers were dropped. Kept here as the original source record — the going-forward working list is `TODO.md`/`LATER.md`, not this file.

# Improvement Ideas — September 2026

A brainstorm pass across every game on the site plus the hub itself: 20 ideas each, mixing big features and small fixes/polish. Nothing here is committed to — respond to any item by its label (e.g. "A4: yes", "C12: later", "F3: no, because...") and it'll get scoped from there. Le Champ de Mots is deliberately left out of this pass for now (active in-progress work) and will get its own lettered section once that settles.

Order follows the hub's own game listing (root `CLAUDE.md`).

---

## A. SOL

1. A prestige / "New Game+" layer after the soft win-state — restart with a permanent bonus, extending replay value past 100% completion.
2. A second achievement wave beyond the current 18 — speedrun-style ones ("won in under N seasons") or challenge-run ones (see #13).
3. A "welcome back" summary toast on return visits showing what changed since last session, distinct from the Governor's own away-management report.
4. A lifetime-stats screen (total resources mined, total clicks, total playtime) separate from the achievements panel.
5. Light sound effects (a click/coin-drop cue) — currently text/numbers-first by design, but cheap and additive without breaking the mobile-first stack.
6. The icon/visual layer the design doc explicitly left room for ("structure code so icons/images could be layered in later without a rewrite") — this is the natural time to cash that in.
7. A "+X since last save" delta readout right after loading a save code.
8. A shareable "my solar system" end-state summary card (screenshot-friendly) — doubles as BCM114 evidence material given SOL's dual DA role.
9. A single settings panel consolidating text-scale, sound, and animation toggles in one place, mirroring the pattern Continuum's Phase 5 just built.
10. A colorblind-safety audit of SOL's own meter/status colors, using the same Okabe-Ito method Continuum's Phase 5 just ran.
11. A visible "governor efficiency" readout (resources generated while away) to make that system's value legible.
12. A personal-best "fastest full playthrough" timer, tracked locally — no backend change needed.
13. A "pure clicker" / "never touched automation" challenge achievement for a different kind of completionist.
14. A light onboarding-tooltip pass for returning players who skipped the tutorial and forgot a mechanic.
15. Visual terraforming feedback — a literal color shift on a planet's card/icon as `terraform_progress` climbs.
16. A simple research-tree diagram instead of a flat list, matching Continuum's own research-panel visual language.
17. An ecology warning banner the moment a world crosses into the 25%-output-penalty zone, instead of relying on the player noticing the number.
18. A "reset this world only" option, distinct from a full save wipe, for retrying one planet's economy.
19. An achievement-earned toast/popup at the moment it's unlocked, rather than only being visible inside the panel.
20. A link from SOL's own achievements panel to the new hub-wide dashboard, closing the loop for players who don't know the hub tracks it too.

---

## K. Continuum

1. Phase 6: link Continuum into the main hub nav — the literal next item on its own roadmap.
2. Roll the achievements framework out to Continuum — 7 eras is rich, natural material (reach each era, hit a top sustainability score, recover from a "Failing" state, etc.).
3. A dedicated full-playthrough integration test (Tribal through Space Age in one continuous run), per Phase 6's own "full playthrough testing" ask.
4. A distinct audio cue per era transition, respecting the game's existing no-forced-pressure conventions.
5. A "civilization summary" end-of-playthrough report (population arc, sustainability trend, key choices) once Space Age is reached.
6. Named camera presets (top-down, street-level) in the 3D scene, beyond free drag-orbit — useful for screenshots and BCM114 evidence.
7. A way to actually *view* a revisited era's snapshot in the 3D layer, not just its stats — the save-revisit system already has the data.
8. Confirm each info-panel source is a clickable outbound link, not just static citation text — fix if it isn't.
9. A mobile sticky HUD, matching `shared/mobile-hud.js`'s pattern already used elsewhere in the hub.
10. A tutorial walkthrough via the shared `shared/tutorial.js` pattern, if Continuum doesn't have one yet.
11. Optional ambient audio bed per era, toggleable, reinforcing the game's strong narrative voice.
12. A scenario/difficulty select at new-game start (resource-scarce start, high-population start) for replayability now that the core arc is complete.
13. A "my settlement" shareable snapshot image, exported from the 3D scene.
14. A search/filter on the research tree now that it spans 14 tiers across 3 branches.
15. Confirm the new accessibility settings (text-scale, colorblind fixes) persist correctly through a real save/load, not just local `localStorage`.
16. An in-game "what's new" changelog panel, given how much has shipped incrementally — doubles as BCM206 process evidence.
17. A subtle day/night or seasonal lighting cycle in the 3D scene, tied to season count, for visual variety between era swaps.
18. An optional stricter "hard mode" sustainability variant for a second playthrough.
19. Distinct visible meshes per building type in the 3D scene (confirm current coverage and extend anything still generic).
20. A proper hub title-card screenshot/art pass once Phase 6 links it in, matching the bar the other 11 games' cards already set.

---

## L. The Hub Itself

1. Finish hub-linking Continuum and Trade Empire — both still flagged "not yet hub-linked."
2. Roll the achievements framework out to the remaining 10 games beyond SOL.
3. Deploy the accounts system to production — built and committed, per `CLAUDE.md`, but not yet live.
4. A "continue where you left off" section on the hub lobby for signed-in users, reusing the save-fetch pattern the achievements dashboard just built.
5. A site-wide dark/light theme toggle, if not already present.
6. Real favicon/PWA icon art — currently placeholder.
7. A "last updated" badge per title card, making the "something new every 2 weeks" cadence visible to visitors.
8. An aggregate stats/About page (total plays, saves, accounts) — good BCM206 process evidence.
9. Resolve the AdSense placeholder client ID before real public traffic scales up.
10. A visitor-facing "What's New" page pulling from the BCM114/BCM206 dev logs.
11. Search/filter on the hub lobby, ahead of the game count growing past 12.
12. A "quick game" vs. "deep systems game" style tag per title card, to help a visitor choose.
13. A site-wide keyboard-accessibility pass (tab order, visible focus rings) across the shared shell.
14. Auto-discover each game's `achievements.json` for the hub dashboard instead of hand-maintaining the list in `script.js`.
15. A "claim your save" nudge for anonymous players who've clearly invested real time, encouraging account creation.
16. A permanent service-worker cache-busting fix (a real cache-version bump strategy) — Continuum's own Phase 5 work already hit this exact stale-cache trap once.
17. A single cross-game feedback/bug-report entry point on the hub, given how often cross-cutting issues (like the recent Le Champ de Mots load bug) surface.
18. A more visible "Add to Home Screen" PWA prompt/nudge.
19. A lightweight public roadmap page, generated from each game's own `CLAUDE.md` milestone table.
20. A rate-limiting/abuse review on the anonymous save-code system — a save code is effectively a bearer token today with no throttling.

---

## B. Canopy

1. A dedicated end-of-session summary screen (the quartet's own visual-polish requirement calls for one) instead of the current inline comparison-message text, to properly close out the hope-angle payoff.
2. A "reset session" button so players can start a fresh forest grid without a full page reload.
3. A second, unlockable forest region/biome with different degradation/compounding rates, as a real content-expansion milestone beyond the single 36-plot grid.
4. Coordinate-style plot labels (e.g. "C3") so stakeholder-request messages read less abstractly than a raw index number.
5. Revisit the audio cue Pass 1 explicitly skipped for lack of an audio system — a minimal chime on recovery/wildlife moments, scoped small.
6. A lightweight history sparkline of income vs. standing value over the session, since only the two running totals are currently shown.
7. Let players save/compare two named playstyle runs ("conservationist" vs "extractor") to make the comparison mechanic feel more intentional.
8. Hover/tap tooltips on plot tiles showing the exact numeric value and degradation level, currently readable only via color gradient.
9. A colorblind-safe pattern/icon overlay for plot states (bare/preserved/replanting/recovered), which currently differ by hue only.
10. Surface biodiversity as an explicit number next to standing value, not just the wildlife-icon visual.
11. Diversify stakeholder requests to occasionally offer a positive trade-off, rather than always framing the moment as clear-vs-decline.
12. A visible badge when a stakeholder request is pending and the player has scrolled away, since the panel currently just toggles `hidden`.
13. A larger-grid option (e.g. 64 plots) as a difficulty/length variant.
14. A persisted "personal best" standing-value/income stat across sessions for light replay incentive.
15. Extend the mobile-dock treatment already proven on the action panel to the stats/legend panels too.
16. Keyboard navigation (arrows + Enter) for selecting and acting on plots, for accessibility.
17. A small floating "+X value" animation when a plot's compounding value ticks up, making "patience compounds" felt moment-to-moment.
18. A shareable end-of-session code/snippet, building on the existing save-code system, for comparing final numbers with a friend.
19. A distinct "fully mature" cap-off visual for Recovered plots, giving Replant's "near-parity" promise a visible finish line.
20. A closing counterfactual line at session end ("if every plot had stayed preserved, standing value would be ~X") to sharpen the hope-angle payoff.

## C. Grid

1. Extend the mobile-dock fix already shipped on Canopy/Trade Empire to Grid's plant-build action row, currently untreated.
2. A battery/grid-storage plant tier addressing renewable intermittency directly — a real-world lever the current six-tier system doesn't model.
3. Attach each disruption-event log line to the specific plant/type that failed, rather than a generic message.
4. Revisit weather-variability-on-renewable-output (explicitly skipped in Pass 1) as an opt-in "hard mode" now the core loop is proven.
5. A proper end-of-run summary screen with a score breakdown, since Grid currently has no defined "end."
6. Let players save two scenarios and overlay their trend graphs for a side-by-side comparison.
7. A plant-mix bar chart (composition by type) so "how clean is my grid" reads at a glance.
8. A one-time callout the first time cumulative renewable capacity crosses 50%, marking a narrative tipping point.
9. Require confirmation before retiring the last remaining unit of a plant type.
10. Show the exact aging/wear percentage next to the existing wear-icon states.
11. Build the real-world/aggregate comparison Pass 2 floated as a stretch goal — an average clean-score across players via the existing ratings backend — never actually built.
12. A visible toast/banner for disruption events, not just a text-line change, so a costly event can't be missed.
13. A funds breakdown (build vs. maintenance vs. disruption-damage spend) for transparency, especially since a flat-refund exploit was already found and fixed here once.
14. An undo/confirm step before Build, since misclicks currently can't be reversed and funds are tight early.
15. An interactive trend graph (hover a point for that round's exact values) instead of a static SVG line.
16. A "steeper demand growth" difficulty variant for replay value.
17. A closing "your grid vs. business-as-usual" counterfactual, sharpening the existing hope-angle payoff.
18. Colorblind-safe differentiation (not just color) for the trend graph's three lines, currently red/green/dashed-grey.
19. A badge on a plant type once its average age crosses breakdown-risk threshold, so risk is discoverable without reading wear-icon color.
20. A one-time first-use callout for Retire's refund and Maintain's cost math, instead of leaving it only in the small "i" tooltip.

## D. Tide

1. Extend the mobile-dock fix already shipped on Canopy/Trade Empire to Tide's investments panel and Advance Season button, currently untreated.
2. A fourth adaptation tier beyond the current three (3/6/10 units), since a long session likely caps the dampening curve early.
3. A numeric "seasons until next tile floods" estimate next to the sea-level meter, giving a concrete planning horizon.
4. A numeric then-vs-now stat block (total damage taken, total income earned) alongside the existing visual coastline comparison.
5. A scrollable/expandable ticker history, since currently only the latest message is shown.
6. A "what if you'd invested earlier" counterfactual replay of the same season sequence, directly visualizing the flattened curve the design doc calls for.
7. An end-of-session summary screen (total damage avoided, fish-stock trajectory, final adaptation tier), matching the quartet's shared visual-polish requirement.
8. A highlight/flash on the specific coastline row the moment it floods, so the event is noticeable rather than only inferable from the log.
9. An optional "harder lag" difficulty mode (e.g. a 5-season delay) as a replayable twist on the core delayed-consequence lesson.
10. Show the acidity value from 3 seasons ago explicitly next to current acidity, making the delayed link numerically visible.
11. Colorblind-safe/textured differentiation for coastline land vs. flooded tiles, currently color alone.
12. A "worst season" callout highlighting the single largest damage spike in the trend.
13. A persisted "best coastline saved" stat (fewest tiles flooded) across sessions.
14. An early-warning banner when rising acidity has already locked in a fish-yield crash 3 seasons out, without removing the delay itself.
15. A Grid-style historical mini-graph for acidity vs. fish yield, since Tide currently only has live meters.
16. Split the Output investment into a fishing/industry sub-choice, restoring a second decision axis flattened out of the original concept.
17. A one-time "first flood" callout distinct from routine ticker lines.
18. Let the coastline-comparison baseline be a player-chosen checkpoint instead of always Season 1, for long sessions.
19. A hover/tap detail per coastline tile showing its exact flood threshold.
20. A one-time ticker callout expanding on the real-world grounding for the very first adaptation-tier unlock.

## E. Aftermath

1. Extend the mobile-dock fix already shipped on Canopy/Trade Empire to Aftermath's actions panel (Resilience/Growth/Face Next Event), currently untreated despite being a long, panel-heavy page.
2. A fourth and fifth skill-tree node, since the current three (Reinforced Infrastructure, Community Reserves, Early Warning) can likely be fully unlocked within a handful of runs.
3. Branching/prerequisite structure for the skill tree instead of three independent flat nodes, so it reads as an actual tree as more nodes are added.
4. Build out the "legacy system" beyond its current flavor-text line — the visual settlement marker referencing prior runs that Pass 2 originally floated as a stretch goal.
5. Another event category beyond the existing weather/non-weather split (e.g. a heat-mortality event) for more variety across the fixed 7-event schedule.
6. Let players review a specific past run's full event-by-event breakdown, not just the aggregate run-1-vs-latest comparison.
7. An "expected damage this event" preview before clicking Face Next Event, so the mitigation math is visible ahead of time.
8. A visible "X/3 skills unlocked" progress summary, instead of scanning three separate rows.
9. A confirmation animation or state change when resilience/growth investment is spent, instead of the numbers just updating silently.
10. A proper end-of-run summary (total damage taken, income earned, knowledge earned) beyond the current compact one-line readout.
11. An export/import code for the localStorage-based skill tree and run history, since Aftermath's persistence is explicitly device-local only.
12. A "reset skill tree" option with confirmation, since there's currently no way to undo a permanent unlock.
13. Surface each skill's real-world grounding text more prominently on first unlock (a brief modal) rather than only the small inline paragraph.
14. A visual badge on the settlement art for each unlocked skill, so accumulated capability is seen, not just read as numbers.
15. Show the current run's actual severity band numerically, so the skill-strength-widens-variance mechanic from Pass 3 is legible, not just felt.
16. A "toughest run yet" comparison against the player's own historical worst run, as a second data point beyond run-1-vs-latest.
17. An optional extended-run mode (more than 7 events) once the skill tree is substantially unlocked.
18. Distinct visual intensity per event severity (mild/typical/severe) on the event-visual-storm art, beyond the current text label alone.
19. A live preview of the knowledge points a run will award before clicking Start New Run, rather than only revealing it after.
20. Show the Growth button's actual current payoff (e.g. "+16 resources/event" once at 2 growth) instead of the static "+8 resources" copy.

## F. Herd

1. A live "pure-growth vs. decoupled" counterfactual score comparison (like Thaw's `temperature_saved`) so the hope-angle payoff is visible in-session, not just verified in dev notes.
2. The pasture visual always renders exactly 5 fixed cow icons regardless of herd size — scale the visual herd so growth is visually legible, not just numeric.
3. An end-of-session "report card" comparing final score and decoupled fraction against a pure-growth baseline, giving Herd its own explicit payoff moment the way Loop's trend and Thaw's ghost-line comparison do.
4. A second feedback question specific to Herd's own risk ("did decoupling feel like a real strategy, or a tax on growth?"), mirroring the two-question pattern Thaw added in its Pass 3.
5. A one-time callout the first time the coupling ratio crosses a meaningful decoupling threshold — Herd has no equivalent to Drift's "turning point" moment.
6. A rising growth-cost curve instead of the current flat cost, so the growth-vs-decouple tradeoff sharpens in the late game.
7. A mini trend graph (reusing Thaw's/Loop's sparkline pattern) plotting methane or coupling ratio over rounds, since Herd currently shows only the current snapshot.
8. A combined dial/readout showing how the decoupling and plant-pivot levers interact, since they're currently separate blocks with no shared summary.
9. A small "+X income/round, +X methane/round" preview next to the Grow Herd button, which currently gives no preview of its consequence.
10. An in-game "Restart Farm" button with confirmation; currently the only way to reset is reload or save/load.
11. Borrow Thaw's tipping-flash pattern for the first time market/regulatory pressure meaningfully bites, giving that soft-consequence system its own felt moment.
12. A short worked numeric example in the How to Play panel (e.g. "growing to 10 units costs ~200 funds and emits ~10 methane/round unless decoupled").
13. A second, comparison farm/region (like Thaw's Region B/C) so a player can see a badly-run and well-run farm side by side in one session.
14. Min/max labels or a small history sparkline behind the coupling gauge so players see whether they're improving over time.
15. Surface the real 42% methane-intensity-reduction figure from the info page as a live inline comparison against the player's own decoupled percentage.
16. A confirm step or brief undo window on the pricier Plant-Based Pivot buy, since there's currently no way to reverse a misclick.
17. A one-time contextual nudge the first time methane meaningfully drags score down, since the score math is otherwise hidden behind an info-toggle.
18. Hook into the existing ratings backend to surface an aggregate community stat (e.g. "average player is X% decoupled").
19. Lightweight animation/feedback (a coin or cow icon pop) on successful investment clicks, matching other games' polish level.
20. Swap the context-blurb to a different pre-written line once methane crosses a threshold, reinforcing the lesson dynamically rather than as static flavor text.

## G. Thaw

1. Give Region B and Region C the same richer readouts Region A has (rise-rate, acceleration, trajectory-saved message) — currently they show only temperature, funds, melt status, and a graph, thinning out Pass 2's "side-by-side proof."
2. An explicit end-of-session line naming which region ended with the least warming and what investment mix achieved it, rather than leaving the comparison implicit in the graphs.
3. A distinct "critical" visual/color state beyond the current binary melting/stable, once acceleration climbs past a threshold.
4. Let players optionally label Region B/C's intended strategy (e.g. "growth-only", "balanced") so the comparison ties back to an explicit hypothesis.
5. A one-line real-world time calibration ("each round ≈ X years of warming at current pace") to ground the fixed background rise.
6. A `temperature_saved`-style stat for the secondary regions too, not just the primary, so B/C's counterfactuals are directly comparable.
7. Revisit the "no audio system" decision from Pass 1 with a minimal dependency-free ping for the tipping-point moment, now that it needs no new library.
8. An in-game reset/restart control so a player who wants to try a different strategy after tipping doesn't have to reload the page.
9. A short clarifying line for what a maxed-out +30° temperature meter represents, or rescale it.
10. A milestone callout the first time a dampening investment measurably delays a melt-threshold crossing versus the counterfactual, giving "the slope matters" its own felt moment.
11. Optional preset strategies for Region B/C (e.g. "run this region unmanaged") so the comparison stays meaningful even for a player who forgets to touch them.
12. A small inline forecast ("+X dampening") on the invest buttons before clicking, extending Pass 3's "make it legible" fix to the buy decision itself.
13. A fourth, optional AI-driven "worst case" region with a fixed aggressive-growth strategy, guaranteeing a baked-in comparison baseline.
14. A faint gridline at the melt threshold on the mini graphs (currently axis-free).
15. Log which strategy produced the best outcome as an optional anonymous aggregate stat via the existing ratings backend.
16. A one-line flavor difference per region (e.g. differing starting vulnerability) so the multi-region comparison feels less like three identical spreadsheets.
17. A "next round preview" tooltip on Advance Round showing the projected rise, so players can plan before committing.
18. Vary the intervention-feedback message's wording/intensity based on dampening magnitude, rather than fixed phrasing regardless of achievement.
19. A simple locally-stored "best run" stat (lowest final temperature, or highest temperature-saved) to give replay a concrete goal.
20. An optional free-text field specifically for "did intervention feel like it was working?", since that's the game's own flagged highest-risk area.

## H. Loop

1. Fix the import/export asymmetry: internal circularity investment above the target auto-sells as surplus, but excess imported supply from the Trade Link currently just evaporates with no revenue or rollover.
2. Let the player choose a different goods category at game start (clothing, furniture, etc.) instead of the hardcoded "electronics"/"a phone," reusing the same fraction-driven logic for replay variety.
3. A one-time celebratory animation/banner the first time the loop closes, rather than the current quiet CSS-class swap — this is the hub's clearest win-state per CLAUDE.md and is currently under-celebrated.
4. A "cost per unit of supply" readout next to Repair/Reuse/Recycle so players can compare efficiency directly instead of doing the division themselves.
5. Animate or highlight the decorative loop-ring nodes proportional to actual investment in each measure, since they're currently static regardless of real state.
6. A "time to close the loop" projection ("at your current rate, ~N more cycles") for a concrete near-term goal.
7. An in-game "Start New Chain" reset control, since currently only reload or save/load resets progress.
8. A second, differently-priced trading partner as a lightweight second option, short of a full second economy.
9. Let players cycle through a few real-world sector comparisons (plastics, electronics, metals) instead of the single static 7% benchmark always used.
10. A short note near the environmental damage meter clarifying that the 2.5x cost multiplier is a hard ceiling, currently only implied.
11. A lighter, more encouraging interim message for the first few cycles instead of the flat "not enough cycles yet."
12. A visible funds count-up or particle burst when trade-network export revenue lands, since that automatic income currently updates silently.
13. Toast callouts at circular-fraction milestones (25/50/75/100%), mirroring the "turning point" pattern already used in Drift.
14. A few alternate vignette phrasings within each fraction bucket, so replays don't show identical text every time.
15. Show each measure's running contribution to supply next to its owned count (e.g. "3 owned, supplying 9 units/cycle"), not just the raw count.
16. An optional "supply chain disruption" random event as an opt-in advanced-mode toggle, deliberately separate from the core deterministic lesson.
17. A live score breakdown ("Funds: X + Circularity bonus: Y = Score: Z") instead of leaving it implicit behind the info-toggle tooltip.
18. A small visual pulse on the trade-network display when its numbers change, matching the instant-update guarantee already locked in elsewhere.
19. A "closed-loop streak" tracker (consecutive cycles held fully closed) to reward sustained circularity, not just having achieved it once.
20. 2-3 alternate goods-flavor sets players can pick from at game start, rounding out a Pass 1 note that currently only ever ships one flavor.

## I. Drift

1. A mini strain/wellbeing trend graph reusing the sparkline pattern from Thaw/Loop — Drift already logs strain and arrivals every round but never visualizes them over time.
2. The region-visual skyline renders a fixed six buildings regardless of real capacity — scale the number/height of buildings with real capacity so the ambient visual reflects institutional growth.
3. An explicit in-play comparison tying the player's services-to-arrivals ratio back to the Uganda policy model already referenced in the context blurb.
4. An in-game "Start New Region" reset control, matching the same gap in the other three climate games.
5. A one-time callout the first time wellbeing crosses into the "thriving" band (≥70), mirroring the existing net-positive turning-point pattern for a second explicit milestone.
6. A one-line consequence description per strain level (stable/strained/critical), not just a color/label change.
7. A one-line effect summary directly on each capacity investment row (e.g. "Housing/Infrastructure reduce strain; only Services integrates people"), currently only in a details toggle.
8. Replace the coda's three separate meter bars with a clearer before/after mini-comparison, so the "generations from now" payoff reads as one comparison.
9. A rough real-world resettlement-outcome benchmark comparison at a milestone or session-end point, kept strictly institutional/statistical per this game's own sensitivity note.
10. A simple locally-stored "best run" stat (highest wellbeing reached, or fastest net-positive turning point) for replay value.
11. A periodic (e.g. every 20 rounds) session-milestone summary, since the long, uncapped timeline currently has no natural checkpoint besides the coda.
12. Extend the checkpoint message to occasionally note a comfortably-ahead dimension too, rather than always naming only the lagging one.
13. A difficulty-variant toggle (accelerated background severity) as an optional harder scenario, framed purely as a systems-parameter change.
14. A subtle "target" marker (e.g. at 70) on each of the three wellbeing gauge bars so players can gauge distance to "thriving" at a glance.
15. A one-time highlight/pulse on the coda button the moment its long-horizon story first becomes available, since there's currently no cue that a new option just appeared.
16. Tie the number or animation speed of the decorative arrival-dot stream to real arrivals-per-round, so the ambient visual communicates rising pressure.
17. A lightweight, passive "unmanaged control region" running the same background pressure for contrast — unlike Thaw, Drift has no built-in unmanaged baseline to compare against.
18. An optional free-text field specifically inviting concerns about tone/framing in the feedback prompt, given this is the most sensitivity-conscious game in the hub.
19. Turn the net-positive turning-point message into a small persistent badge ("Net-positive since round N") once triggered, rather than a one-off conditional line.
20. Surface the funds-to-economic-health scale reference point in the UI (e.g. "Economic health reaches 100 at 1000+ funds") so that 0-100 scale isn't a black box.

## J. Trade Empire

1. Wire up the shared save-widget contract (`get_state()`/`load_state()` plus `window.pyodide` exposure) — the game's own code comment flags this as a gap versus every other hub-linked game, including Continuum.
2. Link Trade Empire from the hub's main nav — it's the only fully-complete game (all 14 milestones) not yet listed on the site.
3. Add the shared ad-bar partial, since every other hub game already carries it.
4. Add the shared "Real Story" info-page panel with real-world sources on trade/logistics economics, matching every other game's pattern.
5. Add the in-game feedback prompt (same shared-ratings-backend pattern used elsewhere) so player sentiment on the trade/automation loop actually gets captured.
6. A 5th/6th purchasable ship (funded by profit) rather than the fixed 4-ship roster, giving a growth lever beyond research-gated upgrades.
7. A second automation-slot research tier beyond the current single node, since the slot cap sits well below the 4-ship roster.
8. A lightweight "ship arrived" toast notification, since arrivals currently surface only via status text and an increasingly busy sale log.
9. A real end-of-session/summary view beyond the currently-hidden endgame panel — total goods moved, colonies developed, etc.
10. Let players rename ships (cosmetic only) for stronger ownership over a growing fleet.
11. A per-route profitability readout (profit-per-trip), since performance is currently only visible via the aggregate sale log and total-profit ledger.
12. A historical price sparkline per good in the market panel, mirroring Grid's trend-graph approach instead of only a live snapshot.
13. A third self-contained expansion cluster beyond the Kepler Cluster, continuing the established galaxy-scaling pattern.
14. A colony detail view (development-level and need history over time) instead of only the always-visible current-state row.
15. A warning badge when a manually-controlled ship sits idle and empty for a long stretch, surfacing the "scaling friction" moment the design intends players to feel.
16. Make Fleet Priority's current target visible (e.g. highlight the most-urgent colony on the map) rather than only inferable after a ship starts moving.
17. A one-time callout marking the first automated ship, treating the manual-to-automation transition as a felt milestone.
18. Colorblind-safe differentiation for automated (gold) vs. manual (white) ship dots on the map, currently color alone.
19. A confirmation step before spending research points or automation credits, since these unlocks are currently one-click and irreversible.
20. A light visual flourish (a growing starfield or count-up animation) on the endgame's background-galaxy payoff, currently a purely numeric readout by deliberate scope cut.


---
---

Answers by user: 

## A
1. yes, are you thinking something simple like 200% more resources/more challenging or something more complicated like skill trees that give boosts and challenges and all that?
2. yes but I want it to be fairly easy to get 100% achievements so not extreme challenges and not requiring 100 hours of work to get
3. yes
4. yes
5. later
6. if easily possible yes, otherwise later
7. later, don't understand the meaning
8. yes
9. yes but site-wide
10. yes but site-wide
11. yes
12. later maybe
13. later maybe, back to A2
14. that should be in the "how to play" section, if not add it site-wide
15. yes
16. yes
17. yes
18. later
19. yes but site-wide
20. yes but site-wide

## K
1. yes
2. yes
3. later
4. later
5. yes
6. yes
7. later
8. yes
9. yes
10. yes
11. if easily possible, I am unsure your audio ability so am skeptical of all the audio suggestions so mainly marking them as later. talk to me about what you can do with audio and we can come back to all the audio ideas.
12. yes
13. yes
14. yes
15. yes
16. yes but site-wide (all games AND site)
17. yes
18. yes
19. yes
20. yes

## L
1. yes
2. yes
3. yes
4. yes
5. yes and colorblind accessability
6. yes
7. yes
8. yes but just visible in admin view for now
9. later, do you think the site is at a place I can go for getting ads? if so give instructions how to go about that.
10. yes but dont have them directly link to devlogs. make them a lot more brief, just short bullet points and a date. also collapsable by date since some days we are doing a lot
11. yes also maybe a top section with "games you have saves for" so players only here for 2-3 games have their games at the top.
12. yes tags for all the games sounds good, even outside of how long they are, can start a general sorting system through the whole site
13. yes
14. yes
15. yes
16. later, I don't know what this means
17. yes
18. later, i dont know what this means
19. yes but remember a lot of work happened outside the inital planning so it might be more than just the md file for it depending how well you logged each change.
20. maybe? it may help if we crate an auto-save system so people are less worried about having to save every few seconds too. I don't see people spamming it but it may be an issue.

## B
1. yes
2. yes
3. yes
4. yes
5. later, refer to previous audio comment
6. yes
7. yes
8. yes
9. yes
10. yes
11. yes
12. yes
13. yes
14. yes
15. if too much is pinned, nothing mas as well be pinned. be careful overpinning but if you still think this is a good idea yes, otherwise no.
16. yes
17. yes
18. yes
19. yes
20. yes
Also for this game, and many of the 114 games, I want to start focusing on the 'fun' aspects of the games rather than just the 'learning' now that this section of the class is over i can shift to gamification rather than pushing the teaching. make another one of these files after this with all the 'teaching' games to gamify them more following the 20 idea layout assuming we follow everything I say yes to within this file. (add making the file a point on the todo list)

## C
1. yes
2. yes
3. yes
4. yes
5. yes
6. later
7. yes
8. yes
9. yes
10. yes
11. yes
12. yes
13. yes
14. maybe an undo button or a "are you sure?" with a "don't show again" option because having to confirm every time can get irritating, mark as later for now and we can talk about it
15. yes
16. yes
17. yes
18. yes
19. yes
20. yes

## D
1. yes
2. yes
3. yes
4. yes
5. yes
6. yes
7. yes
8. yes
9. yes
10. later
11. yes
12. yes
13. yes
14. yes
15. yes
16. yes
17. yes
18. yes
19. yes
20. maybe later

## E
1. yes
2. yes
3. yes
4. yes
5. later
6. yes
7. yes
8. yes
9. yes
10. yes
11. yes
12. yes
13. yes
14. yes
15. yes
16. yes
17. yes
18. yes
19. yes
20. yes

## F
1. yes
2. yes
3. yes
4. later
5. yes
6. yes
7. yes
8. yes
9. yes
10. later, maybe prestige system rather than full reset
11. yes
12. yes
13. yes
14. yes
15. yes
16. later, refer to C14
17. yes
18. yes
19. yes
20. later, im not sure what that changes

## G
1. yes
2. yes
3. yes
4. yes
5. yes
6. yes
7. later, refer to previous comments on audio
8. maybe? idk the difference of making a new save and resetting enough
9. yes
10. yes
11. yes
12. yes
13. yes
14. yes
15. yes
16. yes
17. yes
18. yes
19. yes
20. yes

## H
1. yes
2. yes
3. yes
4. yes
5. yes
6. yes
7. yes
8. yes
9. yes
10. yes
11. yes
12. yes
13. yes
14. yes
15. yes
16. later
17. yes
18. yes
19. yes
20. yes

## I
1. yes
2. yes
3. yes
4. maybe
5. yes
6. yes
7. yes
8. yes
9. yes
10. yes
11. yes
12. yes
13. yes
14. yes
15. yes
16. yes
17. yes
18. yes
19. yes
20. yes

## J
1. yes
2. yes
3. yes
4. no unless it may be useful. this isnt a teaching game like the others, this is made to be just fun
5. no, see J4
6. yes
7. yes
8. yes
9. yes
10. yes
11. yes
12. yesyes
13. yes
14. yes
15. yes
16. yes
17. yes
18. yes
19. how often are players clicking this button? it may get annoying if it is a commonly pressed button
20. yes

## other comments
In general everything looks very crowded, the games and the code workspace, so I want to add to the list to clean that up. making sections either "colapseable" or other "screens" within a game could help with this. the main workspace issue is all the md files are are floating around that could be consolidated.
Add to the end a general bug check after all of this is done as well as generating another file like this I can answer. 
Can we have a game with visual options between low-poly, text-based, cartoon, and high-def to test the different ways that it can be viewed? When you first load in you choose a visual style which can be access through settings. I want champ to be the one that gets this if possible, its okay if the option is only available of desktop so you don't have to work around phone scaling with these visuals. I believe testing the different visual styles will help both me undertsnad what you can do and be a good point for my 206 class on testing different options. 