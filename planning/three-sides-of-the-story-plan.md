# Three Sides of the Story (slug `three-sides-of-the-story`, TODO QI-28) - Groundwork Plan

Source: the Quick ideas round (D4), owner-approved: "a branching story about a real issue (for example a water shortage), played once from each of three people's viewpoints." Checked against `PLAYER-PROFILE.md`: story only Lifeline-style with lots of branching, short missions that join into a story, real-world games show several points of view, caring topics (water, food, healthcare, housing), flawed people and no all-good hero, "fun that happens to be accurate", pictures over charts, free rewind, nothing lost. HARD BAN respected: this is not a visual novel (no portraits, no sprites, no dialogue-box scenes); it is a text-thread and radio-log format like Stranded and Lifeline. Personal project, no BCM tag, working title. One-line pitch: one dry week in a river town, lived three times, as the farmer, the water engineer and the clinic nurse, where each of them is partly right.

## 1. Concept
**Calder Weir** (invented) is a small river town in the seventh week without proper rain. The reservoir is at 31%. Over seven days the council must decide how to share what is left. You play the same week three times:
- **Ilse Brandt**, a third-generation fruit farmer on the upper terraces, whose orchard dies without irrigation, who has not paid the pumping levy, and who is loved and slightly stubborn.
- **Dev Okafor**, the town's water engineer, who has to protect the treatment plant, is blamed for a leak he reported twice, and cuts a corner on a sensor.
- **Rosa Mendes**, the nurse at the clinic and mother of two, who needs steady water for sterilising and who spreads a rumour in good faith.
No one is a villain and none is a saint. Each view is a thread of short messages, radio logs and notes with 2 to 4 choices a scene (Lifeline style). Choices change **town stats** (Reservoir, Trust, Fairness) and personal flags; some events are **fixed** and appear in all three views, seen differently (the same pump failure on day 3 is an alarm to Dev, a lost harvest to Ilse, a quiet ward to Rosa).
- 2-minute session: one day of one viewpoint, five or six messages, one choice that matters.
- 20-minute session: a whole viewpoint across seven days, then the **Compare** panel showing the same moments from the other two sides.
- Look: dark, calm, low-poly map and a simple reservoir gauge drawn as SVG; text-thread bubbles; no faces. Quiet tone, dry humour, nobody dies on screen, no harm shown.

## 2. Structure and rules
- Three views, each 7 days, each day 2 scenes, plus a shared **Council** meeting (day 7) that opens from any view or on its own after one view is finished: 3 x 14 + 8 = 50 scenes, 12 endings (3 per view plus 3 Council endings), all warm or bittersweet, none "wins".
- The engine is a deterministic graph walker: state = list of choice numbers per view (replayed to get scene, stats and flags). No randomness, no clock.
- **Fixed events:** 10 world events (pump failure, cut-off notice, tanker arrival, the rumour, a night inspection and so on) each with an id and a fixed outcome per **world state bucket** (low, middle, high Reservoir). Choices in one view can move a bucket that changes how the others see the event, but never removes a scene.
- **Compare panel:** once you have seen a fixed event in one view, you can see how the other two views tell it only after you have played it there (otherwise a dashed "not yet seen from this side"); no spoilers by default.
- **Free rewind** to any choice; stats reset to that moment; collectables never roll back.

## 3. Content size
- About 50 scenes, 130 choices, 12 endings; 10 fixed events told three ways (30 versions); 36 **Fact cards** (short sourced notes that appear as marginal "Did you know" lines in the thread, optional behind a setting).
- A small **Notebook** of 24 entries (the town's people, places, rules) filled as you meet them.

## 4. How fairness is PROVED (tests)
- A reachability validator walks the graph: every scene reachable, every ending reachable from some choice list, every scene has at least one open choice, no choice depends on a stat that cannot be reached (stat intervals computed per scene).
- A **fact ledger** test lists every world fact the three views assert (reservoir percent on day N, who knew what when). The ledger must be consistent across views: the same fact id never has two different values, and a fact one view says is "known" is not contradicted by another.
- All three characters' flaws are exercised: each view has at least one scene where the viewpoint's choice makes things worse for another view (a test counts them).
- Banned-content lint: no self-harm, no on-screen death words; sensitive topics present multiple points of view.
- Determinism and save replay tests.

## 5. Bigger picture, goals, hints
- The **Week Map**: a seven-day strip with three lanes (Ilse, Dev, Rosa) of day tiles, seen or "?", and a Council tile; a Reservoir gauge shows the last result you reached. A completion percentage bar sits above.
- Three goals always in view (any order): the next three unearned achievements with counts and bars. Stats strip: Scenes seen, Endings, Fixed events compared, Notebook.
- Hint ladder (opt-in, first rung asks "Would you like a suggestion?"): Nudge (which view has a loose end), Hint (which day), Answer (which choice, with a button that takes you there).
- Everything open from the start; Council opens as a free fourth thread. 100% is a walk down the loose ends on the map.

## 6. Achievements (14; computed from facts)
1 First Day; 2 One Week (finish a view); 3 Two Sides (two views); 4 Three Sides (three views); 5 The Council (see the meeting); 6 Every Ending (12); 7 Same Moment (compare 1 event); 8 Ten Moments (10 events compared); 9 Thirty Versions (all 30); 10 Notebook Half; 11 Notebook Full; 12 Fact Finder (read 20 fact cards); 13 Back Up (use rewind 5 times); 14 Second Opinion (all three hint rungs on one scene).

## 7. Real-world facts
Fact cards drawn from named, dated sources read live and shown with the read date: global water stress and agriculture's share of freshwater use (UN-Water / FAO data), the typical share of a town's water lost to leaks (World Bank), and how rationing schemes are designed (a named public water-authority guide). Each card says "Where this comes from" and offers other views ("Farmers say...", "Engineers say...", "Clinics say..."). Fiction notice: town, people and events are invented. More game than teaching.

## 8. Stack, save and reuse
- Pyodide Python, plain HTML/CSS with code-drawn SVG, no build step, no audio. Modules: `graph.py` (scenes, choices), `views_ilse.py`, `views_dev.py`, `views_rosa.py`, `council.py`, `events.py` (fixed events), `ledger.py`, `state.py`, `notebook.py`, `progress.py`, `hints.py`, `render.py`, `achievements.py`, `info.py`, `game.py`, `app.js`.
- Reuses Stranded's branch-map and rewind engine pattern, `shared/story-toggle.js`, `hint-ladder.js`, `goals-panel.js`, `save-widget.js`, `narrative_log.py`.
- Save: choices per view (replayed), endings, notebook, facts read, hint rungs, flags, tally. Only validated state loads.

## 9. Milestones
| # | Milestone | Content |
|---|-----------|---------|
| 1 | Engine | Graph walker, stats, fixed events, ledger and reachability validators, Ilse's view (14 scenes) with tests |
| 2 | Thread UI | Message thread, choices, week map, rewind, reservoir gauge, save contract. Playable slice |
| 3 | Dev and Rosa | The other two views (28 scenes), fixed events told three ways, Compare panel, hint ladder, three-goals strip |
| 4 | Council | The Council meeting (8 scenes), 12 endings, notebook. First complete game |
| 5 | Standard kit | Opening screen, tutorial, settings, About with live-read sources and fiction notice, What's New, keyboard help, light theme, accessibility pass |
| 6 | Achievements | 14 achievements, panel and toast, manifest, reachability test |
| 7 | Desktop boot and wrap-up | `pc-config.json`, `pc.css`, `pc.js`, generated `pc.html`, docs, changelog |

## 10. Open questions for the owner (defaults used meanwhile)
1. Are a fruit farmer, a water engineer and a clinic nurse the right three viewpoints for a water shortage, or would you swap one (for example a shopkeeper or a council member)? Default: as written.
2. Should the Council meeting be a fourth playable thread, or just an ending screen that summarises what the three sides chose? Default: a short playable thread.
3. Should fact cards be on by default or switched on in Settings? Default: on, with a setting to hide.
