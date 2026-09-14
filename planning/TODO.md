# Site-Wide TODO

The one living list, replacing the scattered planning docs' own "open items"/"stretch goals" sections. Built from your labeled answers in `IMPROVEMENT-IDEAS-2026-09.md` (all "yes" items, resolved), plus a pass through every other file in `planning/` pulling out anything still genuinely unresolved there. "Later" items (things you deferred, or that need more explanation first) live in `LATER.md` instead — not here.

Check items off (`[x]`) as they land. Ordered by priority (my call, per your instruction) — roughly: in-flight work first, then cross-cutting site-wide goals (most of these were flagged "yes but site-wide" across several answers), then per-game work, then the big standalone features, then the closing/meta tasks you explicitly asked to run last.

Le Champ de Mots is included here now that its own answers would apply — its 4th minigame batch is still finishing in the background; its own labeled section (M) will fold in once you've reviewed it, same as every other game.

---

## In flight

- [x] Le Champ de Mots Milestones 27-28 (Greetings & Basics Blitz, Verb Racer arcade minigames) — done, committed.
- [x] Le Champ de Mots Milestones 29-30 (Boutique Dash, Café Rush arcade minigames) — done, all 4 minigames complete, 517/517 tests green.
- [x] Continuum Phase 6 (hub nav integration) — done, see "Big standalone features" below.

---

## Site-wide goal: roll achievements out everywhere

*(Origin: L2, A2, K2, and the framework itself — `planning/ACHIEVEMENTS-SYSTEM-DESIGN.md` has the full technical pattern and §7's per-game checklist. SOL is the reference implementation.)*

Two things every game needs once achievements land there, on top of the base rollout (per A19/A20, "yes but site-wide"):
- An achievement-earned toast/popup at the moment it's unlocked (not just visible inside the panel).
- A link from the in-game achievements panel to the hub-wide dashboard.

- [x] SOL — 18 achievements + panel + hub dashboard (reference implementation).
  - [x] Retrofit: add the unlock-toast and hub-dashboard-link (built after SOL shipped, per A19/A20).
- [x] Canopy — 20 achievements + panel + unlock toast + hub-dashboard link.
- [x] Grid — 16 achievements + panel + unlock toast + hub-dashboard link.
- [ ] Tide
- [x] Aftermath — 19 achievements + panel + unlock toast + hub-dashboard link.
- [x] Herd — 18 achievements + panel + unlock toast + hub-dashboard link.
- [x] Thaw — 18 achievements + panel + unlock toast + hub-dashboard link.
- [x] Loop — 20 achievements + panel + unlock toast + hub-dashboard link.
- [x] Drift — 18 achievements + panel + unlock toast + hub-dashboard link.
- [ ] Trade Empire
- [x] Continuum — 19 achievements + panel + unlock toast + hub-dashboard link.
- [x] Hub-side `script.js` registration for SOL/Canopy/Grid/Continuum — each per-game dispatch above correctly left this out as out-of-scope for a single-game session (it's a shared file). Done as one pass touching only `script.js`, verified live by claiming fresh Canopy/Grid saves on a throwaway test account and confirming the hub dashboard shows all four games. Do this same registration step for every game below as its own achievements rollout lands.
- [ ] Le Champ de Mots — **retrofit, not fresh-build**: it already has a game-local achievements slice (its own Milestone 23), but with no `achievements.json` manifest and no hub-dashboard wiring. Reshape it into the cross-game pattern rather than building a second, parallel system.

---

## Site-wide goal: per-game settings panel

*(Origin: A9. One panel per game consolidating text-scale, sound, and animation toggles — Continuum's Phase 5 already built text-scale + a colorblind fix as separate controls; this is about giving every game the same consolidated panel Continuum improvised for itself.)*

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
- [ ] Continuum — consolidate its existing text-scale control into this panel rather than leaving it as a standalone toolbar button.
- [ ] Also add a site-wide dark/light theme toggle (L5) — decide whether this lives in the hub shell, each game's own new settings panel, or both.

---

## Site-wide goal: colorblind-safety audit

*(Origin: A10, reinforced by L5. Use the same Okabe-Ito-palette method Continuum's Phase 5 already ran and documented.)*

- [ ] SOL
- [x] Canopy — done as B9 (per-game dispatch, not folded into a separate site-wide pass): every plot-tile state now carries its own icon (Bare's gap closed) plus a CSS pattern overlay independent of hue. Not a straight Okabe-Ito hue swap like Continuum's — Canopy's state colors are continuous brown-to-green gradients, not a discrete red/green pair, so redundant coding (icon + pattern) was the applicable fix instead of re-picking a palette. See games/canopy/CLAUDE.md for the worked note.
- [ ] Grid
- [ ] Tide
- [ ] Aftermath
- [ ] Herd
- [ ] Thaw
- [ ] Loop
- [ ] Drift
- [ ] Trade Empire
- [x] Continuum — already done as part of Phase 5.
- [ ] Le Champ de Mots
- [ ] The hub shell itself (nav, buttons, review widget)

---

## Site-wide goal: onboarding-tooltip coverage check

*(Origin: A14 — "that should be in the how-to-play section, if not add it site-wide." Investigate first, only build where there's a real gap.)*

- [ ] For each game: check whether its existing Tutorial / How-to-Play already covers "a returning player who skipped the tutorial and forgot a mechanic." Where it doesn't, add a light contextual-tooltip pass rather than relying solely on the one-time walkthrough.

---

## Site-wide goal: "What's New" changelog

*(Origin: K16 "yes but site-wide (all games AND site)", plus L10's own separate hub-page ask — merged into one goal with two parts.)*

- [ ] Per-game in-game changelog panel (K16), for every game.
- [ ] A hub-level "What's New" page (L10), pulling from `BCM114-DEV-LOG.md`/`BCM206-DEV-LOG.md` — **scoped per your notes: brief bullet points + date only, not direct links into the dev logs, and collapsible by date** since some days have a lot logged.

---

## Site-wide goal: finish the mobile-dock rollout

*(Origin: several games separately asked for the same fix Canopy and Trade Empire already have — `shared/mobile-dock.js` docking a game's key action panel to the bottom of the viewport on mobile.)*

- [x] Canopy — action panel (already done).
- [x] Trade Empire — needs strip (already done).
- [x] Canopy — also extend to the stats/legend panels (B15).
- [x] Grid — plant-build action row (C1) — docked Advance Round instead (see games/grid/CLAUDE.md for the judgment call: Grid's plant rows already keep build/retire/maintain inline, no far-apart split to close).
- [ ] Tide — investments panel + Advance Season button (D1).
- [x] Aftermath — actions panel: Resilience/Growth/Face Next Event (E1).
- [ ] Continuum — doesn't have this pattern at all yet (K9).

---

## Site-wide goal: a shared confirmation-dialog pattern ("don't ask again")

*(Origin: three separate games asked for a confirm-before-spending step, and you flagged the same "won't this get annoying" concern each time — C14, F16, J19. Design ONE reusable pattern, not three one-off dialogs.)*

- [ ] Design the shared pattern: a confirm step with a persistent "don't show this again" opt-out (per-browser, e.g. `localStorage`).
- [ ] Apply to Grid: confirm before retiring the last remaining unit of a plant type (C14).
- [ ] Apply to Herd: confirm/undo window before the pricier Plant-Based Pivot buy (F16).
- [ ] Apply to Trade Empire: confirm before spending research points/automation credits (J19) — **first check how often this button is actually pressed** (your own concern); skip or soften if it's a common action, not a rare one.

---

## Site-wide goal: shared save-widget QoL fixes

*(Origin: two stale `REVIEW(documentation)` comments in `planning/SAVE-BUTTON-INTEGRATION.md` describing behavior the widget never actually had — copy-to-clipboard and load-field autofill. Worth actually building now rather than just correcting the docs, since both are small, genuinely useful, and touch exactly one shared file affecting every game at once.)*

- [x] Add a copy-to-clipboard button next to the displayed save code. Tries the Clipboard API first, falls back to a legacy `execCommand` copy on any failure, shows a plain "couldn't copy" message rather than failing silently if both are blocked (verified: this browser pane's own sandbox denies clipboard-write entirely, and the fallback chain degrades gracefully exactly as designed).
- [x] Auto-fill the "load by code" input with the last remembered code for this game. Only fills when the field is empty, so it never overwrites a code the player is actively typing in.
- [x] Fix the two stale doc comments in `planning/SAVE-BUTTON-INTEGRATION.md` — rewritten to describe the actual behavior now that it's built.

---

## Site-wide goal: hub lobby improvements

*(Origin: L11, L12, plus your own added notes.)*

- [ ] Search/filter on the hub lobby (L11).
- [ ] A "games you have saves for" section pinned to the top for signed-in users, so a player who only plays 2-3 games sees those first (your addition to L11) — this overlaps with L4 ("continue where you left off"); build as one combined feature, not two.
- [ ] Tags per title card — not just length/depth (L12 originally suggested "quick" vs "deep systems"), but a general sorting/tagging system across the whole site, per your note that this could "start a general sorting system through the whole site." Decide the tag taxonomy (genre? subject? length?) before building.

---

## Per-game: SOL

- [x] A1: Prestige / "New Game+" layer after the soft win-state. Went with the simple version — a permanent flat resource-yield bonus per prestige level, not a skill tree (see `games/sol/CLAUDE.md`'s own build note for the full reasoning and what does/doesn't reset).
- [x] A2/A13: A second achievement wave — speedrun-style and "pure clicker/never automated" challenge runs. **Constraint from you: keep 100% achievable without extreme grinding or huge time investment.** (4 new achievements, generous timers/thresholds — see `games/sol/CLAUDE.md`.)
- [x] A3: A "welcome back" return-visit summary toast.
- [x] A4: A lifetime-stats screen.
- [x] A6: Layer in the icon/visual layer the design doc always left room for — **only if straightforward**; if it turns into a real asset-pipeline project, downgrade to `LATER.md` instead of forcing it. Found this was already solved via a pure-CSS icon system with zero markup changes needed — no `LATER.md` downgrade needed.
- [x] A8: A shareable "my solar system" end-state summary card.
- [x] A11: A visible "governor efficiency" readout.
- [x] A15: Visual terraforming feedback (color shift as `terraform_progress` climbs).
- [x] A16: A simple research-tree diagram instead of a flat list.
- [x] A17: An ecology warning banner at the 25%-output-penalty threshold.
- [x] A18: A "reset this world only" option.

---

## Per-game: Continuum

- [ ] K5: A "civilization summary" end-of-playthrough report.
- [x] K6: Named camera presets in the 3D scene — Overview/Close-up/Aerial buttons above the 3D view (`render3d.js`'s `CAMERA_PRESETS`), reusing the existing drag-to-look camera math so a preset and a manual drag are indistinguishable to the camera itself; shown only alongside the live 3D view, hidden in 2D mode. Live-verified all three angles render distinctly with no console errors.
- [x] K7: A way to actually view a revisited era's snapshot in the 3D layer — closed a real pre-existing gap (there was no revisit UI at all yet, despite `save.py` fully supporting it since Milestone 4): built a new "Look Back" section (enter/exit buttons per completed era), and confirmed live that the 3D layer's `get_visual_state()` correctly reflects the revisited era's own snapshot automatically once the UI exists to trigger it.
- [x] K8: Confirm every info-panel source is a clickable outbound link — confirmed via `shared/info_page.py`'s renderer and live-checked across all seven eras; nothing needed fixing.
- [x] K10: A tutorial walkthrough via `shared/tutorial.js`, if it doesn't have one — already built (`CONTINUUM_TUTORIAL_STEPS` in `index.html`); confirmed present, no new work needed.
- [ ] K12: A scenario/difficulty select at new-game start.
- [ ] K13: A shareable "my settlement" snapshot image, exported from the 3D scene.
- [x] K14: A search/filter on the research tree (14 tiers across 3 branches now) — a text input filtering by name/blurb/branch, live-verified.
- [x] K15: Confirm accessibility settings (text-scale, colorblind fixes) persist through a real save/load, not just `localStorage` — confirmed this is deliberate, not a bug: both are browser-level preferences, not portable save state (baking a local text-size/view-mode choice into a cross-device save would be backwards). No fix applied, per the task's own "only fix if actually broken" instruction.
- [ ] K17: A subtle day/night or seasonal lighting cycle in the 3D scene.
- [ ] K18: An optional stricter "hard mode" sustainability variant.
- [x] K19: Confirm/extend distinct meshes per building type in the 3D scene — audited every era's building list against `render3d.js`; found one real gap (Sanitation Works, Industrial, had no mesh of its own beyond feeding the smoke-reduction math) and closed it with a distinct teal treatment-tank mesh. Every other era-specific building already had its own distinct shape.
- [x] K20: A proper hub title-card art pass — done as part of Phase 6 (below): a CSS-only thumb matching every other game's hand-drawn-gradient convention (no photographic-screenshot pattern exists anywhere on this hub to break from).
- [x] Achievements: 19 achievements + in-game panel + unlock toast + `achievements_earned` in `get_state()` (hub-side `script.js` registration still needed — out of scope for a `games/continuum/`-only dispatch, same caveat Canopy/Grid's own rollouts already noted above).

---

## Per-game: Canopy

- [x] B1: End-of-session summary screen. A player-triggered "Session Summary" panel folding in B6/B18/B20 together (stats recap, sparkline, shareable text, counterfactual line) — see `render_session_summary()` in `games/canopy/game.py`.
- [x] B2: "Reset session" button. Folded together with B13 into one `reset_session()` (see `games/canopy/game.py`) since both mean "rebuild the session from scratch."
- [x] B3: A second, unlockable forest region/biome. "Highland Grove" — a smaller (3×4), independent grid reusing the same Plot clear/replant/accrue mechanics (no biodiversity or stakeholder tension of its own), permanently unlocked once the main forest's standing value crosses 2,000. New "Second Growth" achievement (21st entry) fires on unlock. See `HIGHLAND_ROWS`/`render_highland_section()` in `games/canopy/game.py`.
- [x] B4: Coordinate-style plot labels.
- [x] B6: A history sparkline (income vs. standing value). Inline SVG in the Session Summary panel (B1), sampled once per tick, capped at 120 points.
- [x] B7: Save/compare two named playstyle runs. "Save as Run A"/"Save as Run B" snapshot the current stats to per-browser `localStorage` (survives a Reset Session, unlike everything else in the Session Summary panel); a comparison table renders once at least one slot is saved — see `save_playstyle_run()`/`playstyle_comparison_html()`.
- [x] B8: Hover/tap tooltips on plot tiles.
- [x] B9: A colorblind-safe pattern/icon overlay for plot states — fold into the site-wide colorblind audit above if that's more efficient than a one-off.
- [x] B10: Surface biodiversity as an explicit number.
- [x] B11: Diversify stakeholder requests to sometimes offer a positive trade-off. A new "incentive" request kind cycles in after every full pass through the original 3 "clear" reasons — accepting keeps the plot standing and pays a relations boost + funding bonus, declining costs nothing (see `STAKEHOLDER_KIND_INCENTIVE` in `games/canopy/game.py`).
- [x] B12: A visible badge for a pending stakeholder request when scrolled away.
- [x] B13: A larger-grid option as a difficulty/length variant. A "Large (9×8)" preset alongside the existing "Normal (6×6)", selectable via a dropdown that triggers a full session reset at the new size; the chosen size round-trips through the save-code system.
- [x] B14: A persisted "personal best" stat across sessions. (Per-browser, via `localStorage` — deliberately independent of the save-code system; see `games/canopy/game.py`'s `load_personal_best()`/`_maybe_update_personal_best()`.)
- [x] B16: Keyboard navigation for plot selection/action.
- [x] B17: A floating "+X value" animation on compounding ticks.
- [x] B18: A shareable end-of-session code/snippet. Plain-text bragging-rights summary (not a decodable save code) + copy-to-clipboard, in the Session Summary panel (B1) — see `share_snippet()`.
- [x] B19: A distinct "fully mature" cap-off visual for Recovered plots.
- [x] B20: A closing counterfactual line at session end. "If every plot had been left standing since the start, this forest would be worth about X" vs. actual standing value, in the Session Summary panel (B1) — see `counterfactual_message()`.
- [ ] **Unresolved — please clarify**: your answer to B15 talks about "overpinning" and worrying about too much being pinned, but B15 itself was "extend the mobile-dock treatment to the stats/legend panels," which has nothing to do with pinning. I've kept B15 itself as a plain yes (folded into the mobile-dock rollout goal above) but flagging this so you can tell me what B15's actual comment was meant to be about.

---

## Per-game: Grid

*(C6 marked "later" with no further comment — moved to `LATER.md` as-is.)*

- [x] C1 — folded into the mobile-dock rollout goal above.
- [x] C2: A battery/grid-storage plant tier. Storage-only (excluded from generation/renewable-share metrics); its one mechanical effect is buffering a renewable shortfall when Weather Variability (C4) is on.
- [x] C3: Attach disruption-event log lines to the specific plant/type that failed.
- [x] C4: Weather-variability-on-renewables as an opt-in hard mode.
- [x] C5: A proper end-of-run summary screen with a score breakdown. An on-demand "Run Summary" panel (Grid has no hard end-state to hang a literal end screen off) — score, average clean share, clean trend, funds breakdown, best streak, and the C17 counterfactual, all in one place.
- [x] C7: A plant-mix bar chart. Generation-only — battery (C2) has no row.
- [x] C8: A tipping-point callout at 50% cumulative renewable capacity.
- [ ] C9: Confirmation before retiring the last unit of a plant type — folded into the shared confirmation-dialog goal above.
- [x] C10: Show the exact aging/wear percentage.
- [ ] C11: The aggregate clean-score-across-players comparison Pass 2 floated but never built. Moved to `LATER.md` — needs a new shared backend aggregate-stats endpoint (`app/main.py`), which is bigger than a single-game scope and affects every game's live backend; worth a deliberate decision rather than a side-effect of a Grid-only session.
- [x] C12: A visible toast/banner for disruption events.
- [x] C13: A funds breakdown (build vs. maintenance vs. disruption-damage).
- [x] C15: An interactive trend graph (hover for exact values). Every point on all three trend lines now carries a native SVG `<title>` tooltip with the exact round/value.
- [x] C16: A "steeper demand growth" difficulty variant.
- [x] C17: A closing "grid vs. business-as-usual" counterfactual. A capacity-held-constant, coal-only shadow trajectory (`bau_emissions`), surfaced in the new C5 Run Summary panel.
- [ ] C18: Colorblind-safe trend-graph line differentiation — fold into the site-wide colorblind audit.
- [x] C19: A breakdown-risk badge once a plant type's average age crosses a threshold.
- [x] C20: A one-time first-use callout for Retire's refund / Maintain's cost math.

---

## Per-game: Tide

*(D10 and D20 marked "later"/"maybe later" — moved to `LATER.md`.)*

- [ ] D1 — folded into the mobile-dock rollout goal above.
- [ ] D2: A fourth adaptation tier.
- [ ] D3: A "seasons until next tile floods" estimate.
- [ ] D4: A numeric then-vs-now stat block.
- [ ] D5: A scrollable/expandable ticker history.
- [ ] D6: A "what if you'd invested earlier" counterfactual replay.
- [ ] D7: An end-of-session summary screen.
- [ ] D8: A highlight/flash on the coastline row the moment it floods.
- [ ] D9: An optional "harder lag" difficulty mode.
- [ ] D11: Colorblind-safe/textured coastline differentiation — fold into the site-wide colorblind audit.
- [ ] D12: A "worst season" callout.
- [ ] D13: A persisted "best coastline saved" stat.
- [ ] D14: An early-warning banner for a fish-yield crash already locked in.
- [ ] D15: A Grid-style historical mini-graph for acidity vs. fish yield.
- [ ] D16: Split the Output investment into a fishing/industry sub-choice.
- [ ] D17: A one-time "first flood" callout.
- [ ] D18: A player-chosen comparison-baseline checkpoint.
- [ ] D19: A hover/tap detail per coastline tile showing its flood threshold.

---

## Per-game: Aftermath

*(E5 marked "later" — moved to `LATER.md`.)*

- [x] E1 — folded into the mobile-dock rollout goal above.
- [x] E2: A fourth and fifth skill-tree node — Adaptive Growth Practices (+1 starting growth) and Mutual Aid Network (+5% mitigation).
- [x] E3: Branching/prerequisite structure for the skill tree — Mutual Aid Network requires both Reinforced Infrastructure and Community Reserves; locked skills show which prereqs are missing.
- [x] E4: Build out the "legacy system" beyond its current flavor-text line — a per-event-type weathered-count chip row, additive to the original single line.
- [x] E6: Another event category beyond weather/non-weather — a "social" category (Civil Unrest), replacing the schedule's second Storm slot to preserve the existing 7-event balance.
- [x] E7: Let players review a specific past run's full event-by-event breakdown — a new persisted run-log history + "Review Past Runs" panel.
- [x] E8: An "expected damage this event" preview before Face Next Event.
- [x] E9: A visible "X/5 skills unlocked" progress summary.
- [x] E10: A confirmation animation/state change when investment is spent — a brief flash on the resources readout.
- [x] E11: A proper end-of-run summary — final stats + full event-by-event breakdown, beyond the original one-line score.
- [x] E12: Export/import code for the localStorage-based skill tree and run history — a base64 progress code, separate from the per-run save widget.
- [x] E13: A "reset skill tree" option with confirmation — an in-UI two-click confirm (no browser dialog), fully refunding spent knowledge.
- [x] E14: Surface each skill's real-world grounding text more prominently on first unlock — a dedicated unlock toast.
- [x] E15: A visual badge on the settlement art per unlocked skill.
- [x] E16: Show the current run's severity band numerically — folded into the E8 expected-damage preview line.
- [x] E17: A "toughest run yet" comparison.
- [x] E18: An optional extended-run mode — a checkbox doubling the event schedule length for the next run.
- [x] E19: Distinct visual intensity per event severity.
- [x] E20: A live preview of the knowledge points a run will award.

---

## Per-game: Herd

*(F4, F10, F16, F20 marked "later" — moved to `LATER.md`.)*

- [x] F1: A live pure-growth-vs-decoupled counterfactual score comparison. `FarmState.counterfactual_funds`/`counterfactual_methane` accumulate a same-herd-size, zero-decoupling shadow path each round; `counterfactual_comparison_message()` surfaces the live score gap.
- [x] F2: Scale the pasture visual's cow count with real herd size. `update_pasture_visual()` reveals 5 fixed cow elements at herd-size thresholds (1/3/6/10/15).
- [x] F3: An end-of-session "report card" vs. a pure-growth baseline. On-demand panel (`report_card_html()`) restating the F1/F13 counterfactual numbers with a fuller breakdown.
- [x] F5: A one-time callout at a meaningful decoupling threshold. Milestone toast fires once at 50% decoupled-below-baseline.
- [x] F6: A rising growth-cost curve instead of flat cost. `grow_herd_cost()` — first unit still costs the original flat price, each unit after adds a fixed slope.
- [x] F7: A mini trend graph (methane/coupling ratio over rounds). `methane_trend_graph_svg()`, same technique as Thaw's mini_temp_graph_svg.
- [x] F8: A combined dial/readout for decoupling + plant-pivot interaction. `combined_decoupling_message()`.
- [x] F9: A consequence preview next to the Grow Herd button. `grow_consequence_message()` — next unit's cost/income/methane delta, no mutation.
- [x] F11: Borrow Thaw's tipping-flash pattern for market/regulatory pressure. Milestone toast fires once when pressure crosses 25% income loss.
- [x] F12: A short worked numeric example in How to Play. Added to the Decoupling Investments tutorial step (10-herd/Capture Systems worked example).
- [x] F13: A second comparison farm/region. The pure-growth counterfactual (F1) doubles as a persistent baseline-farm card (herd/funds/methane/score readouts).
- [x] F14: Min/max labels or a history sparkline behind the coupling gauge. Session-best (current ratio, monotonically improving) vs. fixed baseline.
- [x] F15: Surface the real 42% methane-intensity-reduction figure as a live comparison. `real_world_comparison_message()`, also cited in the Info Page.
- [x] F17: A one-time nudge the first time methane meaningfully drags score down. Milestone toast fires once past a fixed penalty-magnitude threshold.
- [x] F18: An aggregate community stat via the ratings backend. Fetched client-side in `index.html`, fails silently if unavailable.
- [x] F19: Lightweight animation/feedback on successful investment clicks. `_pulse()` toggles a short-lived CSS animation class on the clicked control.

---

## Per-game: Thaw

*(G7, G8 marked "later" — moved to `LATER.md`.)*

- [x] G1: Give Region B/C the same richer readouts Region A has.
- [x] G2: An explicit end-of-session "which region did best" line.
- [x] G3: A distinct "critical" visual/color state beyond binary melting/stable.
- [x] G4: Let players optionally label Region B/C's intended strategy.
- [x] G5: A real-world time calibration line for the background rise rate.
- [x] G6: A `temperature_saved`-style stat for the secondary regions too.
- [x] G9: A clarifying line (or rescale) for the maxed-out +30° temperature meter.
- [x] G10: A milestone callout the first time dampening measurably delays a melt threshold.
- [x] G11: Optional preset strategies for Region B/C.
- [x] G12: A small inline forecast on the invest buttons before clicking.
- [x] G13: A fourth, optional AI-driven "worst case" region.
- [x] G14: A gridline at the melt threshold on the mini graphs.
- [x] G15: Log the best-outcome strategy as an aggregate stat via the ratings backend.
- [x] G16: A one-line flavor difference per region.
- [x] G17: A "next round preview" tooltip on Advance Round.
- [x] G18: Vary the intervention-feedback message by dampening magnitude.
- [x] G19: A locally-stored "best run" stat.
- [x] G20: An optional free-text field for "did intervention feel like it was working?"

---

## Per-game: Loop

*(H16 marked "later" — moved to `LATER.md`.)*

- [x] H1: Fix the import/export asymmetry (excess imported supply currently evaporates).
- [x] H2: Let the player choose a different goods category at game start.
- [x] H3: A celebratory animation/banner the first time the loop closes.
- [x] H4: A "cost per unit of supply" readout next to Repair/Reuse/Recycle.
- [x] H5: Animate/highlight the decorative loop-ring nodes proportional to real investment.
- [x] H6: A "time to close the loop" projection.
- [x] H7: An in-game "Start New Chain" reset control.
- [x] H8: A second, differently-priced trading partner.
- [x] H9: A few alternate real-world sector comparisons, not just the static 7% one.
- [x] H10: A note clarifying the 2.5x cost multiplier is a hard ceiling.
- [x] H11: A lighter interim message for the first few cycles.
- [x] H12: A visible funds count-up/particle burst on export revenue.
- [x] H13: Toast callouts at circular-fraction milestones (25/50/75/100%).
- [x] H14: A few alternate vignette phrasings per fraction bucket.
- [x] H15: Show each measure's running contribution to supply next to its owned count.
- [x] H17: A live score breakdown instead of an info-toggle-only explanation.
- [x] H18: A visual pulse on the trade-network display when its numbers change.
- [x] H19: A "closed-loop streak" tracker.
- [x] H20: 2-3 alternate goods-flavor sets to pick from at game start.

---

## Per-game: Drift

*(I4 marked "maybe" — moved to `LATER.md`.)*

- [x] I1: A mini strain/wellbeing trend graph.
- [x] I2: Scale the region skyline's building count/height with real capacity.
- [x] I3: An explicit in-play comparison to the Uganda policy model.
- [x] I5: A one-time callout at the "thriving" wellbeing band (≥70).
- [x] I6: A one-line consequence description per strain level.
- [x] I7: A one-line effect summary on each capacity investment row.
- [ ] I8: Replace the coda's three meter bars with a clearer before/after comparison.
- [ ] I9: A real-world resettlement-outcome benchmark comparison (institutional/statistical only, per this game's own sensitivity note).
- [x] I10: A locally-stored "best run" stat.
- [ ] I11: A periodic (e.g. every 20 rounds) session-milestone summary.
- [x] I12: Have the checkpoint message occasionally note a comfortably-ahead dimension too.
- [x] I13: A difficulty-variant toggle (accelerated background severity).
- [x] I14: A "target" marker (e.g. 70) on each wellbeing gauge bar.
- [x] I15: A highlight/pulse on the coda button the moment it first becomes available.
- [ ] I16: Tie the arrival-dot stream's density/speed to real arrivals-per-round.
- [ ] I17: A passive "unmanaged control region" for contrast.
- [ ] I18: A free-text field inviting tone/framing concerns in the feedback prompt.
- [x] I19: Turn the net-positive turning-point message into a small persistent badge.
- [x] I20: Surface the funds-to-economic-health scale reference point in the UI.

---

## Per-game: Trade Empire

*(J4, J5 answered "no" — dropped entirely, not carried anywhere: this game is explicitly "just fun," not a teaching game, so the info-page/feedback-prompt pattern the teaching games use doesn't apply here.)*

- [x] J1: Wire up the shared save-widget contract.
- [x] J2: Link Trade Empire into the hub's main nav.
- [x] J3: Add the shared ad-bar partial.
- [ ] J6: A 5th/6th purchasable ship.
- [ ] J7: A second automation-slot research tier.
- [ ] J8: A lightweight "ship arrived" toast.
- [ ] J9: A real end-of-session/summary view.
- [ ] J10: Let players rename ships.
- [ ] J11: A per-route profitability readout.
- [ ] J12: A historical price sparkline per good.
- [ ] J13: A third self-contained expansion cluster.
- [ ] J14: A colony detail view (development-level and need history over time).
- [ ] J15: A warning badge when a manual ship sits idle and empty for a long stretch.
- [ ] J16: Make Fleet Priority's current target visible on the map.
- [ ] J17: A one-time callout marking the first automated ship.
- [ ] J18: Colorblind-safe automated/manual ship-dot differentiation — fold into the site-wide colorblind audit.
- [ ] J19: Confirmation before spending research/automation credits — folded into the shared confirmation-dialog goal above, with your frequency caveat attached.
- [ ] J20: A visual flourish on the endgame's background-galaxy payoff.

---

## Big standalone features

- [x] **Continuum Phase 6**: link Continuum into the main hub nav (K1/L1) — done (title card + review widget). The dedicated full-playthrough integration test (K3 — marked "later", see `LATER.md`) remains open.
- [x] **Trade Empire hub-link** (J2, L1) — done (title card + review widget), same pattern as Continuum's.
- [ ] **Le Champ de Mots: a visual-style switcher** — low-poly / text-based / cartoon / high-def, chosen on first load and changeable in settings. Desktop-only is fine (no need to solve mobile scaling for this). Your stated reasons: helps you see what's actually possible visually, and doubles as a BCM206 testing-different-options angle. **Blocked until Champ de Mots' current in-progress work (the minigames) finishes** — same gating as the rest of its section.
- [ ] Deploy the accounts system to production (L3) — it's built and tested locally but never pushed live.
- [ ] Real favicon/PWA icon art (L6).
- [ ] A "last updated" badge per title card (L7).
- [ ] An aggregate stats/About page — **visible in admin view only for now**, per your scoping note (L8).
- [ ] Auto-discover each game's `achievements.json` instead of hand-maintaining the list in `script.js` (L14).
- [ ] A "claim your save" nudge for anonymous players who've clearly invested real time (L15).
- [ ] A single cross-game feedback/bug-report entry point on the hub (L17).
- [ ] A more visible "Add to Home Screen" PWA prompt (L18 — you said you didn't know what this meant; short answer: browsers can show an "install this site as an app" prompt, since the site already has a PWA manifest — right now nothing nudges a visitor toward it, it only works if they know to look for their browser's own install option. Building this means adding a small, dismissible in-page banner that offers the install prompt directly. Moved to `LATER.md` with this explanation attached in case you want to hold off anyway — flip it to here if you're happy to proceed.)
- [ ] A lightweight public roadmap page generated from each game's own `CLAUDE.md` milestone table (L19) — **caution from you**: a lot of work happened outside the original milestone-table structure this session (e.g. the improvement-ideas rounds, ad-hoc bug fixes); this page needs to pull from actual git history/CLAUDE.md build notes, not just the milestone tables, or it'll undersell how much has shipped.
- [ ] A UI decluttering pass across every game (your "other comments" note: "everything looks very crowded... making sections either collapsible or other 'screens' within a game could help") — treat as its own review pass once the per-game feature backlog above has landed, since several of those features (colony detail views, settings panels, achievements panels) already reduce crowding as a side effect.

---

## Planning-doc audit findings (not from the ideas file — found while cleaning up `planning/`)

- [ ] **Password-reset path for accounts** — `planning/ACCOUNTS-AND-FEEDBACK-DESIGN.md` flags this as a known, still-open gap: a forgotten password permanently strands that account's saves/feedback, since auth is username+password with no email on file. Needs a decision on approach (an email provider, e.g. Resend — the exact thing dropped earlier for cost/complexity reasons — or a lower-tech alternative like an admin-assisted manual reset, reasonable at this site's current scale). Moved to `LATER.md` since it's a real design decision, not a quick build.
- [ ] Confirm whether BCM114 ever needed audience-engagement content (Instagram) alongside the site — `planning/site-plan.md` deferred this pending the semester outline (dated ~July 27, now well past). Just needs a status check, not new work, unless the answer is "yes, build it."
- [ ] Confirm/finalize the site's real public name — `planning/site-plan.md` still calls "CodingIsANoyvj" a placeholder "to confirm before anything public launches." If the site is already public/live, this is overdue.

---

## Closing tasks (run these last, per your instruction)

- [ ] A full site-wide bug-check pass, once everything above is done.
- [ ] Generate a fresh 20-ideas-per-game round-2 document (same format as `IMPROVEMENT-IDEAS-2026-09.md`) once this list is complete, for you to answer again.
- [ ] A second ideas document specifically for gamifying the "teaching" BCM114 games (Canopy, Grid, Tide, Aftermath, Herd, Thaw, Loop, Drift) — same 20-idea-per-game layout, but leaning into "fun" now that the teaching-focused part of the semester has passed. Explicitly requested to happen *after* everything you said yes to in this list is done.
