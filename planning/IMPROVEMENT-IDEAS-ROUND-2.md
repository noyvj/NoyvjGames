# Improvement Ideas — Round 2

Written assuming everything currently in `planning/TODO.md` has landed (achievements, settings panels, colorblind audit, confirmation-dialog pattern, per-game changelogs, mobile-dock, onboarding-tooltips, hub lobby search/filter/tags/Continue Playing, and the standalone features finishing alongside this document) — so nothing below duplicates what's already shipped. 30 ideas per section this time (up from the original 20), each section carrying at least 10 marked **[BIG]** and at least 10 marked **[SMALL]**, with the rest in between. Respond by label ("C7: yes", "K14: later", "Z3: no, because...") the same way as the first round.

**Structure change from round 1:** the old single "site-wide" bucket is now two sections — **Z. Games** (things worth doing across many/all games, not any one game's own feature) and **Y. Home** (the hub shell itself — `index.html`/`script.js`/`style.css`, not any individual game). The Warframe tracker (a personal project living in this workspace but outside the hub's own git tracking, per `warframe_build_tracker/TODO.md`) gets its own section too, per standing instruction — its answers route back to that local file, not to this repo's `planning/TODO.md`.

Order: hub games in the usual listing order, then Z (Games), Y (Home), then the Warframe tracker.

---

## A. SOL

1. **[BIG]** A second prestige tier beyond A1's flat yield bonus — a genuine skill-tree branch unlocked only after N prestiges, since the flat-bonus version was deliberately kept simple the first time.
2. **[SMALL]** Show the current prestige level as a small badge next to the game's title, not just inside the win-banner toggle.
3. **[BIG]** A "New Game+" variant that keeps one system unlocked from scratch (e.g. skip straight to Governor access on every planet) as a second, distinct replay mode alongside plain prestige.
4. **[SMALL]** A tooltip on the Prestige button itself stating exactly what resets and what doesn't, so the A18-style "reset this world" and "prestige" distinction is clear before clicking either.
5. **[BIG]** A proper offline/away report that's more than a snapshot — a real "while you were away" delta (resources gained, Governor decisions made), which the design doc's no-idle-timer rule doesn't actually forbid since it's reporting on real elapsed real-world time, not gating progress on it.
6. **[SMALL]** Let the Stats & Share card's copy button flash "Copied!" the same way other games' copy-to-clipboard buttons now do (the shared save-widget's own copy button already sets this precedent).
7. **[BIG]** A "Governor AI personality" choice per planet (aggressive/balanced/conservative presets feeding into the existing priority/budget system) instead of one flat priority dial.
8. **[SMALL]** Surface `governed_resource_generated`'s lifetime total on the main Stats screen too, not only inside the Governor Report panel.
9. **[BIG]** A proper multi-planet overview screen — a single scrollable dashboard of every unlocked planet's key stats at once, instead of navigating planet-by-planet.
10. **[SMALL]** An achievement-progress bar (X/22) visible in the toolbar itself, not only after opening the panel.
11. **[BIG]** A "trade route automation" layer — once two planets both have stable economies, let the player set a standing trade rule instead of manually re-triggering trade each time.
12. **[SMALL]** A subtle particle/spark animation on the exact resource icon when a manual click lands, reinforcing the "text/numbers-first but still tactile" feel.
13. **[BIG]** A build-order planner/checklist players can tick through manually — this is a spreadsheet-adjacent, optimization-friendly feature genuinely popular with incremental-game veterans.
14. **[SMALL]** Let the research-tree diagram (A16) be collapsed by tier, since 2+ distance tiers will make the flat card list long.
15. **[BIG]** A "sandbox mode" toggle for after the soft win-state — remove resource costs entirely so players can freely experiment with end-game builds for screenshots/exploration.
16. **[SMALL]** A small planet-count readout ("7/11 bodies visited") near the Travel button.
17. **[BIG]** An export/import progress code for lifetime stats (mirroring Aftermath's E12), so a player can back up progress outside the save-code system.
18. **[SMALL]** Add `title` tooltips to each Governor priority button explaining exactly what "Growth/Balance/Ecology" weighting does numerically.
19. **[BIG]** A genuine "close call" achievement family — surviving a near-0%-ecology collapse and recovering, tracked as its own dramatic moment rather than a flat threshold.
20. **[SMALL]** Let the terraform color-shift tiers (A15) also appear as a small swatch legend somewhere, so a new player understands the color progression at a glance.
21. **[BIG]** A "compare my run" feature against the site's aggregate stats (once Z's cross-game aggregate endpoint exists) — how does my playthrough pace compare to other players'.
22. **[SMALL]** A confirmation via the new shared `ConfirmDialog` before a full save wipe (distinct from A18's per-world reset, which is already gated).
23. **[BIG]** A "planet specialization" system — let a fully-developed planet lean into one resource type for a production bonus, adding a build-order decision late-game.
24. **[SMALL]** Surface the exact prestige-bonus percentage next to the resource-gain numbers themselves (e.g. "+10% from Prestige Lv.1") rather than only in the Stats panel.
25. **[BIG]** A "story mode" toggle that surfaces the game's existing flavor text (planet descriptions, milestone framing) more prominently as a light narrative thread, giving SOL something closer to Continuum's diegetic feedback approach.
26. **[SMALL]** A "reset settings to default" button inside the Settings panel, in case a player fat-fingers the text-scale slider to an extreme.
27. **[BIG]** A proper end-game "epilogue" screen once every planet is 100% terraformed — currently the soft win-state is a banner, not a dedicated moment.
28. **[SMALL]** Let the Sky City info-toggle's copy also state the exact Mars-material cost ratio, not just that a second resource is needed.
29. **[BIG]** A community leaderboard for fastest full completion (opt-in, using the existing ratings backend's infrastructure) — SOL is the most "speedrunnable" game on the site.
30. **[SMALL]** A small animated icon transition when a building finishes constructing, distinct from the click-feedback darken effect.

---

## B. Canopy

1. **[BIG]** A third biome beyond the main forest and Highland Grove (B3) — a wetland or coastal-forest region with its own tension (e.g. flood risk on preserved plots), unlocked at a higher standing-value threshold than Highland Grove.
2. **[SMALL]** Let the coordinate-style plot labels (B4) also show up in the stakeholder-request panel, naming exactly which plot is being asked about.
3. **[BIG]** A "forest history" timeline view — a scrollable log of every clear/preserve/replant decision made this session, not just the sparkline.
4. **[SMALL]** A small confetti/leaf-burst animation the first time a plot reaches "fully mature," distinct from the existing cap-off visual (B19).
5. **[BIG]** A genuine multiplayer-adjacent feature: compare your forest's standing value against the site's aggregate average (once Z's cross-game endpoint exists), similar to Grid's global-comparison line.
6. **[SMALL]** Let the Highland Grove's unlock threshold be visible as a progress bar toward 2,000 standing value, not just a silent unlock.
7. **[BIG]** A "forest ranger" mode — an optional harder difficulty where soil degradation from clearing is steeper, for players who've already mastered the base game.
8. **[SMALL]** A tooltip on the stakeholder "incentive" request type (B11) clarifying it's a genuinely positive offer, distinct from the clear-or-decline requests, before the player opens it.
9. **[BIG]** A named-run "playstyle badge" (Preservationist / Balanced / Harvester) computed from the session's clear-vs-preserve ratio, surfaced on the Session Summary and shareable snippet.
10. **[SMALL]** Let biodiversity's numeric readout (B10) show its rate of change (+X/tick), not just the current total.
11. **[BIG]** A "reforestation partner" mechanic — periodically, a second party offers to co-fund replanting a specific bare plot in exchange for a smaller cut of its future value, adding a third stakeholder-style decision type beyond clear-requests and incentives.
12. **[SMALL]** A small "?" icon next to soil-quality percentages explaining what degradation actually costs in future yield.
13. **[BIG]** A proper end-of-session "forest report card" — biodiversity trend, standing-value trend, and stakeholder-relations trend as three small graphs side by side, extending the Session Summary panel.
14. **[SMALL]** Let the Large (9×8) grid preset (B13) have a matching "Small (4×4)" option for a faster, shorter session.
15. **[BIG]** A "legacy forest" feature — starting a fresh session with a small, permanent starting bonus based on a previous session's final standing value (an Aftermath-style meta-progression layer, opt-in).
16. **[SMALL]** Let the keyboard-navigation (B16) also support a "select next stakeholder request" shortcut.
17. **[BIG]** A visible seasonal cycle — plots grow slightly faster/slower depending on an in-game season indicator, adding light texture without a new core mechanic.
18. **[SMALL]** A "copy my playstyle badge" button next to the existing shareable snippet (B18).
19. **[BIG]** A "community forest" comparison page — see how other players' saved Run A/B snapshots (B7) compare in aggregate, anonymized.
20. **[SMALL]** Let the "+X value" floating animation (B17) vary its color slightly by magnitude, so a big compounding tick reads as more exciting than a small one — purely a size/motion tweak, no new color-only meaning per the colorblind audit's own standard.
21. **[BIG]** A "specialist plot" upgrade — once a plot has been preserved long enough, let the player choose a permanent specialization (higher biodiversity vs. higher economic value) as a one-time branching choice.
22. **[SMALL]** A small icon on plots that have survived 3+ stakeholder-clear requests without ever being cleared, as an informal "veteran plot" marker.
23. **[BIG]** A proper wildlife log — a running list of which species icons have appeared and when, turning the ambient wildlife-appearance system into something worth checking back on.
24. **[SMALL]** Let the Reset Session confirmation (already gated) also show the current session's standing value in the confirm message, so the player sees exactly what they're giving up.
25. **[BIG]** A "community grant" event type — occasionally a stakeholder offers funding specifically for replanting (not just the existing incentive-to-preserve type), adding investment-in-recovery as its own decision.
26. **[SMALL]** A subtle highlight/glow on whichever plot the mouse last hovered, to make the coordinate system easier to track visually on the larger 9×8 grid.
27. **[BIG]** An "adopt a plot" personal-goal feature — let the player mark one specific plot as a long-term project, with its own dedicated mini-history separate from the aggregate stats.
28. **[SMALL]** Let the Session Summary's counterfactual line (B20) also state the percentage difference, not just the absolute value.
29. **[BIG]** A guided "best strategy" replay — an optional AI-narrated example playthrough demonstrating a strong preserve/clear balance, for players who want a worked example beyond the tutorial.
30. **[SMALL]** A small monthly/seasonal color palette shift on the forest background art, purely decorative, reusing the existing space-bg-adjacent theming system.

---

## C. Grid

1. **[BIG]** A genuine "grid operator career" meta-progression — persistent stats/unlocks across multiple runs (an Aftermath-style skill tree), since Grid currently resets fully each session.
2. **[SMALL]** Let the breakdown-risk badge (C19) show the exact percentage chance, not just a badge.
3. **[BIG]** A regional/multi-grid mode — manage two interconnected grids with the ability to share surplus capacity between them, extending the single-grid model.
4. **[SMALL]** A tooltip explaining exactly what "aging" does numerically on hover over any plant's wear percentage.
5. **[BIG]** A "grid operator report" — a proper narrative end-of-run summary (already partially covered by C5's Run Summary) extended with a letter-grade or tier ranking against the real-world benchmark line.
6. **[SMALL]** Let the plant-mix bar chart (C7) animate its bars growing/shrinking on change, rather than snapping instantly.
7. **[BIG]** A "demand response" mechanic — let the player invest in reducing peak demand itself (efficiency programs) as a fourth lever alongside build/retire/maintain, distinct from supply-side plant choices.
8. **[SMALL]** A small icon distinguishing renewable vs. fossil plant rows at a glance in the plant-mix chart legend, beyond just color (already colorblind-audited, but an icon adds a second at-a-glance cue).
9. **[BIG]** A storage-arbitrage mini-game layer — once the battery tier (C2) is built, let the player manually choose when to charge/discharge for a small bonus, rather than it being purely automatic buffering.
10. **[SMALL]** Let the disruption-event toast (C12) include a "why this happened" one-line reason tied to the specific plant that failed.
11. **[BIG]** A "grid resilience score" separate from the clean-share score — rewarding diversification (not all-renewable, not all-fossil) as its own axis, reflecting a real grid-planning consideration.
12. **[SMALL]** A small historical "best round" marker on the trend graph, showing the single best clean-share round achieved this run.
13. **[BIG]** A scenario-select mode at game start — "coal-heavy legacy grid," "greenfield renewable-first," etc. — each with different starting plant mixes, for replayability.
14. **[SMALL]** Let the funds-breakdown panel (C13) show a small pie/bar visual, not just numbers.
15. **[BIG]** A cross-player aggregate comparison (C11, already flagged in `LATER.md` pending the shared backend endpoint decision) — worth revisiting now that Z's cross-game aggregate-stats question is being answered anyway.
16. **[SMALL]** A "first battery built" one-time callout, matching the existing pattern used for other plant-type firsts.
17. **[BIG]** A weather-event log (separate from the disruption-event log) narrating exactly how Weather Variability (C4) affected a specific round's renewable output.
18. **[SMALL]** Let Retire's confirmation dialog (C14) show the plant's current age/wear alongside the "last unit" warning, so the decision context is complete.
19. **[BIG]** A "policy lever" mechanic — an occasional opt-in choice (carbon pricing, subsidy) that shifts the cost curve temporarily, adding a light real-world-policy dimension.
20. **[SMALL]** A small up/down arrow next to the demand number each round, showing whether this round's growth was faster or slower than average.
21. **[BIG]** A "grid twin" comparison mode — run two strategies side by side in a split view (same starting conditions, different choices), directly visualizing the fossil-vs-renewable divergence the way Thaw's multi-region comparison does.
22. **[SMALL]** Let the steeper-demand-growth toggle (C16) show its exact multiplier in its own label, not just "on/off."
23. **[BIG]** A maintenance-scheduling feature — let the player pre-commit to a maintenance cadence per plant type instead of manually clicking Maintain every time it's needed.
24. **[SMALL]** A subtle pulse on the emissions meter the instant it crosses the 50% renewable-capacity tipping point (C8), reinforcing the existing callout.
25. **[BIG]** A "grid of the future" endgame projection — extrapolate the current trajectory 20 more rounds and show where it leads, similar in spirit to Thaw's counterfactual.
26. **[SMALL]** Let the plant-age wear icon (C10) have three distinct visual tiers, not just a percentage number.
27. **[BIG]** An "emergency response" mode — a rare, opt-in scenario where a major disruption hits and the player must stabilize the grid within a few rounds, as a distinct challenge mode.
28. **[SMALL]** A small "clean streak" counter visible at all times (not just inside the achievements panel), mirroring how prominently the coupling gauge sits in Herd.
29. **[BIG]** A community-sourced "real utility" comparison mode — let players optionally see how their grid compares to a specific real region's actual generation mix (a stretch, needs real per-region data sourcing).
30. **[SMALL]** A one-time tooltip explaining exactly why renewable costs decrease with cumulative investment (the learning-curve mechanic) the first time a renewable is built, not just in the Info Page.

---

## D. Tide

1. **[BIG]** A fifth adaptation tier beyond Storm-surge barriers (D2) — a "managed retreat" option that trades some coastline for guaranteed long-term stability, introducing a genuinely different strategy branch.
2. **[SMALL]** Let the worst-season callout (D12) also show which specific investment (or lack of one) contributed most to that season's damage.
3. **[BIG]** A multi-settlement mode — manage two coastal settlements with different starting elevations/exposure, similar in spirit to Thaw's multi-region comparison.
4. **[SMALL]** A small wave/tide animation cue tied to the sea-level meter's current percentage, purely decorative.
5. **[BIG]** A "climate refugee" mechanic — once a coastline is sufficiently flooded, population must relocate to remaining land, adding a light connection to Drift's displacement theme without duplicating its mechanics.
6. **[SMALL]** Let the fish-yield crash warning banner (D14) include a suggested action (invest in acidity reduction) rather than just the warning.
7. **[BIG]** A "delayed consequence" visualization — a proper timeline graph showing today's acidity choices against the eventual fish-yield impact several seasons later, making the core lesson more explicit for players who want it.
8. **[SMALL]** A small tide-level indicator showing the current season's high/low tide relative to the coastline tiles, for extra texture.
9. **[BIG]** A community seawall-design comparison — see aggregate stats on which adaptation tier combination other players reach fastest.
10. **[SMALL]** Let the acidity/fish-yield mini-graph (D15) show a dashed reference line at the historical average, similar to Thaw's melt-threshold gridline.
11. **[BIG]** A "coastal economy diversification" mechanic — let the settlement invest in a non-fishing, non-industry third income source (tourism, aquaculture) as a hedge against acidity-driven fish crashes.
12. **[SMALL]** A one-time "first adaptation tier unlocked" celebratory callout, matching the pattern other games use for milestone firsts.
13. **[BIG]** A "storm season" event layer — periodic acute weather events (distinct from the slow background sea-level rise) that test whether adaptation infrastructure holds up under an immediate shock, not just gradual pressure.
14. **[SMALL]** Let the then-vs-now stat block (D4) include a small sparkline, not just numbers.
15. **[BIG]** A proper settlement-growth mechanic — let population/economy grow over a successful session, giving "success" a visible, growing settlement rather than just a stable one.
16. **[SMALL]** A tooltip on the hard-lag difficulty toggle (D9) explaining exactly what the extended lag means in seasons, not just "harder."
17. **[BIG]** A "coastal heritage" mechanic — certain coastline tiles have extra value (a historic site, a reef) that's worth protecting even at higher cost, adding a values-based decision beyond pure economics.
18. **[SMALL]** Let the comparison-baseline checkpoint (D18) show a small marker on the trend graphs at the exact season it was set.
19. **[BIG]** A "sea-level rise scenario" select at game start — conservative/moderate/severe real-world-grounded trajectories, for replayability tied to actual climate scenarios.
20. **[SMALL]** A small icon change on the seawall visual per tier (D2's tiers already have distinct visual signatures per the Pass 2 notes — extend that to a small icon badge in the investments panel too).
21. **[BIG]** A "citizen science" side-mechanic — periodically, monitoring investment reveals a piece of real-world acidification data as a reward, blending the info-page content directly into play.
22. **[SMALL]** Let the output-mix sub-choice (D16) show a live preview of the income/fish-yield tradeoff before committing.
23. **[BIG]** A proper "recovery" narrative — once fish stock crashes and later rebuilds, a distinct callout celebrating the recovery, mirroring the existing decline narration with equal weight.
24. **[SMALL]** A small "seasons survived" counter always visible, not just inside the session summary.
25. **[BIG]** A "shared coastline" cooperative-framing feature — even though there's no real multiplayer, frame an aggregate community stat as "coastlines protected across all players" for a sense of shared stakes.
26. **[SMALL]** Let the per-tile flood-threshold tooltip (D19) also state how many seasons remain at current pace, not just the raw threshold.
27. **[BIG]** A "before it's too late" replay mode — let the player replay from a mid-session checkpoint with the knowledge of what's coming, an explicit hindsight mechanic distinct from D6's counterfactual.
28. **[SMALL]** A subtle color-independent pattern on the seawall visual tiers so the D11 colorblind-audit redundancy extends to the new infrastructure art too.
29. **[BIG]** A "settlement name and history" light narrative layer, giving Tide a bit of the same diegetic-flavor texture Continuum uses, scaled down to fit Tide's own format.
30. **[SMALL]** A one-time tooltip the first time the harder-lag mode (D9) is toggled, confirming the change takes effect next season, not immediately.

---

## E. Aftermath

1. **[BIG]** A sixth and seventh skill node, extending E2/E3's prerequisite-tree pattern into a genuine multi-branch tree rather than a short linear-ish list.
2. **[SMALL]** Let the skill-unlock toast (E14) persist slightly longer for skills with more real-world grounding text to read.
3. **[BIG]** A "disaster type specialization" — let the skill tree branch into weather-focused vs. social-shock-focused resilience paths, giving E6's new event category (Civil Unrest) its own upgrade path.
4. **[SMALL]** A small "runs completed" counter always visible, not just inside the Review Past Runs panel.
5. **[BIG]** A "generational memory" mechanic — occasionally, a run references a specific past run's outcome in its event flavor text, deepening the "legacy" system (E4) beyond the count-chip row.
6. **[SMALL]** Let the extended-run mode (E18) show its exact new event count in the toggle's own label.
7. **[BIG]** A proper difficulty-scaling curve across many runs — event severity variation (already tied to skill-tree strength) could also scale with total lifetime runs played, for long-term veterans.
8. **[SMALL]** A one-time tooltip the first time a run scores negative, reassuring the player that the skill tree persists regardless.
9. **[BIG]** A "community resilience index" — an aggregate stat (once Z's cross-game endpoint exists) showing the average skill-tree strength across all players, framed as a real community achievement.
10. **[SMALL]** Let the toughest-run-yet comparison (E17) show the specific event sequence that made it toughest, not just the score.
11. **[BIG]** A "mutual aid network" event — a rare positive event where another (fictional) settlement offers help mid-run, adding a moment of external support to the otherwise self-reliant framing.
12. **[SMALL]** A small badge on the settlement art (extending E15) for reaching a "toughest run" personal best, not just per-skill badges.
13. **[BIG]** A proper narrative epilogue at the very end of an extended run (E18), similar in spirit to Continuum's era-transition beats but scaled to Aftermath's shorter-run format.
14. **[SMALL]** Let the expected-damage preview (E8) show a confidence range, not just a single number, since severity does still vary.
15. **[BIG]** A "specialize or generalize" build-diversity achievement family — reward both a narrow deep-investment strategy and a broad balanced one as equally valid playstyles.
16. **[SMALL]** A small animated flourish on the Review Past Runs panel when a run's score beats the previous best.
17. **[BIG]** A "climate scenario pack" — let players choose among a few different real-world-grounded event-schedule variants (coastal/inland/urban) at run start.
18. **[SMALL]** Let the knowledge-points-live-preview (E20) show its value with a small "+" animation when it increases.
19. **[BIG]** A proper "resilience curriculum" mode — a guided sequence of runs with specific goals each time, for a player who wants structure beyond free play.
20. **[SMALL]** A tooltip explaining exactly how `skill_tree_strength()` affects severity variation, since it's currently an internal-only concept.
21. **[BIG]** A "what would have happened" replay — apply a different (hypothetical) skill-tree state to an already-completed run's event sequence and show the alternate outcome.
22. **[SMALL]** Let the reset-skill-tree two-click confirm (E13) show exactly how many knowledge points will be refunded before the second click.
23. **[BIG]** A community "hardest schedule survived" leaderboard, since severity variation means no two hard runs are identical.
24. **[SMALL]** A small icon per event category (weather/non-weather/social) visible in the Review Past Runs list itself, not just the live event display.
25. **[BIG]** A proper "settlement identity" customization — let the player name their settlement once, carried across all runs, giving the run-to-run persistence a bit more personal stake.
26. **[SMALL]** Let the export/import progress code (E12) show a short human-readable summary of what it contains before copying, not just the raw code.
27. **[BIG]** A "resilience mentor" onboarding mode — an optional guided first run with inline suggestions, distinct from the standard tutorial, for a gentler on-ramp to the skill-tree strategy layer.
28. **[SMALL]** A one-time callout the first time a run's severity variation actually swings notably harsher due to skill-tree strength, explaining why.
29. **[BIG]** A "societal memory" system where certain very bad past-run outcomes (a near-total loss) permanently unlock a unique defensive skill not otherwise available — turning a bad run into a genuinely different kind of reward.
30. **[SMALL]** A small "X runs until next skill affordable" estimate next to a locked skill's cost, based on average knowledge-point earn rate.

---

## F. Herd

1. **[BIG]** A "regional herd network" — manage a second, smaller satellite farm with its own coupling ratio, letting surplus decoupling investment from the main farm partially offset the satellite's emissions.
2. **[SMALL]** Let the pasture visual's cow-count thresholds (F2) include a small herd-size number overlay, not just the visual count.
3. **[BIG]** A "consumer demand shift" mechanic — occasionally, market preference shifts toward plant-based output, making the pivot (already built) temporarily more profitable, mirroring real market dynamics without the complexity Pass 2 originally deferred.
4. **[SMALL]** A one-time tooltip the first time coupling ratio crosses below 0.5, explaining what "decoupled" means in plain terms.
5. **[BIG]** A "generational herd genetics" system — invest in breeding for naturally lower methane intensity per animal, a slow-burn fourth decoupling lever alongside feed/caps/capture/pivot.
6. **[SMALL]** Let the report card (F3) show the exact percentage of the pure-growth baseline the player's score beat by.
7. **[BIG]** A "farm cooperative" comparison — aggregate stats on how much methane-per-unit the whole player community has collectively avoided, framing individual play as contributing to a bigger number.
8. **[SMALL]** A small "record decoupling ratio" marker on the coupling gauge, similar to Grid's best-round marker idea.
9. **[BIG]** A proper multi-season weather/feed-cost variation layer, adding light unpredictability to the otherwise steady investment-return math.
10. **[SMALL]** Let the community stat (F18) show a small trend arrow (community average improving/declining over time) if the backend can support it cheaply.
11. **[BIG]** A "sustainable certification" milestone — reaching a sustained low coupling ratio for N rounds unlocks a permanent price premium, mechanically rewarding sustained decoupling rather than a one-time threshold.
12. **[SMALL]** A tooltip on the Plant-Based Pivot's confirm dialog (F16) stating the exact income tradeoff percentage, not just the general warning.
13. **[BIG]** A "supply chain" expansion — let the player invest downstream (processing, distribution efficiency) as a new income lever distinct from herd growth itself.
14. **[SMALL]** Let the real-world comparison message (F15) update its framing once the player's own reduction actually exceeds the cited 42% figure, congratulating them for beating the real benchmark.
15. **[BIG]** A "herd health" sub-system — animal welfare as a light second axis alongside methane, where certain decoupling measures (better feed) also improve welfare, tying two real agricultural concerns together.
16. **[SMALL]** A small pulse on the methane trend graph (F7) the moment the curve visibly flattens, mirroring Grid's own trend-flattening idea.
17. **[BIG]** A "farm tour" narrative mode — periodic short flavor vignettes (an inspector visit, a community event) reacting to the farm's current coupling ratio, adding light texture without new mechanics.
18. **[SMALL]** Let the investment consequence preview (F9) show its numbers with a small before/after arrow, not just plain text.
19. **[BIG]** A "regional methane cap" scenario mode — an opt-in harder variant where a hard regulatory cap exists, forcing decoupling rather than merely rewarding it.
20. **[SMALL]** A small badge for reaching the maximum feasible decoupling ratio at least once, distinct from the existing achievement set if not already covered.
21. **[BIG]** A community "decoupling leaderboard" by best score-vs-baseline gap, since that gap (not raw score) is the real teaching metric per this game's own Pass 3 audit.
22. **[SMALL]** Let the min/max range labels behind the coupling gauge (F14) update their session-best marker with a small flash when a new best is set.
23. **[BIG]** A "second herd type" — introduce a genuinely different animal (poultry, aquaculture) with its own coupling curve, as a late-game diversification choice.
24. **[SMALL]** A tooltip explaining exactly what the ambient haze overlay's intensity represents, for a player who notices the visual but not the connection to the methane meter.
25. **[BIG]** A "farm succession" meta-progression — similar to Aftermath's skill tree, let a completed session unlock a small starting bonus for the next one, adding replay incentive Herd currently lacks.
26. **[SMALL]** A small icon distinguishing the three original decoupling measures (feed/caps/capture) from the plant-based pivot in any summary list, since the pivot is structurally different.
27. **[BIG]** A "policy advisor" event — periodically offers the player a choice between a subsidy for decoupling investment or a flat cash bonus, adding a light policy-tradeoff decision.
28. **[SMALL]** Let the worked numeric example in the tutorial (F12) be revisitable from the How to Play panel directly, not just during the initial walkthrough.
29. **[BIG]** A "methane capture marketplace" — let excess capture-system capacity be "sold" for a small return, giving the capture investment a secondary income use once fully built out.
30. **[SMALL]** A small animated methane-wisp effect that visibly thins as the coupling ratio improves, reinforcing the ambient haze overlay's existing intensity cue with motion, not just opacity.

---

## G. Thaw

1. **[BIG]** A fifth region — a genuinely player-optional "wildcard" region with a randomized (but still deterministic-per-seed) starting condition, for replayability beyond the fixed A/B/C/D set.
2. **[SMALL]** Let the region flavor lines (G16) be visible as a permanent subtitle under each region's name, not just discoverable once.
3. **[BIG]** A "permafrost carbon bank" mechanic — let sustained low-acceleration play in a region bank a resource usable for a one-time bonus elsewhere, connecting Thaw's single-region focus to a light meta-choice.
4. **[SMALL]** A tooltip on the Region D reveal toggle (G13) explaining what "worst case" means before the player reveals it.
5. **[BIG]** A "tipping cascade" mechanic — once one region tips into the feedback loop, a small chance it accelerates a neighboring region too, making the loop's danger feel systemic rather than contained per-region.
6. **[SMALL]** Let the melt-threshold gridline (G14) be labeled with its exact temperature value, not just a dashed line.
7. **[BIG]** A "climate scientist" info-mode — an optional deeper data view showing the actual real-world methane-release curves alongside the in-game graph, for players who want the full context beyond the Info Page.
8. **[SMALL]** A small distinct color-independent icon on the critical melt-status tier (G3), reinforcing its text label with a shape cue too.
9. **[BIG]** A "long game" mode — extend the session length significantly for players who want to see the feedback loop's full long-run trajectory, distinct from the standard session length.
10. **[SMALL]** Let the next-round preview tooltip (G17) show all three regions' preview simultaneously in one combined tooltip, not requiring a separate hover per region.
11. **[BIG]** A community "average acceleration factor" comparison — how does this player's regions compare to the aggregate, reinforcing the hope-angle message that intervention is common and effective.
12. **[SMALL]** A one-time callout the very first time `dampening_at_melt_start` (already tracked for the early-investor achievement) is nonzero, explicitly praising the pre-emptive investment.
13. **[BIG]** A "policy simulation" branch — let the player choose a real-world-inspired regional policy stance (aggressive mitigation / gradual transition / status quo) at game start, subtly weighting starting dampening.
14. **[SMALL]** Let the preset strategies (G11) show a small preview of the resulting investment split before committing.
15. **[BIG]** A "permafrost restoration" late-game mechanic — once a region stabilizes, let sustained investment slowly reverse some melt, giving recovery (not just prevention) a mechanical payoff.
16. **[SMALL]** A small trend arrow next to each region's temperature readout, showing whether this round's rise was faster or slower than last round.
17. **[BIG]** A "four regions, one story" narrative thread connecting A/B/C/D lightly (a shared research effort, a shared funding pool) without merging their independent mechanics.
18. **[SMALL]** Let the intervention feedback message's tiered phrasing (G18) include a small icon per tier (modest/meaningful/strong), not text alone.
19. **[BIG]** A "scientist's log" — a running, dated record of key moments (first melt, tipping point, recovery) per region, similar to a lightweight version of Continuum's ongoing-log system.
20. **[SMALL]** A tooltip explaining exactly what `SECOND_WARMING_MILESTONE` (G10) represents in real terms before it's ever crossed.
21. **[BIG]** A "region rescue" mechanic — if a region tips into critical, allow a costly one-time emergency intervention (distinct from ongoing preserve/monitor investment) as a last-resort lever.
22. **[SMALL]** Let the best-run personal record (G19) show which region achieved it, not just the raw `temperature_saved` number.
23. **[BIG]** A proper multi-session "climate archive" — a persistent record across many sessions of every region's best-ever performance, extending G19's single stat into a fuller local history.
24. **[SMALL]** A small pulse on the acceleration-factor readout the instant a region crosses into the critical tier, reinforcing the existing status change with motion.
25. **[BIG]** A "counterfactual world tour" — let the player briefly preview what Region D's (worst-case) trajectory would look like applied to Region A/B/C's actual starting conditions, making the comparison more concrete.
26. **[SMALL]** Let the intervention free-text field (G20) show a short prompt/example answer as placeholder text, encouraging more specific responses.
27. **[BIG]** A "thaw forecast" mini-game — periodically, let the player make a prediction about next-round temperature before advancing, rewarded (cosmetically) for accuracy, adding light engagement to the largely player-doesn't-control-the-driver design.
28. **[SMALL]** A small "rounds since last tipping event" counter, giving stability its own visible streak the way Grid tracks clean streaks.
29. **[BIG]** A "global vs. regional" framing toggle — let the player see the exact same mechanic reframed as either "my region's choices" or "the global aggregate of many regions like mine," reinforcing the real-world scale of the issue.
30. **[SMALL]** A one-time tooltip the first time Region D is revealed, clarifying it's fully automated and never needs player input.

---

## H. Loop

1. **[BIG]** A third trading partner beyond Trade Link and Regional Partner (H8), with its own distinct cost/supply ratio, extending the network layer.
2. **[SMALL]** Let the closed-loop streak tracker (H19) show its current streak with a small flame-free (per this game's "no guilt UI" spirit) progress indicator.
3. **[BIG]** A "supply chain redesign" late-game layer — once fully circular, let the player optimize further by choosing which specific measure (repair/reuse/recycle) to over-invest in for a small efficiency bonus, adding depth after the main loop closes.
4. **[SMALL]** Let the alternate goods-flavor sets (H20) be switchable mid-session as a cosmetic-only relabeling, not just at game start.
5. **[BIG]** A "circular economy index" community comparison — aggregate stats on average circular-fraction reached across all players, reinforcing the hope-angle's "this is achievable" message at scale.
6. **[SMALL]** A small animated particle burst (extending H12) specifically on the moment circular fraction crosses each 25% milestone, not just export revenue.
7. **[BIG]** A "product lifecycle" vignette expansion — let the single-item vignette (Pass 2) follow a specific named product across multiple cycles, building a small ongoing narrative thread rather than a fresh vignette each time.
8. **[SMALL]** Let the cost-per-unit-of-supply readout (H4) show a small trend indicator (getting cheaper/pricier) alongside the current value.
9. **[BIG]** A "waste stream diversification" mechanic — let the player specialize in recovering a specific material type for a bonus, adding a light specialization choice to the three circularity investments.
10. **[SMALL]** A tooltip on the "time to close the loop" projection (H6) explaining it's an estimate based on current investment pace, not a guarantee.
11. **[BIG]** A "regional recycling network" — connect to a shared community pool where excess recovered material from one player could (in aggregate, anonymized) represent value for others, a stretch feature needing real backend support.
12. **[SMALL]** Let the score breakdown (H17) show a small pie chart of score sources, not just numbers.
13. **[BIG]** A "circular design challenge" scenario mode — start with a deliberately hard-to-close chain (a goods category with historically low circularity) as an opt-in harder variant.
14. **[SMALL]** A small badge for trying all available goods-flavor sets (H20) across different sessions.
15. **[BIG]** A "loop efficiency audit" panel — a periodic optional deep-dive showing exactly where supply is being wasted (evaporating surplus, underused capacity) with actionable suggestions.
16. **[SMALL]** Let the first-time-closed-loop banner (H3) include the exact cycle number it happened on, for bragging-rights context.
17. **[BIG]** A "consumer behavior" mechanic — let the player invest in demand-side changes (encouraging reuse/repair culture) as a mechanic distinct from supply-side circularity investment.
18. **[SMALL]** A small glow on the loop-ring visualization's node that's currently receiving the most investment, highlighting where attention is going.
19. **[BIG]** A "circular economy scorecard" comparing the player's actual achieved circularity against several real-world sector benchmarks simultaneously (H9 already has "a few alternate comparisons" — this extends it into a proper side-by-side chart).
20. **[SMALL]** Let the alternate vignette phrasings (H14) rotate randomly among the fraction-bucket's options rather than always showing the same one, for variety on repeat sessions.
21. **[BIG]** A "material passport" mechanic — track a piece of material's full journey (extracted → made → used → recycled → made again) as a literal traceable object, making circularity concrete rather than aggregate.
22. **[SMALL]** A tooltip explaining the hard-ceiling note (H10) with the exact multiplier value inline, not just "a hard ceiling."
23. **[BIG]** A "zero-waste challenge" mode — a stricter variant where the extraction meter must stay below a hard cap, forcing near-total circularity rather than merely rewarding it.
24. **[SMALL]** A small running count of "cycles since last new extraction," visible once circularity is high, as an informal streak.
25. **[BIG]** A "trade network visualization" upgrade — a small diagram showing both trade partners and the internal loop simultaneously, rather than separate readouts for each.
26. **[SMALL]** Let the reactive pulse on the trade-network display (H18) vary in intensity based on the size of the change, not a flat pulse regardless of magnitude.
27. **[BIG]** A "community goods category" vote/rotation — periodically feature a specific goods category as the "challenge of the week" for players who want a shared starting point to compare notes on.
28. **[SMALL]** A one-time tooltip the first time Regional Partner (H8) becomes available, distinguishing it from Trade Link before the player has to guess from the two buttons alone.
29. **[BIG]** A "circular supply chain map" — a visual network diagram (nodes for extraction/manufacturing/use/disposal/trade partners) replacing or supplementing the current linear-flow visualization, making the "redesign a system" framing more literal.
30. **[SMALL]** Let the "Start New Chain" reset (H7) show the two lifetime counters that survive (chains completed, categories tried) in the confirmation message, so the player sees what persists before resetting.

---

## I. Drift

1. **[BIG]** A second receiving region — manage two regions with different starting capacity/pressure profiles simultaneously, extending the "how prepared is prepared enough" question across a comparison rather than one region alone.
2. **[SMALL]** Let the passive unmanaged control region (I17) show its wellbeing trend on the same trend graph as the player's own region, for a direct visual comparison.
3. **[BIG]** A "policy toolkit" mechanic — let the player choose among a few real-world-grounded institutional policy levers (streamlined credentialing, language-access funding) as named investment options rather than the current abstract housing/services/infrastructure split.
4. **[SMALL]** A tooltip on the accelerated-severity toggle (I13) stating the exact multiplier, matching the fix already made for its title attribute — surface it visibly, not just on hover.
5. **[BIG]** A "generations forward" interactive coda — instead of a static long-horizon outcome, let the player make one or two final symbolic choices that flavor (not mechanically alter) the epilogue text, deepening the existing coda without adding real new systems.
6. **[SMALL]** Let the session-milestone summary (I11) include a small trend indicator (improving/plateauing/declining) alongside the snapshot numbers.
7. **[BIG]** A "regional network" mechanic — let a well-prepared region optionally support a struggling neighboring region (light connection to the two-region idea above), reflecting real inter-regional cooperation.
8. **[SMALL]** A small icon distinguishing the three composite wellbeing sub-scores (services/economy/cohesion) in every place they're shown, beyond the existing three-bar dashboard.
9. **[BIG]** A "capacity planning" forecast tool — let the player see a projected arrivals curve for the next N rounds (based on current background severity), enabling proactive rather than purely reactive investment.
10. **[SMALL]** Let the net-positive turning-point badge (I19) show the exact round it was reached, not just that it happened.
11. **[BIG]** A "thriving region" showcase mode — once a region reaches the Thriving wellbeing band, unlock a short optional "what this region looks like now" descriptive vignette, institutional in framing per this game's sensitivity note.
12. **[SMALL]** A tooltip explaining exactly what "unmanaged control region" (I17) represents and why it's shown, for a player encountering it without context.
13. **[BIG]** A "resettlement outcome" real-data comparison mode — let the player's region's integration rate be compared directly against the real 89% benchmark (I9) as a live in-session stat, not just an Info Page citation.
14. **[SMALL]** Let the target marker on wellbeing gauges (I14) be labeled with the exact threshold number, not just a visual line.
15. **[BIG]** A "crisis-to-recovery" narrative mode — an opt-in harder start (already-strained region) specifically to demonstrate the "not too late" message even from a bad starting position.
16. **[SMALL]** A small badge for reaching the Model Region tier via a from-behind recovery, distinct from reaching it via steady management.
17. **[BIG]** A "community capacity index" — an aggregate stat (once Z's cross-game endpoint exists) showing average regional wellbeing across all players, framed institutionally per this game's tone.
18. **[SMALL]** Let the free-text tone/framing feedback field (I18) show a short explanatory placeholder about what kind of feedback is useful there.
19. **[BIG]** A "resource reallocation" mid-run mechanic — let the player shift already-committed capacity between housing/services/infrastructure at a small cost, adding flexibility for correcting an early misallocation.
20. **[SMALL]** A one-time callout the first time the arrival-dot stream's density (I16) visibly changes due to a difficulty toggle, so the connection is clear.
21. **[BIG]** A "long-horizon divergence" comparison — show the coda's generations-later outcome side by side for both the player's region and the passive control region (I17), making the long-run stakes of preparedness concrete.
22. **[SMALL]** Let the funds-to-economic-health scale reference (I20) be shown as a small always-visible conversion note, not just discoverable once.
23. **[BIG]** A "regional identity" light customization — let the player name their region once, carried through the whole session and into the coda, giving the long-run narrative a bit more personal stake (institutional framing preserved).
24. **[SMALL]** A small trend arrow next to each of the three composite sub-scores, showing direction of change each round.
25. **[BIG]** A "second wave" mechanic — after initial arrivals integrate, a second, larger wave tests whether the region's now-improved capacity holds up under greater pressure, extending the timeline meaningfully.
26. **[SMALL]** Let the comfortably-ahead dimension callout (I12) name the specific sub-score that's ahead, not just note that one exists.
27. **[BIG]** A "capacity investment ROI" dashboard — show exactly how much each dollar invested in housing/services/infrastructure has returned in integration contribution, making the net-positive mechanic's math legible.
28. **[SMALL]** A tooltip explaining exactly what triggers the strain-level consequence descriptions (I6), so a player understands the threshold, not just the label.
29. **[BIG]** A "cross-region learning" mechanic — once one region reaches Thriving, unlock a small permanent efficiency bonus applicable to any future region managed, an Aftermath-style meta-progression scaled to this game's institutional framing.
30. **[SMALL]** A small "rounds until next capacity milestone" estimate, based on current investment pace, similar to Herd's investment-consequence preview.

---

## J. Trade Empire

1. **[BIG]** A fourth self-contained expansion cluster beyond the home system and Kepler Cluster, requiring an even deeper research investment, extending the galaxy-scaling arc.
2. **[SMALL]** Let the per-route profitability readout (J11) show a small trend arrow (improving/declining) based on recent trips.
3. **[BIG]** A "trade guild" mechanic — a light NPC faction offering occasional bulk contracts (deliver X units of Y to Z by a deadline) for bonus rewards, adding structured objectives beyond the open-ended economy.
4. **[SMALL]** Let the historical price sparkline per good (J12) show the exact current price as a labeled point, not just the trend line.
5. **[BIG]** A "fleet composition" upgrade — let the player choose among a few distinct ship archetypes (cargo-heavy/fast/balanced) at purchase time, rather than every ship being functionally identical.
6. **[SMALL]** A tooltip explaining exactly what Fleet Priority's target-ring visualization (J16) is pointing at, for a returning player who's forgotten.
7. **[BIG]** A "colony investment" mechanic — let the player directly fund a colony's development (beyond just delivering its needed good), accelerating its growth/specialization for a cost.
8. **[SMALL]** Let the warning badge for an idle manual ship (J15) show exactly how many ticks it's been idle, not just a static badge.
9. **[BIG]** A "market speculation" layer — let the player stockpile a good during a price crash and sell during a later recovery, adding a genuine trading-strategy dimension beyond simple production/consumption matching.
10. **[SMALL]** A small animated docking/undocking visual on the map when a ship arrives/departs, beyond the existing moving-dot representation.
11. **[BIG]** A "trade route insurance" mechanic — a small recurring cost that protects against a rare route-disruption event, introducing light risk-management without the "no external threats" design constraint's combat/piracy angle.
12. **[SMALL]** Let the ship-rename feature (J10) support a quick "reset to default name" option.
13. **[BIG]** A "galactic economy overview" dashboard — a single screen summarizing every colony's need/supply state at once, extending J14's per-colony sparkline into a full-galaxy view.
14. **[SMALL]** A small badge for a ship that's completed N round trips on the same route, an informal "veteran hauler" marker.
15. **[BIG]** A "research specialization" branch — let the player choose between an automation-focused or a market-focused research path once the tree grows large enough to support real branching.
16. **[SMALL]** Let the endgame galaxy-dot canvas (J20) respond to mouse hover with a small info tooltip per dot, rather than being purely decorative.
17. **[BIG]** A "player-run trade post" mechanic — once automation is maxed, let the player establish a passive trade post that generates income without needing an assigned ship, distinct from the existing background-galaxy trickle.
18. **[SMALL]** A tooltip on the automate button reminding the player automation is a one-time, non-reversible choice per ship (matching J19's own confirm-dialog framing).
19. **[BIG]** A "colony rebellion/loyalty" mechanic — chronically under-served colonies occasionally demand a one-time concession, adding light consequence to persistently ignored needs without a hard fail-state.
20. **[SMALL]** Let the market-crashed styling (`.market-price--crashed`) include a small recovery-ETA estimate in its tooltip.
21. **[BIG]** A "trade empire legacy" meta-progression — once the endgame state is reached, let a fresh game start with a small permanent bonus, an Aftermath-style replay incentive for this otherwise single-arc game.
22. **[SMALL]** A small particle/spark effect on a successful high-value sale, distinct from the existing profit-tick feedback.
23. **[BIG]** A "diplomatic relations" layer between the home system and Kepler Cluster — let sustained trade volume between the two unlock a small permanent efficiency bonus, rewarding genuine cross-system integration.
24. **[SMALL]** Let the colony detail sparkline (J14) show a small "needs met %" summary number alongside the graph.
25. **[BIG]** A "fleet-wide efficiency report" — a periodic optional panel showing exactly which ships/routes are underperforming, similar in spirit to Loop's proposed loop-efficiency-audit idea.
26. **[SMALL]** A tooltip on the research panel's locked nodes explaining exactly what's still needed to unlock them, not just that they're locked.
27. **[BIG]** A "trade empire almanac" — a lightweight in-game reference documenting each good's typical price range and which colonies produce/need it, reducing reliance on memorization.
28. **[SMALL]** Let the one-time first-automated-ship callout (J17) show a small congratulatory animation, not just text.
29. **[BIG]** A "seasonal demand" mechanic — periodic, predictable shifts in which goods are in higher demand, adding light planning depth to route assignment.
30. **[SMALL]** A small map legend explaining the automated-vs-manual diamond/circle ship-dot distinction (already colorblind-safe per J18) for a first-time viewer.

---

## K. Continuum

**A note on audience for this section specifically, per your own request:** you asked for Continuum's round-2 ideas to target a specific audience — 40-year-old men in the tech industry in California, your dad's friends — and to do real research on what that audience actually responds to before writing this list. Quick, honest summary of what a web search actually turned up (not exhaustive, treat as a starting signal, not a finished study): this age/industry cohort's nostalgia anchors are the SimCity/Civilization/Anno era of city-builders, they gravitate toward genuinely deep, spreadsheet-friendly optimization systems (Frostpunk 2's hard societal tradeoffs, Anno's supply chains) over casual/mobile-tycoon simplicity, and there's a whole adjacent niche of tech-industry-themed sims (Silicon Valley/startup tycoon games) that confirms this group enjoys seeing their own professional world reflected back at them — though Continuum's own "SDG 11, one continuous city" identity shouldn't be bent into a startup-tycoon pastiche to chase that. The ideas below lean into: nostalgia-coded UI/framing nods, genuine numeric/optimization depth, competitive comparison (this group likes benchmarking), and letting the Digital/Space Age eras' tech themes resonate a little more directly with a tech-professional's own frame of reference — without breaking the no-teaching-on-the-nose design philosophy already established.

1. **[BIG]** A "city planner's dashboard" — an optional dense, data-forward overlay (numeric readouts for every stat at once, styled like a real ops dashboard) as an alternate view mode alongside the 3D scene, directly serving the spreadsheet-optimizer instinct this audience skews toward.
2. **[SMALL]** A small "founded [year]" plaque-style readout on the main screen, giving the city a persistent sense of real institutional history the way a real municipal website might.
3. **[BIG]** A "benchmark your city" comparison mode against the aggregate of all other players' cities at the same era (once Z's cross-game endpoint exists) — this audience responds well to competitive/comparative framing.
4. **[SMALL]** A subtle SimCity-era-style isometric camera preset option alongside the existing Overview/Close-up/Aerial presets (K6), as a deliberate nostalgia nod for players who grew up on that specific visual language.
5. **[BIG]** A "policy log" — a running, dated ledger of every major research/infrastructure decision made, styled like a city council's meeting minutes, giving the game's existing story system a bureaucratic-nostalgia flavor this audience may find charming rather than dry.
6. **[SMALL]** Let the research tree's search/filter (K14) support filtering by branch (provision/community/craft) as quick-toggle chips, not just a text search.
7. **[BIG]** A "civilization summary" end-of-playthrough report (K5, still open) — go further than a plain recap: frame it like an annual shareholder/stakeholder report, complete with a scored "sustainability rating," directly speaking this audience's professional idiom without breaking character.
8. **[SMALL]** A small efficiency-per-capita readout always visible in the HUD, appealing directly to the optimization instinct (this is literally the metric the sustainability score already rewards — just surface it more prominently).
9. **[BIG]** A scenario/difficulty select at new-game start (K12, still open) — include a "hard mode: resource-scarce start" specifically, since this audience tends to seek out difficulty as a mark of mastery once the base game is understood.
10. **[SMALL]** A small "years since last unrest event" streak counter, mirroring Grid's clean-streak idea, rewarding sustained stability visibly.
11. **[BIG]** A "civic engineering challenge" mode — periodic optional constraints (build the next tier using 20% less resource extraction) as opt-in mini-challenges within an ongoing playthrough, appealing to the same instinct that makes speedrunning/challenge-runs popular with this demographic.
12. **[SMALL]** A tooltip on each research node showing its exact numeric effect (e.g. "+20% food yield") directly in the tree view, not requiring a click to see the delta.
13. **[BIG]** A "my city vs. history" comparison — since the game already tracks real per-era sustainability data via its info panels, let the player's own city's trajectory be plotted against a real historical reference curve for the same era, a direct, satisfying "am I doing better than real history" comparison.
14. **[SMALL]** A small day/night cycle toggle (K17, still open) that can be paused on a specific time-of-day for screenshot purposes — this audience values shareable, portfolio-quality screenshots.
15. **[BIG]** A "founder's log" — let the player write (or select from templated) short personal annotations at each era transition, creating a lightweight but genuinely personal record of their own playthrough's story, distinct from the game's own scripted transition beats.
16. **[BIG]** An optional stricter "hard mode" sustainability variant (K18, still open) with meaningfully tighter livability thresholds, framed explicitly as a mastery challenge for players who've already completed a normal run.
17. **[SMALL]** A small "efficiency rank" badge (Bronze/Silver/Gold city) computed from the final sustainability score, giving completion a tiered outcome rather than binary pass/fail.
18. **[BIG]** A "settlement archive" — a proper gallery of every past completed playthrough's final city (a snapshot of stats + a screenshot), letting a player compare their own historical attempts against each other.
19. **[SMALL]** A small real-world GDP-per-capita-style reference line on the resource-balance graph, grounding the abstract number in a familiar economic framing this audience already understands professionally.
20. **[BIG]** A "shareable settlement snapshot" (K13, still open) rendered as a clean, professional-looking infographic card (stats + a 3D-scene screenshot) — genuinely good enough to post, matching this audience's taste for polished, shareable artifacts.
21. **[SMALL]** A small "tech tree completion %" readout, appealing to the completionist instinct alongside the sustainability score.
22. **[BIG]** A "consulting mode" — an optional harder scenario where the player takes over a pre-built, already-struggling city and must turn it around, rather than always starting from Tribal-era scratch — a genuinely different, resonant framing for players who enjoy "turnaround" narratives (a strong tech-industry professional trope).
23. **[SMALL]** A small "next tier unlocks in ~N research points" estimate on locked research nodes, based on current knowledge production rate.
24. **[BIG]** A "civic infrastructure map" overlay — a simplified 2D top-down schematic view of building placement/density, distinct from the 3D scene, for players who prefer a data-dense planning view over the cartoonish render.
25. **[SMALL]** A small "livability vs. growth" scatter-plot mini-graph tracked across the whole playthrough, visualizing the core tension as an actual chart rather than only two live numbers.
26. **[BIG]** A "space age expansion" epilogue — once Space Age's habitat capacity is maxed, an optional short "what comes after" narrative epilogue closing out the sever-era arc properly, giving the ending more weight than a plain completion state.
27. **[SMALL]** A small keyboard-shortcut cheat-sheet overlay (accessible via a "?" key), a small but real quality-of-life touch this audience — often keyboard-shortcut-fluent from professional tool use — would likely notice and appreciate.
28. **[BIG]** A "resource flow diagram" — an optional Sankey-style visualization of how resources move through the current era's production chain, directly appealing to the systems-visualization aesthetic common in data/tech-adjacent tooling.
29. **[SMALL]** A small "time played this city" readout, purely informational, satisfying the instinct to track invested effort the way a professional tracks hours logged.
30. **[BIG]** A "peer city" async ghost feature — show a faint, non-interactive overlay of what an anonymized top-scoring city's building layout looked like at the same era, without full multiplayer complexity, giving a taste of comparison/inspiration this competitive-leaning audience would likely respond to.

---

## L. Le Champ de Mots

1. **[BIG]** A fifth arcade minigame beyond the current four (Blitz/Verb Racer/Boutique Dash/Café Rush), covering a sequence range not yet dedicated to one (e.g. the passé composé/partitive weeks).
2. **[SMALL]** Let the visual-style switcher (Milestone 32) remember a per-context preference — e.g. Cartoon for casual review, Text-based for a focused cram session — via two saved presets instead of one single choice.
3. **[BIG]** A "weak spot drill" mode — a dedicated practice session generated purely from the error-pattern digest's flagged topics, rather than the normal spaced-repetition queue.
4. **[SMALL]** A small "days until next FREN152 week unlocks" estimate for rows still gated by real course pacing.
5. **[BIG]** A "conversation simulator" — a longer-form practice mode chaining several related vocab/grammar items into a short simulated dialogue exchange, going beyond single-item recall prompts.
6. **[SMALL]** Let the confidence-rating buttons ("Sure"/"Unsure") show a small running accuracy-by-confidence stat, so the player can see whether their self-assessment is well-calibrated.
7. **[BIG]** A "study streak calendar" — a lightweight monthly calendar view showing which days had review activity, without introducing the guilt-driven streak-fire framing this design explicitly avoids.
8. **[SMALL]** A small "plots automated" progress bar always visible at the top of the farm, summarizing overall mastery at a glance.
9. **[BIG]** A "listening comprehension" practice type — audio-based prompts (text-to-speech, since there's no voice-recording pipeline) for phonetic and vocab items, extending beyond the current typed/multiple-choice formats.
10. **[SMALL]** Let the gender-tagging drill show a small running accuracy stat specific to that drill type, separate from the overall progress dashboard.
11. **[BIG]** A "sentence builder" freeform mode — instead of only the bonus sentence-building sections tied to specific weeks, a general-purpose sentence constructor usable with any mastered vocabulary at any time.
12. **[SMALL]** A small "next review due" countdown on each automated plot, so a player curious about the SRS scheduling can see it directly rather than it being fully invisible.
13. **[BIG]** A "study buddy" pacing coach — a light, opt-in daily suggested review-session length based on how many plots are currently due, distinct from the existing calm "plots needing water" counter.
14. **[SMALL]** Let the report-button flow show a short "thanks, noted" confirmation distinct from the normal question-feedback flow, so reporting a possible error feels acknowledged.
15. **[BIG]** A "grammar deep-dive" panel per grammar topic — an optional expanded explanation beyond the terse rule shown during practice, for players who want the "why," not just the pattern.
16. **[SMALL]** A small visual distinction (border color or icon) between vocab, grammar, phrase, and phonetic plot types on the farm grid itself, beyond the existing stage-based sprite.
17. **[BIG]** A "mixed review marathon" mode — a long-form session pulling due plots from across the entire farm regardless of row, for a player who wants one big review rather than row-by-row.
18. **[SMALL]** Let the weeds mix-up state show a small "these two are often confused" note explaining exactly which other item it's being mixed up with.
19. **[BIG]** A "personal phrasebook" — let the player bookmark specific items they find personally useful/tricky into a custom cross-cutting list, independent of the syllabus row structure.
20. **[SMALL]** A small "catch-up progress" readout for the 11 already-unlocked FREN151 rows, distinguishing "reviewed since unlocking" from "never yet watered."
21. **[BIG]** A "pronunciation practice" mode building on the existing pronunciation-risk reporting — record-free, but offering a slowed-down text-to-speech playback plus a visual syllable breakdown for tricky words.
22. **[SMALL]** Let the cultural-notes toggle show a small "new note available" indicator when a freshly-unlocked row has cultural context worth reading.
23. **[BIG]** A "spaced repetition transparency" panel — an optional, fully explained view of exactly how the SM-2-style scheduling works for a curious player, turning the "under the hood" mechanic into an optional teaching moment about SRS itself.
24. **[SMALL]** A small animated watering-can cursor/effect when actively watering a plot, adding a touch of tactile feedback to the core interaction.
25. **[BIG]** A "review before the exam" cram mode — a dedicated, denser review session covering everything from a chosen chapter range, for pre-test studying distinct from the normal paced farm progression.
26. **[SMALL]** Let the liaison/elision quiz show a small phonetic-symbol legend, for a player who's forgotten what a specific symbol represents.
27. **[BIG]** A "farm-wide health" summary visualization — a single glanceable chart (not per-row) showing the whole farm's mastery distribution (how many plots at each stage), for a bird's-eye view of overall progress.
28. **[SMALL]** A small badge/icon for perfectly answering a full row's worth of plots in one sitting.
29. **[BIG]** A second, standalone mini-game family beyond the arcade minigames — a lighter, more frequent "quick water" mode (a single rapid-fire question, no full minigame session) for very short study breaks, distinct from the four full arcade games' own sequence-range gating.
30. **[SMALL]** Let the achievements panel's "View achievements across every game" hub link open in a way that preserves the current visual style choice when navigating back, rather than resetting to default.

---

## Z. Games (things worth doing across many/all games, not any single one's own feature)

1. **[BIG]** A cross-game aggregate-stats backend endpoint (the shared infrastructure several per-game ideas above depend on — Grid's C11, Canopy's aggregate comparison, Continuum's benchmark mode, etc.) — one real decision and one real build, rather than each game separately floating the same "needs a new endpoint" caveat.
2. **[SMALL]** A consistent "last played" per-game timestamp stored client-side, surfaced on the hub's own title cards (distinct from Y's "last updated" badge, which is about the site, not the player's own history).
3. **[BIG]** A genuinely shared "meta-progression" pattern — several games above independently proposed an Aftermath-style small-bonus-carries-forward system (SOL's New Game+ variant, Herd's farm succession, Drift's cross-region learning); worth designing ONE shared pattern/module rather than each game inventing its own shape from scratch.
4. **[SMALL]** A consistent keyboard-shortcut convention across every game (Canopy already has plot-navigation shortcuts; Continuum's idea above proposes a cheat-sheet) — audit and align on a shared minimal set (e.g. `?` for help, `Esc` to close any open panel).
5. **[BIG]** A shared "challenge mode" pattern — several games proposed their own harder/stricter variant (Continuum's hard sustainability mode, Grid's emergency-response mode, Tide's storm-season layer); a shared naming/UI convention for "this is the harder version of this game" would make the site's difficulty options feel like one coherent feature, not 12 one-offs.
6. **[SMALL]** A shared small CSS utility for "record/personal-best" badges — several games (SOL, Canopy, Tide, Thaw, Grid) each built their own version of a "new best!" flash; consolidate into one shared, consistently-styled pattern.
7. **[BIG]** A genuine site-wide "replay value" audit — now that every game has achievements/settings/changelog, step back and ask which games still lack ANY reason to play twice (several of the climate-quartet games are single-arc, one-and-done sessions) and decide, game by game, whether that's fine (they're teaching tools, not endless games) or worth a light meta-progression pass.
8. **[SMALL]** A shared "export my progress" pattern — several games (Aftermath's E12, this list's own proposals for SOL/others) want a portable progress code outside the save-widget system; one shared helper function/module instead of each game reinventing base64-blob export.
9. **[BIG]** A genuine cross-game "campaign" framing — an optional, purely presentational hub feature that tracks a player's progress across ALL 12 games as one combined journey (a checklist, a combined completion percentage), giving the site itself a sense of a larger single experience beyond 12 separate demos.
10. **[SMALL]** A consistent "difficulty variant" icon/badge shown on a game's title card when it has one active, so a returning player can tell at a glance which games have unlockable harder modes.
11. **[BIG]** A shared "narrative log" component — Continuum's ongoing-log system, Thaw's proposed scientist's-log, and Le Champ de Mots' report-confirmation flow are all variations on "a small dated feed of things that happened"; worth a genuinely shared, reusable module rather than three separate implementations.
12. **[SMALL]** A consistent placement convention for the achievements/settings/changelog toggle buttons across every game's toolbar — a quick visual audit to confirm they're not landing in a different order/position per game, purely for muscle-memory consistency.
13. **[BIG]** A real "onboarding survey" — a single optional, lightweight first-visit prompt (which subjects interest you? do you prefer quick or deep games?) feeding into the hub lobby's tag-filter defaults, personalizing the very first thing a new visitor sees.
14. **[SMALL]** A shared small helper for "time since last played" freshness badges (distinct from the changelog's own dates) — useful groundwork for idea #2 above.
15. **[BIG]** A genuine accessibility pass beyond colorblind-safety and text-scale — a real screen-reader audit across at least the achievements/settings panels (ARIA labels, focus order), since none of this session's accessibility work has specifically verified screen-reader compatibility yet.
16. **[SMALL]** A consistent "report a bug/typo" affordance inside every game (Le Champ de Mots already has a report button for pronunciation-risk items) — audit whether the other 11 games have an equivalent lightweight in-game reporting hook, or only the general site-wide feedback form.
17. **[BIG]** A shared "comparison/benchmark" UI pattern — several games above want a "your result vs. a real-world/community reference" chart (Grid's global line, Continuum's history comparison, Herd's real-world %); consolidate into one reusable chart component with swappable reference-data sources.
18. **[SMALL]** A quick audit of every game's mobile viewport at the very narrowest common phone width (320px, not just 375px) to catch any remaining edge-of-screen clipping the 375px-focused testing this session used might have missed.
19. **[BIG]** A genuine "New Player" landing flow — since the hub now has 12 games plus tags/search, a first-time visitor might benefit from a single guided "start here" recommendation (e.g. suggest Canopy, the simplest game, as a first pick) rather than an undifferentiated grid.
20. **[SMALL]** A consistent emoji/icon set audit — confirm no two games are using the same emoji for meaningfully different concepts in a way that could confuse a player moving between games (e.g. a trophy meaning "achievement" everywhere, not "goal" in one game and "reward" in another).
21. **[BIG]** A shared "printable/exportable summary" feature — several games' end-of-session summaries (Canopy, Tide, Aftermath, Herd) could share one print-friendly CSS stylesheet, useful if any of this is ever used as physical BCM evidence.
22. **[SMALL]** A consistent "Reset progress" confirmation wording audit across every game now that the shared `ConfirmDialog` exists — several games still use their own bespoke confirm flow (SOL's `_confirm()`, Aftermath's two-click) predating the shared pattern; worth deciding whether to migrate them for consistency, or leave as intentionally varied.
23. **[BIG]** A genuine "seasonal content" pattern — a lightweight, shared mechanism for a game to show different flavor text/art on real-world dates (a small Easter egg layer), purely optional per game.
24. **[SMALL]** A shared small "what changed since you last played" banner — distinct from each game's own changelog panel, a one-line, non-intrusive banner comparing the current changelog's latest date against a `localStorage`-tracked "last visited" date per game.
25. **[BIG]** A genuine save-portability audit — confirm every game's save-code payload size is reasonable (some games now have quite rich state: achievements, run histories, changelogs) and hasn't silently grown unwieldy since the original save-system design.
26. **[SMALL]** A consistent "info page" discoverability pass — confirm the "The Real Story" button's exact wording/icon is identical across all 8 climate-quartet games (it should be, per the shared `info_page.py`, but worth a quick regression check now that so much else has shipped around it).
27. **[BIG]** A shared "difficulty-aware achievements" pattern — several games gate achievements behind default-difficulty assumptions; audit whether any achievement becomes impossible or trivially easy under a game's own hard-mode/difficulty-variant toggle.
28. **[SMALL]** A consistent loading-state indicator while Pyodide boots — confirm every game shows some visible "loading..." state rather than a blank screen during the (sometimes several-second) Pyodide startup, for a first-time visitor's patience.
29. **[BIG]** A genuine cross-game "credits/sources" aggregation page — a single page listing every real-world source cited across all 8 climate-quartet games' Info Pages plus Continuum's era sources, useful as consolidated BCM114/206 evidence.
30. **[SMALL]** A quick pass confirming every game's `favicon`/tab title is set correctly and distinctly (matching the new NoyvjGames branding), since several games may still carry a generic or missing `<title>`.

---

## Y. Home (the hub shell itself — index.html/script.js/style.css, not any individual game)

1. **[BIG]** A real "public roadmap" page (L19, still open per `planning/TODO.md`) — pull from actual git history/CLAUDE.md build notes rather than just milestone tables, per your own caution that a lot of this session's work happened outside the original milestone structure.
2. **[SMALL]** Let the hub's search/filter bar remember the last-used search term and tag filter across a page reload, via `localStorage`.
3. **[BIG]** A real admin-only aggregate stats/About page (L8, still open) — total plays, saves, accounts, achievements earned site-wide, visible only in admin view per your own scoping note.
4. **[SMALL]** A small "12 games and counting" or similar live game-count readout on the hub's own header/tagline, since the count itself is a small but real signal of the site's growth.
5. **[BIG]** A "claim your save" nudge (L15, still open) for anonymous players who've clearly invested real time — needs a real trigger heuristic (e.g. a save with a nontrivial play-time or achievement count, still unclaimed after N visits).
6. **[SMALL]** Let the review widget's star-rating show the current average as a small visual (filled/half-filled stars), not just the numeric "4.5 ★ average" text.
7. **[BIG]** A more visible "Add to Home Screen" PWA install prompt (L18) — this was explicitly parked in `LATER.md` pending your go-ahead; flagging it again here in case you're ready to proceed now that the site has matured further.
8. **[SMALL]** A small "you're signed in" persistent indicator visible even when scrolled past the account section (e.g. in a fixed corner badge), so a signed-in player always has a visible reminder achievements/saves are being tracked.
9. **[BIG]** A permanent service-worker cache-busting fix (L16, still open) — a proper cache-version scheme so `sw.js` doesn't need the "reload twice" workaround this whole session repeatedly had to use, which a real player would never think to do.
10. **[SMALL]** A small "new since your last visit" count badge on the What's New nav link itself, not just inside the page.
11. **[BIG]** A genuine site-wide dark/light theme toggle — deliberately deferred this round (L5's own decision note explains why: no light theme exists anywhere yet) but worth scoping as a real, dedicated design pass once you're ready to commit to building a second full color scheme across every game.
12. **[SMALL]** Let the hub's account section show a small "member since" date for signed-in users, a light but real touch of permanence.
13. **[BIG]** A "site tour" onboarding flow for first-time hub visitors — a very light, skippable walkthrough of the search/filter/tags/Continue Playing features, since the hub itself has grown a fair amount of its own UI this round.
14. **[SMALL]** A small footer with basic site info (a link to the GitHub repo if it's ever made public, a contact/feedback link, the site name) — the hub currently has no footer at all.
15. **[BIG]** A "community highlights" section — periodically feature a real (anonymized) high-scoring or notable playthrough from the aggregate stats, once that backend exists, giving the hub a living, community feel beyond a static game list.
16. **[SMALL]** A small loading skeleton/placeholder for the title-card grid while the ratings widget's async fetch resolves, instead of the "Loading reviews…" text popping in after a blank moment.
17. **[BIG]** A proper 404/error page for any broken game link, styled to match the hub rather than a bare browser error.
18. **[SMALL]** Let the account sign-out button show a brief "Signed out" confirmation message before the UI switches back to the signed-out view.
19. **[BIG]** A "site search" that also searches inside game descriptions AND each game's own changelog entries (once those exist site-wide), not just the visible title-card text — a deeper search than the current lobby filter.
20. **[SMALL]** A small "share this game" button per title card (copies a direct link), distinct from the review widget, for a visitor who wants to recommend a specific game to a friend.
21. **[BIG]** A genuine "what's popular" sort option on the hub lobby — sort title cards by rating average or review count, once enough real reviews exist to make that meaningful.
22. **[SMALL]** A small visual distinction on title cards for games with an active difficulty/challenge variant (tying into Z's idea #10 above), visible from the hub itself, not just inside each game.
23. **[BIG]** A proper terms-of-use/privacy-note page — even a personal project collecting accounts/saves/feedback probably deserves one short, honest page explaining what's stored and why, especially once real strangers (not just you) start signing up.
24. **[SMALL]** A small "random game" button for an undecided visitor, picking a random unplayed (per their save history, if signed in) title card.
25. **[BIG]** A genuine site-wide notification/announcement banner mechanism (distinct from the What's New page) for anything time-sensitive worth surfacing immediately (e.g. "AdSense just went live" or a maintenance notice) — dismissible, `localStorage`-tracked so it doesn't reappear once dismissed.
26. **[SMALL]** Let the achievements dashboard's overall progress bar show the exact fraction as a tooltip on hover, not just the visual bar width.
27. **[BIG]** A genuine "recently added" section on the hub lobby, separate from Continue Playing — surfacing the newest game(s) added to the site for a returning visitor who hasn't seen them yet.
28. **[SMALL]** A small consistent focus-ring style across all hub-level interactive elements (buttons, inputs, links) for keyboard-navigation clarity, auditing whether the current styling relies only on the browser default.
29. **[BIG]** A genuine hub-level analytics opt-in (privacy-respecting, e.g. a simple self-hosted pageview counter, not a third-party tracker) — purely to have real visitor-count data for BCM206 evidence purposes, distinct from the admin stats page's in-game data.
30. **[SMALL]** A small "back to top" floating button on the hub lobby once the page is scrolled past the fold, given how long the page now is with 12 title cards plus the account/filter sections above them.

---

## X. Warframe Build Tracker (personal project — not part of the hub; answers here route to `warframe_build_tracker/TODO.md`, not `planning/TODO.md`)

1. **[BIG]** The recursive refinery expansion already flagged in the tracker's own `TODO.md` — populate `MANUFACTURING_RECIPES` for the ~15-20 refined resources (Alloys, Toroids, Marquise-tier gems) that are themselves crafted from a raw material, so `flatten_recipe()`'s existing recursive support actually has something to expand.
2. **[SMALL]** A small "days since last data.json update" readout, purely informational, to see how actively the tracker is actually being used.
3. **[BIG]** A "build priority" sort/highlight — rank the 33 parts by "closest to buildable" (fewest missing resources) rather than the fixed Amp/Zaw/Kitgun category order, so the most actionable next build is always at the top.
4. **[SMALL]** Let the resource location tooltip show a small icon per planet/location, for faster visual scanning down a long resource list.
5. **[BIG]** A "farming route planner" — given the current shortfall list, suggest which single location would satisfy the most outstanding resource needs at once, since several resources share the same planet/location.
6. **[SMALL]** A small "reset all inventory to zero" confirmation-gated button, distinct from the existing per-part/per-resource manual editing, for starting a fresh farming push.
7. **[BIG]** A genuine "meta build" comment expansion — the existing category-level notes (Amp/Zaw/Kitgun) could grow into short per-part notes pulling from each part's own Wiki "Tips" section, the same honest, non-"current meta"-claiming approach already used for the category-level notes.
8. **[SMALL]** A small progress bar per category (Amp/Zaw/Kitgun) showing "X/Y parts complete," not just the overall 14/33-style single number.
9. **[BIG]** A "resource shopping list" export — a plain-text or copyable summary of exactly what's still needed, useful for cross-referencing against in-game trade chat or a squad-farming session.
10. **[SMALL]** Let the "used in" tab show the resource's own total remaining-needed count inline, not just which parts use it.
11. **[BIG]** A "relic/mission source" layer for resources still gated behind Void Relic drops rather than open-world farming, if any of the 65 resources actually work that way (worth checking) — extending beyond the current open-world-location-only model.
12. **[SMALL]** A small dark/light toggle for the tracker's own UI, purely a personal preference option since it's your own tool.
13. **[BIG]** A "build queue" feature — mark several ready-to-build parts and build them all in one click, rather than one Build click per part.
14. **[SMALL]** A small "last built" timestamp per part, so you can see your own farming/building history over time.
15. **[BIG]** A "resource value" heuristic — flag which currently-owned resources are rare/hard-to-farm (per their location data) vs. common, helping prioritize which builds to do first to avoid over-spending a scarce resource on a lower-priority part.
16. **[SMALL]** Let the Wiki links open in a way that's visually distinct for pages already visited this session (a tiny personal convenience, browser-native `:visited` styling might already half-cover this).
17. **[BIG]** A "companion/vacuum range" or other adjacent Warframe-tracking module, if the "even better tracker" ambition from the original README ever gets picked up — genuinely optional, since amp/kitgun/zaw parts were the explicit original scope.
18. **[SMALL]** A small favicon for the tracker itself (currently likely using Flask's default or none), matching the effort already put into the hub's own favicon.
19. **[BIG]** A "riven disposition" reference column for the completed Zaws/Kitguns/Amps, once built, since that's a natural next question after "is it built" for a Warframe player.
20. **[SMALL]** A small inline note on resources with unusually high quantity requirements (hundreds of units), flagging them as "grindy" so you know to prioritize a dedicated farming session.
21. **[BIG]** A "build comparison" mode — since Zaws/Kitguns/Amps are all modular (Strike+Grip+Link, Chamber+Grip+Loader, Prism+Scaffold+Brace), let the tracker suggest which UN-built combinations are closest to completion given current resources, not just track the ones already on your list.
22. **[SMALL]** A small manual "note to self" free-text field per part, for jotting down why a specific one is prioritized or deprioritized.
23. **[BIG]** A "session farming log" — a simple running log of resource-inventory deltas between tracker updates, giving a rough sense of farming rate over time.
24. **[SMALL]** A small confirmation toast ("Built!") on a successful Build click, distinct from the current page-reload-based feedback.
25. **[BIG]** A "what's blocking me" summary at the top of the page — the single resource currently blocking the most builds, computed from the "used in" data already gathered.
26. **[SMALL]** A small percentage-complete readout for the whole 33-part list, not just the fraction.
27. **[BIG]** A mobile-friendly layout pass, if the tracker is ever checked from a phone mid-farming-session rather than only at a desktop.
28. **[SMALL]** A small "copy resource name" button next to each resource, for quickly pasting into an in-game trade-chat search.
29. **[BIG]** A "market price reference" (Warframe.market or similar) integration — showing whether it's cheaper to farm or simply buy a specific missing resource with platinum, if that data can be sourced without hitting the same bot-protection wall the Wiki did.
30. **[SMALL]** A small "archive completed parts" toggle to hide fully-built parts from the main view, decluttering the list as more of it gets finished.
