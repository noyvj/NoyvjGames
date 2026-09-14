# Site-Wide TODO

The one living list, replacing the scattered planning docs' own "open items"/"stretch goals" sections. Built from your labeled answers in `IMPROVEMENT-IDEAS-2026-09.md` (all "yes" items, resolved), plus a pass through every other file in `planning/` pulling out anything still genuinely unresolved there. "Later" items (things you deferred, or that need more explanation first) live in `LATER.md` instead — not here.

Check items off (`[x]`) as they land. Ordered by priority (my call, per your instruction) — roughly: in-flight work first, then cross-cutting site-wide goals (most of these were flagged "yes but site-wide" across several answers), then per-game work, then the big standalone features, then the closing/meta tasks you explicitly asked to run last.

Le Champ de Mots is included here now that its own answers would apply — its 4th minigame batch is still finishing in the background; its own labeled section (M) will fold in once you've reviewed it, same as every other game.

---

## In flight

- [x] Le Champ de Mots Milestones 27-28 (Greetings & Basics Blitz, Verb Racer arcade minigames) — done, committed.
- [ ] Le Champ de Mots Milestones 29-30 (Boutique Dash, Café Rush arcade minigames) — running now.
- [ ] Continuum Phase 6 (hub nav integration) — see "Big standalone features" below, gated behind nothing else.

---

## Site-wide goal: roll achievements out everywhere

*(Origin: L2, A2, K2, and the framework itself — `planning/ACHIEVEMENTS-SYSTEM-DESIGN.md` has the full technical pattern and §7's per-game checklist. SOL is the reference implementation.)*

Two things every game needs once achievements land there, on top of the base rollout (per A19/A20, "yes but site-wide"):
- An achievement-earned toast/popup at the moment it's unlocked (not just visible inside the panel).
- A link from the in-game achievements panel to the hub-wide dashboard.

- [x] SOL — 18 achievements + panel + hub dashboard (reference implementation).
  - [ ] Retrofit: add the unlock-toast and hub-dashboard-link (built after SOL shipped, per A19/A20).
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
- [ ] Canopy
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
- [ ] Canopy — also extend to the stats/legend panels (B15).
- [ ] Grid — plant-build action row (C1).
- [ ] Tide — investments panel + Advance Season button (D1).
- [ ] Aftermath — actions panel: Resilience/Growth/Face Next Event (E1).
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

- [ ] Add a copy-to-clipboard button next to the displayed save code.
- [ ] Auto-fill the "load by code" input with the last remembered code for this game (currently it's only shown separately, never pre-filled).
- [ ] Fix the two stale doc comments in `planning/SAVE-BUTTON-INTEGRATION.md` once the above lands (or remove the claims if you'd rather not build them).

---

## Site-wide goal: hub lobby improvements

*(Origin: L11, L12, plus your own added notes.)*

- [ ] Search/filter on the hub lobby (L11).
- [ ] A "games you have saves for" section pinned to the top for signed-in users, so a player who only plays 2-3 games sees those first (your addition to L11) — this overlaps with L4 ("continue where you left off"); build as one combined feature, not two.
- [ ] Tags per title card — not just length/depth (L12 originally suggested "quick" vs "deep systems"), but a general sorting/tagging system across the whole site, per your note that this could "start a general sorting system through the whole site." Decide the tag taxonomy (genre? subject? length?) before building.

---

## Per-game: SOL

- [ ] A1: Prestige / "New Game+" layer after the soft win-state. **Needs a decision from you before building**: a simple stat-boost restart, or something closer to a skill-tree-based system? (You asked which I'm thinking — my default lean is to start simple: a permanent flat bonus on restart, since a full skill-tree prestige layer is really its own milestone-sized feature. Say the word if you want the bigger version instead.)
- [ ] A2/A13: A second achievement wave — speedrun-style and "pure clicker/never automated" challenge runs. **Constraint from you: keep 100% achievable without extreme grinding or huge time investment.**
- [ ] A3: A "welcome back" return-visit summary toast.
- [ ] A4: A lifetime-stats screen.
- [ ] A6: Layer in the icon/visual layer the design doc always left room for — **only if straightforward**; if it turns into a real asset-pipeline project, downgrade to `LATER.md` instead of forcing it.
- [ ] A8: A shareable "my solar system" end-state summary card.
- [ ] A11: A visible "governor efficiency" readout.
- [ ] A15: Visual terraforming feedback (color shift as `terraform_progress` climbs).
- [ ] A16: A simple research-tree diagram instead of a flat list.
- [ ] A17: An ecology warning banner at the 25%-output-penalty threshold.
- [ ] A18: A "reset this world only" option.

---

## Per-game: Continuum

- [ ] K5: A "civilization summary" end-of-playthrough report.
- [ ] K6: Named camera presets in the 3D scene.
- [ ] K7: A way to actually view a revisited era's snapshot in the 3D layer.
- [ ] K8: Confirm every info-panel source is a clickable outbound link — fix any that aren't.
- [ ] K10: A tutorial walkthrough via `shared/tutorial.js`, if it doesn't have one.
- [ ] K12: A scenario/difficulty select at new-game start.
- [ ] K13: A shareable "my settlement" snapshot image, exported from the 3D scene.
- [ ] K14: A search/filter on the research tree (14 tiers across 3 branches now).
- [ ] K15: Confirm accessibility settings (text-scale, colorblind fixes) persist through a real save/load, not just `localStorage`.
- [ ] K17: A subtle day/night or seasonal lighting cycle in the 3D scene.
- [ ] K18: An optional stricter "hard mode" sustainability variant.
- [ ] K19: Confirm/extend distinct meshes per building type in the 3D scene.
- [ ] K20: A proper hub title-card art pass — do this once Phase 6 (below) links it in.

---

## Per-game: Canopy

- [ ] B1: End-of-session summary screen.
- [ ] B2: "Reset session" button.
- [ ] B3: A second, unlockable forest region/biome.
- [x] B4: Coordinate-style plot labels.
- [ ] B6: A history sparkline (income vs. standing value).
- [ ] B7: Save/compare two named playstyle runs.
- [ ] B8: Hover/tap tooltips on plot tiles.
- [ ] B9: A colorblind-safe pattern/icon overlay for plot states — fold into the site-wide colorblind audit above if that's more efficient than a one-off.
- [x] B10: Surface biodiversity as an explicit number.
- [ ] B11: Diversify stakeholder requests to sometimes offer a positive trade-off.
- [ ] B12: A visible badge for a pending stakeholder request when scrolled away.
- [ ] B13: A larger-grid option as a difficulty/length variant.
- [ ] B14: A persisted "personal best" stat across sessions.
- [ ] B16: Keyboard navigation for plot selection/action.
- [ ] B17: A floating "+X value" animation on compounding ticks.
- [ ] B18: A shareable end-of-session code/snippet.
- [ ] B19: A distinct "fully mature" cap-off visual for Recovered plots.
- [ ] B20: A closing counterfactual line at session end.
- [ ] **Unresolved — please clarify**: your answer to B15 talks about "overpinning" and worrying about too much being pinned, but B15 itself was "extend the mobile-dock treatment to the stats/legend panels," which has nothing to do with pinning. I've kept B15 itself as a plain yes (folded into the mobile-dock rollout goal above) but flagging this so you can tell me what B15's actual comment was meant to be about.

---

## Per-game: Grid

*(C6 marked "later" with no further comment — moved to `LATER.md` as-is.)*

- [ ] C1 — folded into the mobile-dock rollout goal above.
- [ ] C2: A battery/grid-storage plant tier.
- [ ] C3: Attach disruption-event log lines to the specific plant/type that failed.
- [ ] C4: Weather-variability-on-renewables as an opt-in hard mode.
- [ ] C5: A proper end-of-run summary screen with a score breakdown.
- [ ] C7: A plant-mix bar chart.
- [ ] C8: A tipping-point callout at 50% cumulative renewable capacity.
- [ ] C9: Confirmation before retiring the last unit of a plant type — folded into the shared confirmation-dialog goal above.
- [ ] C10: Show the exact aging/wear percentage.
- [ ] C11: The aggregate clean-score-across-players comparison Pass 2 floated but never built.
- [ ] C12: A visible toast/banner for disruption events.
- [ ] C13: A funds breakdown (build vs. maintenance vs. disruption-damage).
- [ ] C15: An interactive trend graph (hover for exact values).
- [ ] C16: A "steeper demand growth" difficulty variant.
- [ ] C17: A closing "grid vs. business-as-usual" counterfactual.
- [ ] C18: Colorblind-safe trend-graph line differentiation — fold into the site-wide colorblind audit.
- [ ] C19: A breakdown-risk badge once a plant type's average age crosses a threshold.
- [ ] C20: A one-time first-use callout for Retire's refund / Maintain's cost math.

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

- [ ] E1 — folded into the mobile-dock rollout goal above.
- [ ] E2: A fourth and fifth skill-tree node.
- [ ] E3: Branching/prerequisite structure for the skill tree.
- [ ] E4: Build out the "legacy system" beyond its current flavor-text line.
- [ ] E6: Another event category beyond weather/non-weather.
- [ ] E7: Let players review a specific past run's full event-by-event breakdown.
- [ ] E8: An "expected damage this event" preview before Face Next Event.
- [ ] E9: A visible "X/3 skills unlocked" progress summary.
- [ ] E10: A confirmation animation/state change when investment is spent.
- [ ] E11: A proper end-of-run summary.
- [ ] E12: Export/import code for the localStorage-based skill tree and run history.
- [ ] E13: A "reset skill tree" option with confirmation.
- [ ] E14: Surface each skill's real-world grounding text more prominently on first unlock.
- [ ] E15: A visual badge on the settlement art per unlocked skill.
- [ ] E16: Show the current run's severity band numerically.
- [ ] E17: A "toughest run yet" comparison.
- [ ] E18: An optional extended-run mode.
- [ ] E19: Distinct visual intensity per event severity.
- [ ] E20: A live preview of the knowledge points a run will award.

---

## Per-game: Herd

*(F4, F10, F16, F20 marked "later" — moved to `LATER.md`.)*

- [ ] F1: A live pure-growth-vs-decoupled counterfactual score comparison.
- [ ] F2: Scale the pasture visual's cow count with real herd size.
- [ ] F3: An end-of-session "report card" vs. a pure-growth baseline.
- [ ] F5: A one-time callout at a meaningful decoupling threshold.
- [ ] F6: A rising growth-cost curve instead of flat cost.
- [ ] F7: A mini trend graph (methane/coupling ratio over rounds).
- [ ] F8: A combined dial/readout for decoupling + plant-pivot interaction.
- [ ] F9: A consequence preview next to the Grow Herd button.
- [ ] F11: Borrow Thaw's tipping-flash pattern for market/regulatory pressure.
- [ ] F12: A short worked numeric example in How to Play.
- [ ] F13: A second comparison farm/region.
- [ ] F14: Min/max labels or a history sparkline behind the coupling gauge.
- [ ] F15: Surface the real 42% methane-intensity-reduction figure as a live comparison.
- [ ] F17: A one-time nudge the first time methane meaningfully drags score down.
- [ ] F18: An aggregate community stat via the ratings backend.
- [ ] F19: Lightweight animation/feedback on successful investment clicks.

---

## Per-game: Thaw

*(G7, G8 marked "later" — moved to `LATER.md`.)*

- [ ] G1: Give Region B/C the same richer readouts Region A has.
- [ ] G2: An explicit end-of-session "which region did best" line.
- [ ] G3: A distinct "critical" visual/color state beyond binary melting/stable.
- [ ] G4: Let players optionally label Region B/C's intended strategy.
- [ ] G5: A real-world time calibration line for the background rise rate.
- [ ] G6: A `temperature_saved`-style stat for the secondary regions too.
- [ ] G9: A clarifying line (or rescale) for the maxed-out +30° temperature meter.
- [ ] G10: A milestone callout the first time dampening measurably delays a melt threshold.
- [ ] G11: Optional preset strategies for Region B/C.
- [ ] G12: A small inline forecast on the invest buttons before clicking.
- [ ] G13: A fourth, optional AI-driven "worst case" region.
- [ ] G14: A gridline at the melt threshold on the mini graphs.
- [ ] G15: Log the best-outcome strategy as an aggregate stat via the ratings backend.
- [ ] G16: A one-line flavor difference per region.
- [ ] G17: A "next round preview" tooltip on Advance Round.
- [ ] G18: Vary the intervention-feedback message by dampening magnitude.
- [ ] G19: A locally-stored "best run" stat.
- [ ] G20: An optional free-text field for "did intervention feel like it was working?"

---

## Per-game: Loop

*(H16 marked "later" — moved to `LATER.md`.)*

- [ ] H1: Fix the import/export asymmetry (excess imported supply currently evaporates).
- [ ] H2: Let the player choose a different goods category at game start.
- [ ] H3: A celebratory animation/banner the first time the loop closes.
- [ ] H4: A "cost per unit of supply" readout next to Repair/Reuse/Recycle.
- [ ] H5: Animate/highlight the decorative loop-ring nodes proportional to real investment.
- [ ] H6: A "time to close the loop" projection.
- [ ] H7: An in-game "Start New Chain" reset control.
- [ ] H8: A second, differently-priced trading partner.
- [ ] H9: A few alternate real-world sector comparisons, not just the static 7% one.
- [ ] H10: A note clarifying the 2.5x cost multiplier is a hard ceiling.
- [ ] H11: A lighter interim message for the first few cycles.
- [ ] H12: A visible funds count-up/particle burst on export revenue.
- [ ] H13: Toast callouts at circular-fraction milestones (25/50/75/100%).
- [ ] H14: A few alternate vignette phrasings per fraction bucket.
- [ ] H15: Show each measure's running contribution to supply next to its owned count.
- [ ] H17: A live score breakdown instead of an info-toggle-only explanation.
- [ ] H18: A visual pulse on the trade-network display when its numbers change.
- [ ] H19: A "closed-loop streak" tracker.
- [ ] H20: 2-3 alternate goods-flavor sets to pick from at game start.

---

## Per-game: Drift

*(I4 marked "maybe" — moved to `LATER.md`.)*

- [ ] I1: A mini strain/wellbeing trend graph.
- [ ] I2: Scale the region skyline's building count/height with real capacity.
- [ ] I3: An explicit in-play comparison to the Uganda policy model.
- [ ] I5: A one-time callout at the "thriving" wellbeing band (≥70).
- [ ] I6: A one-line consequence description per strain level.
- [ ] I7: A one-line effect summary on each capacity investment row.
- [ ] I8: Replace the coda's three meter bars with a clearer before/after comparison.
- [ ] I9: A real-world resettlement-outcome benchmark comparison (institutional/statistical only, per this game's own sensitivity note).
- [ ] I10: A locally-stored "best run" stat.
- [ ] I11: A periodic (e.g. every 20 rounds) session-milestone summary.
- [ ] I12: Have the checkpoint message occasionally note a comfortably-ahead dimension too.
- [ ] I13: A difficulty-variant toggle (accelerated background severity).
- [ ] I14: A "target" marker (e.g. 70) on each wellbeing gauge bar.
- [ ] I15: A highlight/pulse on the coda button the moment it first becomes available.
- [ ] I16: Tie the arrival-dot stream's density/speed to real arrivals-per-round.
- [ ] I17: A passive "unmanaged control region" for contrast.
- [ ] I18: A free-text field inviting tone/framing concerns in the feedback prompt.
- [ ] I19: Turn the net-positive turning-point message into a small persistent badge.
- [ ] I20: Surface the funds-to-economic-health scale reference point in the UI.

---

## Per-game: Trade Empire

*(J4, J5 answered "no" — dropped entirely, not carried anywhere: this game is explicitly "just fun," not a teaching game, so the info-page/feedback-prompt pattern the teaching games use doesn't apply here.)*

- [ ] J1: Wire up the shared save-widget contract.
- [ ] J2: Link Trade Empire into the hub's main nav.
- [ ] J3: Add the shared ad-bar partial.
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

- [ ] **Continuum Phase 6**: link Continuum into the main hub nav (K1/L1), plus a dedicated full-playthrough integration test (K3 — actually marked "later", see `LATER.md`; the hub-link half is the actionable part now).
- [ ] **Trade Empire hub-link** (J2, L1) — same nav-integration work, can be done alongside Continuum's.
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
