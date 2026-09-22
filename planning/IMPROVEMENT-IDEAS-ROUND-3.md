# Improvement Ideas — Round 3

Written assuming **everything currently in `planning/TODO.md` has landed** (every open per-game item, the cross-game Z section, the hub Y section including the site-wide light/dark theme, the Warframe items, the recovered tasks, and the multiplayer scoping plan). Nothing below repeats something built, on that list, or answered "no"/"later" earlier.

**One file, three parts, per your instruction — plus a fourth folded in afterward (see below):**
- **Part 1 — Gamify the teaching games (sections GB–GI).** Fun-first ideas for the eight games that started as BCM114 teaching games (Canopy, Grid, Tide, Aftermath, Herd, Thaw, Loop, Drift), 30 each. The lens is fun, replayability and tension, not lessons.
- **Part 2 — Round 3 for every game (sections A–L, M, N–U, Z, Y, X).** 31 ideas per game in hub listing order (item 31 on every one is the same standing idea: make that game's own achievements more visible/stylized — see each section's own final item for the game-specific version), then **M** (5 brand-new game concepts, fun-first), then two folded-in follow-up docs given their own sections — **N** (seasonal/real-world-date event ideas, from the Z23 seed doc) and **O** (the replayability-audit follow-up for Trade Empire/Continuum, from the Z7 seed doc) — then **P–U** (open questions for the five new games already approved in round 2: Signal, Undersleep, Overclock, Last Line, Deep Descent — each needs a full groundwork plan read before building, but the genuinely undecided design forks are pulled out here so you can answer them the same way as everything else), then **Z** (cross-game patterns), **Y** (the hub itself) and **X** (the Warframe tracker). For the eight teaching games this covers the *other* dimensions (depth, polish, quality-of-life, presentation, stats, sharing, long-term progression) so it doesn't repeat Part 1.
- **Part 3 — Returning later (section R).** Everything parked in `planning/LATER.md`, each needing one word from you: now / later / drop.
- **Part 4 — Your answers.** A ready-made answer sheet at the very end of this file: every section above, already titled and pre-numbered to match its own items, with a blank after each number. You never have to write out `## <SECTION>` headers or item numbers yourself — just fill in a word (or a few) after each pre-existing number and leave anything you're not ready to answer blank.

**How to answer:** fill in Part 4 at the end of the file — one line per item, in place, under its own pre-made section heading. "Yes" builds it, "no" drops it, "later" parks it, and any note you add after the word is kept. (If you'd rather answer the old way, `## <SECTION>` blocks with numbered lines still work exactly as before — Part 4 is just a scaffold, not a new format.) Ideas are tagged **[BIG]** or **[SMALL]**; every section has at least 10 of each, except M/N/O/P/Q/S/T/U, which are shorter by nature (5-11 items).

**Where overlap is likely:** several ideas appear in more than one game's section (run modifiers, daily seeds, event decks, unlock trees). Each section ends with a short notes paragraph flagging those, so shared scaffolding can be built once and reused.

---

# PART 1 — Gamify the teaching games

## GB. Canopy (gamified)

1. **[BIG]** Wildfire season. Every so often a spark ignites on a dry standing plot and spreads to neighbouring plots each tick. Bare or replanting plots act as firebreaks, so the player can deliberately clear a plot (a Clear click, taking the soil hit) to save a mature cluster, or race to click "Dampen" on the burning tile. It turns the clear/preserve/replant actions into a tense triage puzzle. Season hooks in: fire risk rises in summer and drops in winter (existing 160-tick cycle). Opt-in via difficulty select.
2. **[SMALL]** A "golden seedling" that pops up on a random bare or replanting plot for about 4 seconds, cookie-clicker style. Clicking it instantly banks a burst of recovery progress on that plot with a satisfying leaf-burst (reusing the B4 burst). It gives idle stretches a cheap active-skill beat.
3. **[BIG]** Expedition mode (roguelike run). A fixed 12-season run (480 ticks); at each season change you pick 1 of 3 random "boons" (e.g. Mycorrhizal Network: mature plots feed +10% to their neighbours; Deep Roots: soil never drops below 50%; Timber Boom: clears pay double but each costs relations). Boons stack into a run-defining build, and the run ends in a score plus a shareable seed. It sits beside normal play as a separate mode and reuses the Session Summary.
4. **[SMALL]** Nurture cooldown: a "Tend" action (hotkey T) on any hovered plot gives it a short growth-rate boost, then a 20-tick cooldown. Skilled players juggle it across the grid instead of just watching numbers rise. Pure active-skill flavour, no new state beyond a cooldown timer.
5. **[BIG]** Neighbour synergy layout puzzle. Mature plots gain a canopy bonus for each adjacent mature plot, and a bare plot next to a mature one replants faster. Grid shape suddenly matters: solid blocks vs checkerboards vs a protected core with a cleared "farm edge." Hooks into the existing plot state and accrual formula, and shows a small "+link" glyph on synergised tiles.
6. **[BIG]** Species on replant. Replanting asks you to choose a tree: Pioneer pine (fast recovery, low ceiling), Hardwood oak (slow, high value and biodiversity), or Orchard (steady income, no wildlife). Mixed forests get bonuses; the specialist upgrade (B21) can layer on top. This gives every replant click an actual decision and an identity to each plot.
7. **[BIG]** Blight in monocultures. If a large connected patch is one species, a blight can hit and spread through it, killing plots back to BARE. Diverse patches resist it. It is a real risk/reward against min-maxing the best tree everywhere, and it is only live once species exist (idea 6).
8. **[SMALL]** A hidden "Heart Tree": arrange seven mature plots in a ring (a full loop of neighbours) and the centre plot grows a glowing ancient tree with a unique sprite and a permanent aura. There is no hint in the UI, just a wildlife-log style entry and a toast when found. It is a discovery secret for the curious.
9. **[BIG]** Ranger contracts board. Three rotating contracts at a time ("Have 5 plots mature at once," "Never let relations drop below 40 for 60 ticks," "Earn 300 income without touching Highland"). Completing them pays seed points that feed a between-session unlock track (idea 10). It gives a sessions-long "what am I chasing now" without a lecture.
10. **[BIG]** Seed Vault meta-progression (Canopy-specific, extends B15 legacy). Sessions earn seeds spent on permanent unlocks: new species, a fourth stakeholder type, a starting "nursery" row, cosmetic tree skins. Nothing is mandatory, and harder modes give more seeds. It follows your "meta-progression inside a game" taste.
11. **[SMALL]** Fast-forward toggle (1x / 2x / 4x tick speed) next to the season indicator. Idle stretches stop being dead air, and veterans can burn through a solved opening. It is a pure ticker-interval change that does not touch any tick-based math.
12. **[BIG]** Rival logging company. An AI "Halloran Timber Co." starts buying up plots on your grid edges on a visible countdown (a plot flashes, then flips to a mining claim). You can pay a conservation easement to lock any plot, but it costs standing value income. That adds a pressured spending decision and a rival with personality, escalating over a session.
13. **[SMALL]** Poacher whack-a-mole: occasionally a small poacher icon appears on a wildlife-bearing plot with a 5-second timer. Click to scare them off, or lose a species from the wildlife log. It gives the wildlife log stakes (B23) and rewards attention.
14. **[SMALL]** Let players name their forest and give an individual tree nickname to the adopted plot (B27). The log then narrates it ("Old Bramble survived a third clearing request"). It is a personality/attachment hook and costs one text field.
15. **[BIG]** Storm front events. A storm drifts across the grid over 10 ticks along a visible path; the player can spend income to "shelter" plots. Unsheltered young/replanting plots get flattened back to BARE, while mature plots take only a small hit. It is a foresight puzzle: read the path and spend your budget before impact.
16. **[SMALL]** A "forest spirit" narrator with a dry sense of humour that reacts to your choices ("Cleared that plot three times? Bold."). It is off by default via the Settings panel (a story toggle) and appears only in the forest history log.
17. **[BIG]** Challenge run set, each with its own badge: Pacifist (never clear), Scorched Start (all plots begin BARE, reach 2,000 standing value), Sprint (5,000 value in 300 ticks), No-Highland (win without unlocking the second grove). Each run has its own personal-best slot, extending the playstyle badge idea into replayable goals. They plug into the achievements panel.
18. **[SMALL]** A short undo window: after Clear, a 3-second "Undo" chip restores the plot. It is off in Ranger difficulty. It makes mis-clicks on the 9x8 grid forgivable, so the risk of a big grid isn't just fat-finger loss.
19. **[BIG]** Daily seeded forest. A date-derived seed generates a starting layout (some plots pre-cleared, a fixed stakeholder-request order, a scheduled storm/fire). Everyone gets the same puzzle, and the player's score is compared against their own local history. It is replay value without needing the multiplayer pass.
20. **[SMALL]** Rare wildlife that only appears under conditions: a ghost stag only at night-tinted late-autumn ticks on a 90%+ biodiversity plot, a fox after 3 declined clear requests. It adds "gotta find them all" entries to the B23 wildlife log.
21. **[BIG]** Timber gambler mechanic: a "Clear-cut" alternative to Clear that rolls for a rare hardwood windfall (3x payout, 25% chance) versus a heavy soil crash (-40% productivity) otherwise. It offers a real risk/reward slot machine for Harvester-style players and pairs with the playstyle badge.
22. **[SMALL]** A tiered "Standing Value" milestone celebration: at 1k, 2.5k, 5k, 10k the forest background flushes with a brief light pulse and a title bump (Seedling, Grove, Woodland, Old-Growth). Purely a satisfying-feedback moment reusing the personal-best flash pattern.
23. **[SMALL]** Weather reads on the grid: rain shimmer boosts accrual for 8 ticks, drought tints the tiles and slows them. It is visible via the existing season indicator and gives the passive numbers texture.
24. **[BIG]** Wetland/mangrove biome as a real puzzle (extends the still-open B1): tidal cycles swap plots between flooded and dry every few ticks, and only certain species/states can be placed while flooded. Mastering the tide timing is the fun, with rewards like a bonus wildlife set. Overlaps with Tide's water logic, so build it once and share.
25. **[SMALL]** Stakeholder faces: give each requester a recurring named character with a mood (the farmer, the mayor, the carbon broker) and a tiny portrait. Repeated grant/decline choices change the tone and unlock friendship perks such as a reduced clear-request frequency. It is humour and personality on top of an existing system.
26. **[BIG]** Idle/automation layer: earn "ranger crew" upgrades that auto-replant bare plots or auto-decline low-value requests, at a cost per tick. You shift from clicking to designing an automated forest, and the hard mode makes crews unreliable. It fits your idle taste and the 1-second tick.
27. **[SMALL]** A satisfying "chain bloom" effect: when several plots reach maturity within a few ticks, their leaf bursts ripple across the grid in sequence with escalating size. It is juice for good timing and adds no new mechanics.
28. **[SMALL]** A "Forest Almanac" collection page tracking species planted, seasons survived, rare wildlife found, and hidden structures discovered, shown as a checklist with silhouettes for unfound entries. It is a completionist hook; hidden items only appear as "???".
29. **[BIG]** Carbon-credit market minigame: standing forest generates credits whose price swings on a small sparkline. Hold or sell (selling pays now but temporarily reduces the "preserved" multiplier), so timing the market becomes a second, riskier income route beside clearing. It ties to the existing incentive request type.
30. **[SMALL]** A "Perfect Season" streak: end a season with no BARE plot decreasing your standing value and no declined-and-regretted request to earn a small multiplier, displayed as a flame counter. It rewards consistent play across the 4-season cycle.

---

## GC. Grid (gamified)

1. **[BIG]** Project cards (deck-builder shape). Each round you draw 3 cards (Solar Farm Site, Fuel Deal, R&D Grant, Community Backlash, Heatwave Warning...) and play one, with the rest discarded. Cards can permanently modify the run (e.g. "Wind sites cost -15%"). Builds emerge from what you draw, so no two runs are alike, and it plugs into the existing policy lever and cost curve.
2. **[BIG]** Roguelike run modifiers plus starting relics. Before a run pick a relic (Old Coal Contract, Storage Startup, Diplomatic Immunity) and get a random mutator like Dry Years (hydro output halved) or Fuel Embargo (gas twice as expensive). Extends the four scenarios into an endless combinatorial mode; the career perks can unlock relics.
3. **[BIG]** Day-in-the-life dispatch puzzle. Each round optionally expands into a 24-hour timeline with a solar hump, a wind wobble, and an evening peak; you drag plants into a dispatch order (cheapest first, batteries at the peak). Better dispatch means better revenue and fewer brownouts. It is the tight, clever-decision mode battery arbitrage only hinted at.
4. **[SMALL]** Named plants. Each built plant gets a random nickname ("Old Smoky," "Sunny Delight"), and retiring the last coal plant plays a tiny eulogy line and a demolition puff. It is humour and attachment for the plant-count rows without touching the math.
5. **[BIG]** Expanded tech tree in the Career: spend career points to unlock genuinely new plant types (offshore wind, geothermal, small modular nuclear, gas with capture, green hydrogen) each with its own cost/capacity/risk quirk. New build options change how each run plays out, in Grid's own meta-progression, not shared with other games.
6. **[SMALL]** Ribbon-cutting juice: building a plant plays a quick flash and a pop-in animation on its row, and the first plant of each type gets a bigger one. Reaching 25/50/75% clean share fires a little skyline light-up. It is pure feedback polish on the build button.
7. **[BIG]** Siting map. Building a solar/wind/hydro plant means picking a tile on a small regional map (ridge = wind, desert = solar, river = hydro), where tile quality changes capacity factor, and cities nearby generate NIMBY pushback. It is a spatial puzzle layered on the existing plant rows, and it needs an art pass but can stay emoji-tile simple.
8. **[SMALL]** City skyline HUD: a strip of buildings whose lights brighten as demand is met and flicker/dim during brownouts, with a smoky haze that thickens with emissions. It gives the round result an emotional read at a glance instead of a number.
9. **[BIG]** Ghost run. Race your own best previous run: its trend line (clean share, funds) is overlaid as a translucent "ghost" line on the trend graph and a round-by-round "ahead/behind" delta shows. It makes personal improvement the fun target and needs only a stored per-run array in localStorage.
10. **[BIG]** Boss rounds. Every 8th round is a named peak event (Heatwave, Polar Vortex, Dry Summer) with a preview one round ahead and a specific demand spike or output penalty. Beat it for a big reward (a free card, a discount, an achievement). It adds rhythm, prep tension and memorable moments to the escalating rounds.
11. **[SMALL]** Peek forecast: spend a small fee to reveal next round's weather roll and disruption chance before committing a build. It is a cheap information-buying decision that fits the existing Weather Variability toggle.
12. **[BIG]** Handcrafted puzzle campaign. 10-12 short scenarios ("Island grid: 6 rounds, 300 funds, hit 80% clean and never brown out") with 1-3 star ratings on par-rounds and budget. They are tight, solvable, and shareable, and add a first-time-player on-ramp and a mastery layer without the full run.
13. **[SMALL]** Rolling-blackout gamble button: when short on capacity you can trigger a rolling blackout to cap the shortfall penalty, but at a 30% chance of a public-trust hit. It is a clean risk/reward in a bad round instead of only eating the loss.
14. **[BIG]** Coal town loyalty. Retiring fossil plants shifts a Town Support meter; keeping it up means funding retraining or a phased-closure option, and letting it crash triggers protest events that block builds. It creates a genuine "slow and steady vs fast and messy" tension and rewards the diversification score (resilience) already in the game.
15. **[SMALL]** A "Perfect Round" combo: consecutive rounds with zero disruptions and demand fully met build a multiplier on revenue, shown as a visible streak flame. It extends the existing clean-streak counter (C28) into an active goal to protect.
16. **[BIG]** Autopilot manager (idle shape). Hire and upgrade automation: an auto-builder that follows a priority list you set (e.g. "always build the cheapest renewable when funds > X"), then fast-forward N rounds at once with stop-on-event. It shifts play from clicking to designing rules, and the career points pay for smarter managers.
17. **[SMALL]** "Auto-advance 5 rounds" button that halts the moment any disruption, breakdown or policy offer fires. It respects the tense moments without forcing a click per calm round.
18. **[BIG]** Energy market. A spot price that random-walks each round; long-term supply contracts lock in a fixed price for N rounds with a bonus if you always deliver. Contracts are the risk/reward pick versus riding the spot price, and they reward planning capacity ahead. It builds on the existing revenue-per-unit formula and storage arbitrage.
19. **[SMALL]** Grid AI companion "Gridley": a wry one-line commentary voice on round outcomes ("You built coal again? Bold strategy.") that can be toggled off in the Settings panel. It is personality with a story-toggle escape hatch.
20. **[BIG]** R&D lab gamble. Put funds into research on any renewable: each investment is a lottery with escalating odds of a breakthrough that permanently improves its cost decay or capacity. Dead ends refund part of the spend. It is a push-your-luck loop that makes the learning-curve mechanic something you actively chase.
21. **[SMALL]** A one-step "undo last build" within the same round (free), disabled in an opt-in Ironman toggle where every action is final. It's a quality-of-life feature and a bragging-rights challenge flag in one.
22. **[BIG]** Neighbour-grid trading lite (a scoped-down C3). A second AI grid whose surplus/shortfall varies; each round you can export surplus or import to cover a shortfall at a negotiated price, but interconnector capacity is limited. It brings cooperation and timing to the game without simulating two full grids.
23. **[SMALL]** Hidden achievements only shown as "???": one-of-a-kind feats like "run the grid on 100% hydro for 5 rounds," "survive a heatwave with zero fossil," "retire every coal plant in a single round." It reuses the achievements framework for discovery.
24. **[BIG]** Storm-prep tower-defence rounds: severe weather is forecast a few rounds out with a track and a damage radius. You can spend funds to harden (wear reset, insulation, backup) certain plants before it lands. It gives maintenance and aging a proactive, foresight-driven use beyond the schedule dropdown.
25. **[SMALL]** Surprise grants: a random small funding windfall or inspection fine appears occasionally as a two-button choice (accept the strings-attached grant or decline). It's a moment of luck and choice that breaks up the fixed round loop.
26. **[SMALL]** Scoreboard of personal bests (fewest rounds to 90% clean, highest grade, longest clean streak) shown in the Career panel with a "new record!" flash. It gives runs a target to chase per attempt.
27. **[BIG]** Speedrun/challenge set: Net-Zero Sprint (90% clean in 20 rounds), Coal Forever (reach A grade while keeping 2 coal plants), Frugal (never spend above 300 funds), Nuclear Renaissance (win with no wind or solar). Each has a badge and its own save-persistent best, and they are opt-in harder modes.
28. **[SMALL]** Animated needle balance gauge for supply vs demand: it wobbles and settles, spikes red into the "brownout" zone with a shake, and clicks satisfyingly when you nail the match. It is juice on the core comparison you make every round.
29. **[BIG]** Daily seeded grid: the date determines demand shape, weather rolls, and a fixed event schedule, so all players face the same run. Your score sits beside your own history (a friend-comparison via multiplayer later). It brings replay value cheaply and reuses the scenario system.
30. **[SMALL]** A "skip the tutorial" veteran bonus: finishing a first Grade-A run unlocks a "Hardcore operator" title with a subtle skyline badge, and a customisable grid banner colour. It gives status and cosmetic reward for mastery.

---

**Notes.** Overlaps: Canopy 3/19 and Grid 2/29 (roguelike run + daily seed) and both games' challenge-run sets (Canopy 17, Grid 27) and hidden achievements/almanac ideas could share one "seeded run + boons" framework. Canopy 24 (tidal wetland) overlaps Tide and the open B1; Grid 22 is a smaller cousin of the deferred C3 and Grid 18 (market) resembles Trade Empire, so decide where trading lives. Grid 12/14 and Canopy 12 add lightly humane "who's affected" flavour that can be cut if it feels like a lesson.

---

## GD. Tide (gamified)

1. **[BIG]** **Tidewarden roguelike mode.** A "Season Rush" run where every 4 seasons you pick 1 of 3 random "Council Edicts" (e.g. "Fishing boom: Output +40% but acidity rises 25% faster", "Wetland grant: free sandbag tier, heritage upkeep doubled"). Edicts stack into a build across a 20-season run, so each run plays differently; it sits on top of the existing invest/advance loop and OUTPUT_MIX and ADAPTATION_TIERS multipliers.
2. **[BIG]** **Meta-progression "Harbor Charter".** Finishing runs earns Charter Marks spent on permanent, Tide-only unlocks (a starting Sandbag tier, a second Monitor charge, a new starting Edict slot, cosmetic pier styles). Kept inside Tide's own localStorage, not shared across games, and it leans on the existing achievements list to grant marks.
3. **[BIG]** **Storm Season as a boss fight.** Turn the every-5-seasons storm (STORM_INTERVAL) into a telegraphed "boss": the forecast shows surge height and the player gets two seasons to pre-commit funds to a "brace" allocation (barriers, evacuate heritage, stockpile). Success or failure plays out on the coastline grid with a wave-crash animation and a tiered result (Shrugged Off / Battered / Breached).
4. **[BIG]** **Two-lag puzzle mode ("Tidal Chess").** A challenge mode where fish lag and a new "runoff lag" (industry pollution feeds acidity 2 seasons late) both hit at once, and the player sees only the fish-yield warning. Score is how few seasons dip below FISH_YIELD_WARNING_THRESHOLD; it turns the delayed-consequence core into a forecasting puzzle you can get good at.
5. **[BIG]** **Daily Tide seed.** A once-a-day fixed run (sea scenario, storm timing, edict offers seeded by date) with a shareable result line ("Day 14: 11 seasons, 2 rows lost, 1 site saved"). Same seed for everyone gives comparison and a reason to return, and the seeded deterministic pattern matches Aftermath's severity hash.
6. **[BIG]** **Rival settlement ghost.** Race a computer-run "neighbor town" playing a fixed strategy (greedy industrialist, cautious wall-builder, diversifier) shown as a faint second coastline strip beside yours. Beating each rival's final population/funds unlocks their strategy as a starting preset.
7. **[BIG]** **Reef Builder side-board.** Add a small 3x4 reef plot under the coastline where spending "Reduction" points plants coral tiles that grow over seasons, soften storm surge, and boost fish yield in adjacent columns. Tile placement is a light puzzle (adjacency bonuses, bleaching when acidity spikes) and reuses the existing grid renderer.
8. **[BIG]** **Trade winds: market events.** Random season events offer risk-reward deals: a fish-export contract (big funds if yield above 80%, penalty if not), a tourism boom, an insurance payout. Player accepts/declines one per event; deals interact with D11 diversification levels and are a tension source between storms.
9. **[BIG]** **Coastal Empire scoring: the Postcard Ending.** At session end the game renders a pixel "postcard" of your settlement built from actual state (walls, reef, heritage sites, boats per population tier, flooded rows as sunken roofs) with a letter grade and a nickname ("The Salt Fortress"). Collecting all postcard variants is a light completionist hook.
10. **[BIG]** **Fixed-scenario puzzle levels.** A "Harbor Trials" campaign of hand-made starts (e.g. 15 seasons, 200 funds, already-high acidity, two heritage sites, only 3 invests allowed per season) each with a par score and 3 stars. Levels are short, tight, and replayable for stars, distinct from the open sandbox.
11. **[BIG]** **Crew and specialists.** Hire up to three specialist crew (Marine Biologist: fish lag reads one season shorter; Harbor Engineer: tier costs -15%; Broker: better deal odds). Each has a pay-per-season upkeep, so which three you can afford is a real build decision.
12. **[BIG]** **Boss: the Acid Tide.** Around season 15 an optional mega-event pushes acidity toward a spike unless you spend a big "buffer" (a chunk of funds plus reduction). Survive it and the fish recovery banner becomes a full victory beat; skip it and fish crash hard, a clear bet on your own read of the meters.
13. **[SMALL]** **Seasonal "Lucky Catch" mini reveal.** Each Advance Season has a small chance of a bonus haul shown as a net-cast animation with a funds pop ("+35 lucky catch"), more likely at high fish yield. Cheap variable-reward juice that makes healthy oceans feel good.
14. **[SMALL]** **Combo meter for consecutive balanced seasons.** Invest in all three categories in a season to build a x1.1 / x1.2 / x1.3 income streak; skipping a category breaks it. Adds a tiny tempo and a reason to spread spending.
15. **[SMALL]** **Wave-crash screen juice on flood.** When a row floods, the row's tiles ripple in sequence with a brief screen shake and a soft splash text ("glub"), and the flash from D8 gains a foam edge. Feedback that makes losing land feel dramatic without getting bleak.
16. **[SMALL]** **Boat traffic scaled to prosperity.** Tiny boat sprites drift across the scene; more appear with higher fish yield and population, and they vanish (leaving one abandoned hull) after a crash. Pure ambient feedback for how you're doing.
17. **[SMALL]** **Named crew quips.** A one-line ticker voice from the harbor master ("Wall's holding, boss. Ask me again in five seasons.") triggered by real state changes, with a settings switch to mute it. Adds personality and humor; the "story off" toggle the user asked for.
18. **[SMALL]** **Secret coastline critters.** After certain conditions (acidity below 20 for 5 seasons; a heritage site saved through a storm) a hidden critter (a seal, a whale fin) pops onto the scene and can be clicked to log it in a small "Sightings" list. Discovery bait that rewards good stewardship without a lesson.
19. **[SMALL]** **Pin-a-goal banner.** Player sets one personal goal from a dropdown ("Keep 4 rows dry", "Reach 200 population") that shows a tiny progress bar under the header and pings when hit. Self-directed targets for sandbox play.
20. **[SMALL]** **Undo one season (limited).** One "Rewind Tide" charge per run lets you retract the last Advance Season; using it marks the run with a small tin-hat icon so leaderboards/summary stay honest. Lowers fear of a bad click while keeping decisions weighty.
21. **[SMALL]** **Surge forecast dice.** The storm forecast text shows a rolled range ("surge 18-26, 70% chance to overtop Seawalls") drawn as a little bell-curve chip, making the wall decision a gamble to read rather than a number to compare.
22. **[SMALL]** **Achievement cosmetic rewards.** Certain existing achievements (fortified_in_time, stocks_rebound) unlock cosmetic themes for the scene: dusk sky, storm-glass, coral-pink sand. Small, instant reward for goals already in the list.
23. **[SMALL]** **Speedrun timer + best-seasons record.** Optional "fewest clicks / fewest seconds to max tier" personal-best trackers displayed in the session summary. Gives min-maxers a challenge target in the same per-browser record slot as best-coastline-saved.
24. **[SMALL]** **Hard-lag "ironman" badge.** Finishing a 20-season run in Hard Lag mode without ever using Rewind or the checkpoint replay awards a gold-anchor badge on the header and settlement history. Opt-in prestige for people who want the harder take.
25. **[SMALL]** **Streak-of-quiet-seasons counter.** A small counter of seasons since your last acidity rise, with a glowing frame at 5 and 10. Small, hypnotic "don't break the chain" pressure that fits the meter view.
26. **[SMALL]** **Random settlement name generator dice.** A dice button by the settlement name input rolls fun harbor names ("Port Regret", "Kelp Junction", "Brine-on-Sea") and the chronicle references it. Personality that costs almost nothing.
27. **[SMALL]** **Heritage-site rescue moment.** When a heritage site is saved at the last second before its row floods, play a short rescue flourish (a lifeboat icon, "SAVED!" burst) and a chronicle entry. Turns an existing mechanic into a highlight reel moment.
28. **[SMALL]** **Chain-reaction "Domino" callout on total loss.** If several rows flood in one season the ticker calls it a "Domino Season" with a scoreboard-style tally; it also awards a small "comeback" bonus (temporary cheaper barriers) so a disaster becomes a pivot rather than a death spiral.
29. **[SMALL]** **Toggle for chunky retro sound-style visual cues.** With no audio in the hub, add optional "sound-word" popups ("SPLASH", "KA-CHING", "CRUNCH") on major events as comic-style burst text, off by default in Settings. Personality and feedback without needing an audio system.
30. **[SMALL]** **Season-end "report card" flash.** A 1-second overlay after each Advance Season with three quick stat chips (funds delta, acidity delta, fish delta) colored by good/bad plus an icon, then fading. Faster to read than the ticker and makes each turn feel like it landed.

---

## GE. Aftermath (gamified)

1. **[BIG]** **Event draft: choose your prep card.** Before each event, draw 3 "prep cards" (Sandbag Wall: -30% flood damage this event; Emergency Rations: -30% supply damage; Mediation Team: -30% unrest damage) and pick one to play. Decks are shaped by unlocked skills, so the skill tree becomes a deck-builder for run-time decisions.
2. **[BIG]** **Skill tree as deck: choose a loadout of 4.** Unlocked skills stay owned forever, but only 4 can be "slotted" into a run. Choosing which 4 for the coming schedule (coastal flood-heavy? social-heavy?) makes the tree a build puzzle instead of a checklist.
3. **[BIG]** **Hidden-schedule "fog of war" mode.** Opt-in mode where the next 3 events are hidden until an early warning skill reveals them (Early Warning = 1 event ahead, Mutual Aid = 2). Players must gamble resilience vs. growth without knowing which shock is next, and the skill finally has a felt payoff.
4. **[BIG]** **Boss event: the Compound Disaster.** A rare final event chains two types at once (Storm + Infrastructure Failure), shown as a two-phase fight where the player gets one emergency action between phases. Optional 8th event on extended runs, big knowledge-point payout for surviving.
5. **[BIG]** **Roguelike "Descent" mode.** Chain runs with no reset between them: settlement damage and resources carry over across 5 back-to-back schedules while severity climbs; you bank knowledge points only when you "evacuate" or finish, and lose half if the settlement collapses. Push-your-luck on top of the run loop with permanent tree unlocks as the safety net.
6. **[BIG]** **Emergency actions with cooldowns.** During a run, unlock "Deploy Crews", "Open Shelters", "Ration Supplies" as one-time-per-run emergency buttons that trade resources for a burst mitigation on the current event. Adds a mid-event decision instead of only between-event allocation.
7. **[BIG]** **Ironman schedule variants ("Cursed Seasons").** Pick a curse before a run (All floods x1.5, growth income halved, no early warning) for a scaling knowledge-point multiplier. Opt-in harder modes with clear rewards that reward mastery; stack up to 3 curses for bragging-rights tiers.
8. **[BIG]** **Settlement districts on a small map.** A 3x3 grid of districts (harbor, market, hill, etc.) where resilience and growth units are placed; events hit specific districts based on type (floods hit harbor and market). Placement becomes a spatial puzzle rather than a single pool of points.
9. **[BIG]** **Citizen roster: people with quirks.** Recruit 3 named citizens per run from a random pool (The Engineer cuts infrastructure damage, The Organizer softens unrest, The Gambler boosts growth with a risk). Their fates after events feed the legacy system and each run reads differently.
10. **[BIG]** **Prestige: "Second Founding".** After buying every skill, reset the tree for a permanent prestige star that adds a small starting perk and unlocks 3 "Founding-only" alternate skills with strong tradeoffs. Gives veteran players a long-term loop.
11. **[BIG]** **Challenge gauntlet: weekly-style fixed schedules.** A rotating list of hand-built schedules ("The Three Floods", "Blackout Week", "Everyone Is Angry") with fixed severities and a par score, separate from the regular hash-severity runs. Repeatable puzzles with a target to beat.
12. **[BIG]** **Insurance and gambling on the next event.** Between events the player can buy insurance (pay now, recover 60% of the next event's damage) or double-down a bet (pay resources for a bonus if damage stays below the preview range). Uses the E8/E14 expected-damage range as the odds display.
13. **[SMALL]** **Damage-avoided popup with combo.** After each event, show a big "-58 damage prevented!" number that counts up in a satisfying tally, plus a mini streak if mitigation held two events in a row. Makes prevention feel like scoring.
14. **[SMALL]** **Event screen shake and category flash.** Each event category gets a short signature hit (flood: blue ripple, heatwave: orange pulse, unrest: red shudder) plus emphasized numbers on the resolution panel. Quick, visceral feedback for a system that's currently text-forward.
15. **[SMALL]** **Perfect Run badge: zero-damage event.** If mitigation reduces an event's damage to under 10% of base, flash "Flawless Defense!" and grant a bonus knowledge point. A crisp mastery target, sits with the E15 achievement family.
16. **[SMALL]** **Skill unlock reveal animation.** Newly bought skills glow-pulse on the tree and connect lines "light up" toward newly available prereq-gated children, with a satisfying click. Discovering the next branch feels like unwrapping.
17. **[SMALL]** **Mystery skill nodes.** A couple of "?" nodes in the tree show no description until their prereqs are bought, then reveal a surprise perk (like "Lucky Break: 10% chance an event is halved"). Discovery pressure to keep exploring the tree.
18. **[SMALL]** **Undo last allocation click.** Within a between-event phase, let the player undo their last resilience/growth click before pressing Resolve; a small counter shows undo uses for anyone racing. Lowers misclick pain while keeping choices meaningful.
19. **[SMALL]** **Weekly-style "Mutation of the day".** A daily random modifier (severity x1.2 for floods, growth cost -3) displayed on the run screen, deterministic by date so it feels like the same day for everyone. Cheap novelty that helps returning players.
20. **[SMALL]** **Settlement mood emoji strip.** A row of tiny citizen faces that shift from grinning to grim as resources and resilience move, updating per allocation click. Immediate, glanceable, humorous feedback on where you stand.
21. **[SMALL]** **Post-run one-liner "epitaph".** Each run ends with a randomly picked witty line from a large bank keyed to outcomes ("The levee held. The mayor did not." / "Nobody panicked. Everybody panicked politely."). Personality that makes bad runs funny, with a settings toggle to hide it.
22. **[SMALL]** **Streak of consecutive runs beating your prior best.** A little fire counter appears at 2+ consecutive improvements in run score with a warm glow on the run history list. Encourages "one more run" momentum.
23. **[SMALL]** **Speedrun clock for the run.** Optional visible timer plus a best-time-to-finish column in Review Past Runs; times don't affect score, only a badge. Adds a race angle for a very short-run game.
24. **[SMALL]** **Random starting twist.** Each run begins with one random "quirk" (Rich Start: +60 resources, no growth; Fortified Slum: +2 resilience, -1 growth). Small variance in the opening makes every run start with a decision.
25. **[SMALL]** **Unlock-tier cosmetic settlement skins.** Reaching skill thresholds (5, 10, all) changes the settlement art (thatched, timber, concrete) shown at run start and in history. A visible payoff for the tree that costs no balance.
26. **[SMALL]** **Event countdown pulse.** As the resolve button nears (event about to hit), the schedule strip gently pulses and the next event icon grows slightly, adding a bit of dread. Pure tension juice.
27. **[SMALL]** **Lucky charm rolls.** Rare 5% chance an event's severity draws a "lucky break" (severity x0.7) or "dark omen" (x1.3) with a special banner; the deterministic hash decides which, so it's fair but surprising. Increases variance in a fun way.
28. **[SMALL]** **Knowledge-point "critical insight".** Each run has a small chance to award a doubled KP on a perfect defense, shown with sparkle text. Occasional jackpot moments keep the currency exciting.
29. **[SMALL]** **Run recap "highlight reel".** The end-of-run panel plays a 5-second sequence of the run's biggest events (worst hit, best save) as animated cards instead of a static list. Lets a run end on a story beat instead of a table.
30. **[SMALL]** **Named legacy monuments.** Extremely good runs (top-3 score) permanently add a small monument icon to the settlement art with your chosen settlement name on a plaque. A visible trophy shelf for the legacy system.

---

**Notes:** Tide's Edict roguelike (#1), Charter meta-progression (#2), and daily seed (#5) and Aftermath's Descent (#5), curse modes (#7), and daily mutation (#19) are the same shapes; a shared "daily seed + opt-in curse" helper in `shared/` could serve both plus other climate games. Tide #17 / Aftermath #21 (witty voice lines with a mute toggle) and both games' "cosmetic unlocks" (Tide #22, Aftermath #25) overlap across games and could be built once as a shared pattern. Aftermath #1 (prep cards) and #2 (loadout of 4) are alternatives to each other; pick one route for the tree-as-deck idea, and Aftermath #12 interacts with the existing E17a scenario pack and E29 societal-memory items on the TODO.

---

## GF. Herd (gamified)

1. **[BIG]** **Ranch Run (roguelike mode).** A 20-round run where each round offers a "draft" of three random cards (a cheap feed additive, a shady subsidy, a viral-beef-trend market spike, a drought) and the player keeps one, building a synergy stack around the existing levers (feed, caps, capture, breeding, supply chain). Ends with a score and a run seed, so runs feel different every time instead of one solved optimal path.
2. **[BIG]** **Ranch Legacy unlock tree (in-game meta-progression).** Every finished run earns "heritage points" spent on permanent perks inside Herd only: start with one capture unit, a 2nd policy-advisor option, a rare breed with better breeding odds, a new farmhouse skin. Certification and poultry become early goals a run can chase rather than a one-off unlock.
3. **[BIG]** **Boss-round "Auditor" events.** Every 10th round a regulator audit arrives with a visible target (e.g. "coupling under 0.6 AND welfare over 60"); you get 3 rounds of warning to reshape the farm. Pass and you earn a big permanent perk, fail and you eat a fine and a market-trust hit. Gives the flat round loop deadlines and set-piece tension.
4. **[BIG]** **Rival ranch (ghost opponent).** A simulated neighbour farm plays a fixed strategy (pure growth, pure restraint, or a copy of the community's median), with its score and herd shown live on a scoreboard strip. Beating it in dollars AND methane is the win; rival personalities (Big Ag Barry, Organic Olive) add humour and different pressures.
5. **[BIG]** **Combo engine: decoupling chains.** Buying levers in certain orders triggers named combos ("Circular Barn": capture + biofilter + litter gives free biogas income; "Happy Herd": feed + welfare + breeding). Each combo is discoverable, shown as a grey silhouette in a combo book, and rewards clever build order rather than just spending.
6. **[BIG]** **Ranch-of-the-Week seed challenge.** A date-seeded run with fixed events, handicaps and a modifier ("no capture systems, double weather swings"). The score is compared against the community percentile using the existing Z1 stats path, with a personal history strip of weekly results.
7. **[BIG]** **Market crash / commodity trading side-game.** A tiny price ticker for meat, dairy and eggs where you can hold "contracts" (lock next 3 rounds at today's price). Correct calls give big income spikes, bad ones sting, and it interacts with the season swings and plant-demand surges already in the opt-in mode.
8. **[BIG]** **Disaster season: events with counterplay.** Random heatwave, disease outbreak, feed-price spike and flood events land with a 2-round telegraph, and each can be blunted by a specific lever (welfare and breeding vs disease, capture vs a regulator visit). Turns the passive weather layer into tension with clever prep rewards.
9. **[BIG]** **Ranch expansion map.** A small grid of paddocks where herd units are physically placed; neighbouring paddocks share bonuses (capture pipes link, biofilters cover adjacent poultry sheds). Placement puzzles add spatial strategy and give the pasture illustration a real job.
10. **[BIG]** **Story mode: "The Family Farm" (toggleable).** A branching narrative where Grandpa's farm faces choices (sell to an agribusiness, go organic, take the subsidy) with light vignettes and 3 endings, layered on the existing farm-tour vignettes. Fully skippable via a story toggle, with the sim unchanged underneath.
11. **[BIG]** **Speed-run and score-attack ladder.** Named challenge modes ("Decouple by round 12", "Max profit under a 15 methane cap", "Poultry only") with their own bronze/silver/gold medals and an in-game trophy shelf. Builds on the cap mode and the counterfactual baseline that already exist.
12. **[SMALL]** **Herd juice: cow reactions.** Cows in the pasture visual moo bubble, hop or nap depending on welfare and coupling, and clicking one gives a silly quip. Purely fun feedback on data already in the game.
13. **[SMALL]** **Named cows.** Herd units get randomly generated names (Beyonmoo, Sir Grazealot) shown on hover, and a "retired hall of fame" lists your longest-serving ones. Cheap personality that makes losing herd units to a cap feel like something.
14. **[SMALL]** **Satisfying "cha-ching" round summary.** The end-of-round tally counts up funds with a ticking rolling number and a small confetti burst when the round beats the last one. Pure juice on the Advance Round moment.
15. **[SMALL]** **Perfect-round streak counter.** A visible streak of consecutive rounds where methane fell AND funds rose, with a flame icon and a tiny bonus at 3/5/10. Adds a "don't break the chain" tension without new systems.
16. **[SMALL]** **Secret breed: the Methane-Eater Cow.** A hidden herd unit that unlocks only if you hit an odd condition (e.g. coupling under 0.25 while welfare is over 90) and shows a glowing sprite plus a shelf achievement. Rewards mastery with a discovery moment.
17. **[SMALL]** **Achievement-gated cosmetic barns.** Earning certain achievements unlocks alternate barn/fence/tractor skins for the pasture hero image, selectable in the extras panel. Achievements over callouts, with a visible reward.
18. **[SMALL]** **"Undo last round" with a cost.** Once per game (or per run in Ranch Run) you can rewind one round at the price of a fund penalty. Lets players experiment with risky levers and cuts the fear of misclicks.
19. **[SMALL]** **Tractor sound and haptic-style animation stubs.** A short animated tractor crosses the screen on Advance Round, and buttons squish on press, all CSS-only and reduced-motion respecting (no audio, per the hub's standing decision). Gives clicks a tactile feel.
20. **[SMALL]** **Random farm event card.** Each round has a 20% chance of a one-line flavour event with a two-button choice ("Neighbour offers to buy 2 units: cash or refuse") and small stakes. Breaks up routine with humour and micro-decisions.
21. **[SMALL]** **Golden-cow bonus round.** Rarely, a golden cow glides across the pasture; clicking it in time grants a one-off funds bonus. A light, whimsical idle-game style reward that rewards attention.
22. **[SMALL]** **Rating title ladder.** The report card grants a title from "Hobby Farmer" to "Decoupling Legend" with a tiny cartoon, and it shows the next title's requirement. Replay goal without a lecture.
23. **[SMALL]** **Loadout presets for new runs.** Choose a starting loadout (Big Herd, Lean Green, Poultry Start, Cash Rich) that bends opening funds/levers, unlocked as achievements accrue. A quick way to vary each opening.
24. **[SMALL]** **Dev-mode "what if" sandbox toggle.** Unlock a sandbox where you set herd size, methane and levers freely and watch the gauge react, with no scoring. Rewards discovery and gives power users a toy.
25. **[SMALL]** **Feed additive minigame.** Investing in feed opens a 5-second click-timing mixer (hit the green band) whose result nudges that round's effect by a few percent. Small skill layer, purely optional (auto-resolve button).
26. **[SMALL]** **Rival taunts and cheers.** Rival ranch and policy advisor deliver one-liners in a small speech bubble after each round based on your standing. Personality-only, uses existing vignette plumbing.
27. **[SMALL]** **Mystery crate after certification.** Reaching the certification milestone triggers a "crate" with a random cosmetic or small perk and a satisfying open animation. Makes the prestige moment feel like a reward.
28. **[SMALL]** **Hard mode: no baseline peek (blind run).** An opt-in mode that hides the counterfactual and gauge best-markers until the run ends, so decisions rely on feel. Reveals a stronger reveal at the end.
29. **[SMALL]** **Per-run stat "highlights reel".** After a run, a 3-line recap picks funny moments ("Peak herd: 42, biggest single-round swing: +38 funds"). Personal, screenshot-friendly, makes runs feel memorable.
30. **[SMALL]** **Daily perk pick.** Each calendar day the first run offers one of two random small boons (e.g. +5% feed effect) to try. Pulls players back with light variety without demanding attention.

---

## GG. Thaw (gamified)

1. **[BIG]** **Expedition roguelike: "Permafrost Watch".** A run mode where each round you draw three research-station cards (drone survey, insulating mats, emergency crew, a risky private grant) and keep one, tuning how you dampen the feedback across regions A/B/C. Runs end at a fixed round with a score, so the tipping point becomes a per-run story rather than one learned path.
2. **[BIG]** **Tipping-point survival mode: hold the line.** A single objective mode: keep at least two of the three regions un-tipped for N rounds while the background rise steadily gets harsher (new escalation events). Score is rounds survived, giving Thaw a tense "how far can I push" feel with a leaderboard-friendly number.
3. **[BIG]** **Station Upgrade tree (in-game meta-progression).** Finishing runs earns "research credit" spent on permanent Thaw-only upgrades: a better monitoring tower (earlier warning on the next-round tooltip), starter dampening, a 4th preset strategy, or a wider mini-graph. Long-run replay reasons that feel different from Herd's or Loop's.
4. **[BIG]** **Crisis events with a clock.** Random events (wildfire, sinkhole road, unusual heatwave, bad research funding year) appear with a 2-3 round countdown; spending the right resource (monitor for early response, preserve for slump) defuses them. Adds spikes of urgency on top of the steady slope.
5. **[BIG]** **Resource routing between regions.** Let funds "convoy" between A, B and C with a small transport tax so the player is constantly weighing rescuing a critical region against feeding a healthy one. Adds triage decisions and makes the three-region view a real puzzle.
6. **[BIG]** **Hidden-variable regions ("survey mode").** Regions start with unknown permafrost carbon density, revealed only by paying for a survey; a rich region tips harder but also yields more output. Risk-reward discovery layered on the existing melt and dampening math.
7. **[BIG]** **Daily "Cold Case" seed challenge.** A date-seeded scenario with fixed starting temperatures and one twist ("Region B starts already thawing", "Monitoring costs double"). Compare your temperature-saved score with the community percentile through the existing Z1 stats hook.
8. **[BIG]** **Sandbox "director" mode: you are the climate.** Flip roles for a run: choose when to push background rise bumps (volcano, heat dome) to try to tip regions controlled by an AI steward of varying skill. A playful inversion that teaches the same dynamics as a toy.
9. **[BIG]** **Challenge ladder with modifiers.** Named runs like "Minimalist" (no output spending), "All-in Output until melt, then pivot", "Blind (graph hidden until round 10)" with medals and a trophy shelf. Small rule changes create big strategy differences on the same engine.
10. **[BIG]** **Timed "quick crisis" minigame between rounds.** When a region enters critical tier, an optional 10-second stabilise minigame (route sensors, plug leaks, click hotspots) grants a temporary dampening buff. Skippable by auto-resolve, so it adds skill flavour without gating the sim.
11. **[BIG]** **Story mode: "The Station Crew" (toggleable).** A small ensemble cast at a research station comments on each region across the run with 3 endings depending on your spread of outcomes, and a story-off toggle strips it back. Personality and stakes for a game that otherwise reads as a graph.
12. **[SMALL]** **Screen-shake and rumble on tipping.** The tipping flash gains a brief low-frequency shake of the region card and a crack animation across its mini-graph. Amplifies the best drama beat with juice only.
13. **[SMALL]** **Streak medal: "Ice Age".** A visible medal counts consecutive rounds a region stays below the melt threshold, expanding into a frosty icon at 5/10/15. Extends the existing rounds-since-tipping counter into a chase.
14. **[SMALL]** **Secret region D reward.** If you ever finish with Region A cooler than the auto-played worst-case D by 8+ degrees, a secret "Snow Leopard" badge and station skin unlock. Discovery reward for mastery.
15. **[SMALL]** **Penguin (or arctic fox) mascot reactions.** A tiny mascot in the corner reacts to state (shivers when hot, cheers when dampening rises, faints at critical). Humour and feedback for free using existing flags.
16. **[SMALL]** **Random research grant.** Each round has a small chance a grant note appears with a gamble ("Take 30 funds now, or 60 funds only if no region tips next round"). Micro risk/reward decisions.
17. **[SMALL]** **Undo once per run.** Rewind one round at a funds cost, making bold bets like gambling on Region C's tipping safer to try. Encourages experiment.
18. **[SMALL]** **Achievement-locked map skins.** Alternate visual themes (aurora borealis, siberian tundra at dusk, tundra in 8-bit) unlocked by achievements and selectable in settings. Achievements that give something visible.
19. **[SMALL]** **Thermometer rolling numbers.** The temperature readout ticks upward digit by digit like an odometer during Advance Round, faster when the loop is accelerating. Turns "the slope is steeper" into something you feel.
20. **[SMALL]** **"Close call" callout.** If a region's next-round projection would have crossed melt or critical but your last investment pulled it back, a brief "phew" banner appears. Rewards clever timing with instant feedback.
21. **[SMALL]** **Rival stewards on the scoreboard.** Three fixed AI stewards (Cautious Kai, Rash Rasmus, Balanced Bea) post temperature-saved scores each run, so you know exactly who you beat. Personality-driven target for the personal best.
22. **[SMALL]** **Mystery supply drop.** Every 6th round, a crate with a random perk (extra preserve unit, monitor discount, faster preset) appears with a satisfying opening animation. Pacing sprinkle for the middle of a run.
23. **[SMALL]** **Hard mode: no preview tooltip.** Opt-in mode disables the next-round three-region preview tooltip and dampening forecast, forcing intuition. The end-of-run reveal shows how close you were.
24. **[SMALL]** **Title ladder for runs.** Finishing a run grants a title from "Ice Cube" to "Cryosphere Guardian" by temperature-saved bands, with the next title's goal listed. Simple replay carrot.
25. **[SMALL]** **Blindfold graph toggle.** A variation that hides the mini-graphs and shows only text status, so players read the numbers instead of the curves. Novel challenge for veterans without any new content.
26. **[SMALL]** **Random flavour headlines.** After each round a ticker shows a funny fake headline reacting to conditions ("Local fox files complaint about mud"). Sets tone and adds humour.
27. **[SMALL]** **Perfect-balance bonus.** If all three regions end a round within 1 degree of each other, a small bonus and a chime-style pulse fire. Encourages keeping balance across regions as a soft mini goal.
28. **[SMALL]** **Highlights reel at session end.** A 3-line auto-recap from the scientist's log ("Region B tipped on round 9, you clawed it back by round 14"). Shareable, story-shaped end screen.
29. **[SMALL]** **Loadout presets per run.** Pick a starting posture (Scout, Builder, Gambler) that shifts starting funds and dampening, unlocked via the station upgrade tree or achievements. Varied openings each run.
30. **[SMALL]** **Daily boon.** First run each day offers a choice of two tiny boons (extra 10 funds, cheaper monitor). A soft-return hook with no pressure.

**Notes:** Roguelike draft, run-based meta-progression trees, daily/weekly seed challenges, challenge ladders, hard "blind" modes, undo, title ladders and highlights reels are near-identical across Herd (1/2/6/11/28/22/29) and Thaw (1/3/7/9/23/24/28), so build them once as shared hub scaffolding (run/seed manager, unlock-tree store, medal shelf, recap component) with per-game content on top. Personality items (mascots, rivals, headlines) also share a lightweight speech-bubble component; the crisis/audit event systems (Herd 3/8, Thaw 4) suit the same telegraphed-event engine. Nothing here duplicates F1/F25 (Herd) or G3/G5/G9/G13/G15/G17/G21/G23/G27/G29 (Thaw), all left untouched.

---

## GH. Loop (gamified)

Already built/on the TODO and deliberately not repeated: third partner, streak text bar, particle bursts, audit panel, text supply map, zero-waste/challenge-chain/consumer-behavior/material-passport/waste-stream/lifecycle-vignette (H23/H13/H17/H21/H9/H7, still open on the TODO). Pitches below are fun-first angles that hook into the real mechanics (Repair/Reuse/Recycle investments, the 50-unit production target, damage-driven extraction cost multiplier capped at 2.5x, funds, trade partners, goods categories, score).

1. **[BIG]** **Factory Blueprint roguelike run.** Each run starts by drafting 1 of 3 random "Founder Traits" (e.g. "Cheap Repairs: repair costs 15 instead of 20 but reuse costs +10", "Scrap Baron: recycling yields more but damage accrues faster") that bend the numbers in CIRCULARITY_INVESTMENTS. Every run plays differently, and the draft creates a build identity to chase across replays.
2. **[BIG]** **Boardroom Draft between cycles.** Every 5 cycles, offer three "policy cards" (Right-to-Repair Law, Deposit Scheme, Planned-Obsolescence Ban, Subsidy Blitz) with a permanent-for-this-run modifier and a real downside. Picking one of three, and living with the combo, is the deck-builder hook this game lacks.
3. **[BIG]** **Market Shock events.** Random-but-telegraphed events (commodity price spike, port strike blocking a trade partner for 3 cycles, viral "unboxing" trend that raises demand) hit the 50-unit production target and trade links. The player sees the shock one cycle early and can hedge, so a well-looped chain shrugs it off while a linear chain gets punished: tension without a fail-state.
4. **[BIG]** **Loop Lab meta-progression.** Finished chains earn "Patents" that permanently unlock in-game options: new investment variants (Modular Design, Take-Back Depots), extra starting funds tiers, a fourth investment slot. It stays inside Loop and gives the lifetime counters (chains completed, categories tried) a reason to exist beyond a badge.
5. **[BIG]** **Rival Corporation ghost.** A linear-economy AI competitor runs the same production target in parallel with a simple extraction-only policy and races you on cumulative profit. It is ahead early (cheap extraction) and falls behind as damage multiplies its costs, so the player feels the crossover point as a satisfying overtake.
6. **[BIG]** **Chain Puzzle Mode.** A set of hand-authored puzzle levels ("close this 40% chain in 6 cycles with 200 funds and no trade", "hit 90% circular using only Reuse"). Each has a par cycle count and 3-star ratings, giving short sessions, clear goals, and mastery-based replay.
7. **[BIG]** **Daily Seed chain.** One shared deterministic starting scenario per day (goods category, starting damage, event schedule) with a personal best score shown locally, or on the existing feedback/stats backend if it fits. Everyone plays the same puzzle, the vignette/featured-category weekly logic is already deterministic, so a daily seed extends it naturally.
8. **[BIG]** **Bottleneck mode: conveyor logistics.** Investments gain a throughput cap per node, so the player must balance repair, reuse and recycling capacity like a factory-builder (Factorio-lite) rather than dumping funds into the cheapest one. Overloading a node visibly backs up the flow particles, which finally makes the animated chain the core interaction rather than decoration.
9. **[BIG]** **Loop Tycoon idle layer.** After the first closed loop, unlock "Autopilot": cycles advance on a timer while the player spends funds on upgrades that raise automation tiers, with offline-style catch-up computed on return. It leans into the idle taste, pairs with the existing Advance Cycle, and keeps time-based work simple (compute elapsed cycles on load, no live audio or timers needed).
10. **[BIG]** **Prestige: Rebuild the Factory.** Once the loop is closed and score passes a bar, "Franchise" resets the chain in exchange for a permanent multiplier and a new tier of goods (Electronics, then Vehicles, then Buildings, each with harder base circularity). Long-term ladder, each tier feels like a new game with the same tools.
11. **[BIG]** **Sabotage cards for the challenge-seeker.** An opt-in "Chaos" toggle deals the player a malicious card each cycle (a supplier goes bankrupt, a batch is contaminated and recycling yield halves) with a visible counter-play cost. It is a hard mode people choose on purpose, matching the opt-in harder-mode taste.
12. **[SMALL]** **"Perfect Cycle" combo.** If a cycle hits the production target with zero new extraction, a combo counter climbs and multiplies that cycle's score bonus. Miss one and it drops to zero: a tiny, sticky score-chasing hook on top of the streak bar.
13. **[SMALL]** **Satisfying "clunk" on every investment.** Each Repair/Reuse/Recycle purchase makes the corresponding ring node snap, ring a ripple outward, and count up the extraction saved as floating "-4 raw" numbers. Pure juice, but it makes the core payoff loop feel physical.
14. **[SMALL]** **Secret goods category unlock.** Reaching 100% circular on all three normal categories unlocks a fourth hidden one (e.g. "Ship-Breaking Yard" or "Fast Fashion") with its own quirky vignette lines and a different starting fraction. Discovery reward that nudges the goods-explorer badge chain.
15. **[SMALL]** **Loop Score name plates.** Ending titles based on play style: "The Scrapper" (mostly recycle), "The Fixer" (mostly repair), "The Diplomat" (mostly trade), shown on the end screen. Cheap personality with an obvious "I want the other ones" replay pull.
16. **[SMALL]** **Damage meter cracks.** As the environmental damage meter climbs, the panel border gains visual "cracks" and the starfield dims slightly, easing back as circularity recovers. It supplies mood and stakes with no extra numbers to read.
17. **[SMALL]** **Golden Cycle.** Once per chain a random future cycle is silently "golden": whichever investment you buy that cycle gives double supply. Players who watch for the sparkle in the UI feel clever, and the surprise breaks the routine.
18. **[SMALL]** **Undo-one-cycle with a token.** Give one "Rewind" token per chain that reverts the last Advance Cycle. Removes frustration from misclicks while making the token itself a decision (when is a mistake worth spending it?).
19. **[SMALL]** **Snarky supply-chain narrator.** An optional one-line ticker under the chain comments on your play ("Your landfill sends its regards", "The mine is filing a complaint"), with a Settings toggle to switch it off per the existing story-toggle preference. Humor and personality with zero mechanical cost.
20. **[SMALL]** **Speed-loop achievement set.** New achievements such as "Closed the loop by cycle 12", "Closed with under 500 total extraction", and "Never used trade", surfaced only via the achievements panel (not callouts). Gives experienced players target runs.
21. **[SMALL]** **Import-export minigame beat.** When trading, show a short two-choice gamble ("sell at 3.0 now or hold a cycle for a 50% chance at 5.0") before the price applies. Adds a small risk-reward pulse to trade decisions without a new screen.
22. **[SMALL]** **Fun facts as unlockable "Trading Cards".** Each goods category has 6 collectable cards that unlock at fraction thresholds, with art-free stat blocks styled like a TCG (rarity, "Recycle-ability 7/10"). The collection and rarity are the hook; the info is incidental flavor.
23. **[SMALL]** **Color-swappable ring themes.** Unlock cosmetic ring palettes (Neon, Blueprint, Paper Cut-out) through achievements and swap them in Settings. Cosmetic meta-progression that rewards play without touching balance.
24. **[SMALL]** **Streak insurance.** Spend 10 funds once per chain to "freeze" the closed-loop streak through one bad cycle (e.g. after a shock). A small resource sink with real risk-management weight.
25. **[SMALL]** **Near-miss messaging.** When a cycle finishes at 47/50 units, flash "So close: 3 units short!" and show the cheapest one-click fix that would have covered it. It turns a fail into an immediate "next time" resolve, a classic retention nudge.
26. **[BIG]** **Landfill Mining reverse-engineering mode.** Start with a huge sitting waste heap (past-you's linear mistakes) as a resource pool; the player spends funds to dig it back into the loop, with "toxicity" that costs extra unless Repair/Reuse is high. The puzzle of unwinding a mess offers a different opening and a satisfying "cleaning up" arc.
27. **[BIG]** **Two-chain juggling.** Run two categories at once (e.g. Electronics and Clothing) sharing one funds pool and one damage meter, with trade partners forced to pick a side each cycle. It doubles the decision density for veterans and lets investments in one chain spill over as by-products for the other.
28. **[BIG]** **Ghost replay sharing.** After a run, export a compact "run code" (investments per cycle) that another player can load as a ghost line on their own supply-fraction graph to beat. Uses the existing save-code convention, gives a social competition without a new backend.
29. **[SMALL]** **Sound-free "juice" haptics for mobile.** Add subtle vibration on investment and on 25% milestones where the browser allows, off by default in Settings. Tactile feedback on phones costs almost nothing.
30. **[SMALL]** **Mystery Box crate.** Each closed-loop milestone grants a "Crate" that reveals a random small perk (+10 funds, a free investment discount, a cosmetic ring node), opened with a short shake animation. It leans into surprise-reward flavor while staying cosmetic-light.

---

## GI. Drift (gamified)

Already built/on the TODO and not repeated: second region (I1), policy toolkit (I3), regional network (I7), second wave (I25), cross-region learning (I29), reallocation, forecast, crisis start, ROI dashboard, coda legacy choices, thriving vignette. The framing here stays institutional and respectful (no gore, no "win the refugees" tone); the fun comes from budgeting under pressure, tempo, and choice. Hooks: housing/services/infrastructure capacity, background severity rising 0.5/round, arrivals pipeline (pending vs integrated), strain levels, composite wellbeing, control region, personal best in localStorage.

1. **[BIG]** **Mayor's Council draft.** Every 10 rounds the region council offers three named "civic programs" (Night-School Network, Rapid Housing Modules, Transit Expansion) with a permanent run-long effect and a trade-off. A deck-builder-style draft gives runs distinct identities without changing the core three capacities.
2. **[BIG]** **Crisis event deck.** Telegraphed events (a sudden surge round, budget cut, a bumper harvest boosting income, a flood damaging infrastructure) appear one round ahead in a "Next Round" preview. The player can pay to brace, which gives tension and clever-decision moments while remaining recoverable, not a fail state.
3. **[BIG]** **Advisors as a party.** Recruit up to three specialist advisors (Housing Planner, Language Teacher, Logistics Chief) who each add a small passive bonus and a "special move" with cooldown (e.g. "Surge Build: housing is half price this round"). Choosing whom to hire, and when to fire the special, gives clear mastery.
4. **[BIG]** **Scenario roster with unlock ladder.** A "Region Atlas" of preset starting regions (Coastal Port, Mountain Valley, Border Junction, Post-Industrial Town) each with a distinct capacity/income profile; clearing one at a target wellbeing unlocks the next. It gives structured meta-progression and replay value inside Drift itself, with I15 crisis start reused for the last tier.
5. **[BIG]** **Idle "Budget Autopilot".** Set standing allocation rules ("keep services at 60%, spend surplus on housing") and let rounds auto-advance quickly while the player tunes the rules. The game becomes a systems-tuning puzzle, echoing the idle-loved taste, and rewards players who can write robust rules against the severity curve.
6. **[BIG]** **Rival Region leaderboard ghosts.** Run against 3 named AI-managed regions with distinct personalities (Frugal, Builder, Reactive) on the same severity curve, shown as lines on the existing trend graph. Beating them by round 60 feels like a competitive game; the passive control region already provides the ghost-line pattern.
7. **[BIG]** **Grant Applications minigame.** Periodically a set of funding grants appear, each requiring a specific capacity mix in place by a deadline (e.g. "Services >= 40 within 5 rounds for +100 funds"). It gives the player short-term objectives layered over the open-ended long game, with tension from deadline versus arrival pressure.
8. **[BIG]** **Tetris-style capacity blocks.** Replace pure sliders with a grid where each building (housing block, school, clinic) occupies a footprint on a small city map and adjacency gives bonuses (school next to housing boosts services). Uses the existing 6-building region visual as the seed, and delivers a genuine spatial puzzle.
9. **[BIG]** **Prestige: Legacy Points.** Ending a run at Model Region banks Legacy Points spent on a permanent unlock tree (start with +20 funds, unlock a fourth capacity type "Community Spaces", unlock Hard Mode tiers). Different from I29's single efficiency bonus: a full tree with branching choices.
10. **[BIG]** **Timeline scrubber "what-if".** After a run, replay from any round with one changed decision and see the wellbeing curve diverge against the original. The game turns into mastery through experimentation, and it can reuse `subscore_log` and the trend graph data.
11. **[BIG]** **Boss rounds: severity spikes.** Rounds 25, 50 and 75 are named "surge" tests (a big arrivals spike scaled to the severity curve) with a preview and a bespoke celebratory "held the line" card if capacity covers it. Gives the long timeline a rhythm and something to build toward.
12. **[BIG]** **Weekly Region Challenge seed.** A deterministic weekly starting profile plus a fixed event schedule, with personal best displayed via the existing localStorage personal-best mechanism. Gives a reason to return without a backend.
13. **[SMALL]** **Perfect Fit streak.** If capacity exactly covers the round's arrivals (within a small margin) with no wasted overbuilding, a "Perfect Fit" counter grows and adds a small wellbeing bonus. Rewards precise forecasting, and pairs with the forecast panel that already exists.
14. **[SMALL]** **Building "pop" animation.** Each investment spawns a building on the region visual with a quick rise-and-settle bounce and a tiny dust puff. Pure juice for the most repeated action in the game.
15. **[SMALL]** **Region personality title.** End-of-run title from your spending pattern: "The Builder" (housing-heavy), "The Educator" (services-heavy), "The Engineer" (infrastructure-heavy), "The Balancer". Collectible identities encourage replaying with a different style.
16. **[SMALL]** **Lucky Break event.** Rarely, a small windfall (community donation, volunteer wave: +15 funds or a free housing build) appears with a sparkle. Delightful variance against the relentless severity curve, and easy to build atop income.
17. **[SMALL]** **Speedrun achievements.** "Reach Thriving by round 20", "Reach Model Region on Crisis Start", "Never reallocate", "Only services before round 10". They live in the achievements panel and give experienced players target runs.
18. **[SMALL]** **Rewind token.** One "take back" per run that undoes the last round advance, with a used-marker in the summary. Forgives misclicks and makes the token a decision.
19. **[SMALL]** **Strain meter heartbeat.** The strain readout gets a soft pulse whose speed rises with strain level and calms as it drops, giving atmosphere without text. It communicates tension at a glance.
20. **[SMALL]** **Municipal-humor ticker.** An optional one-line ticker of local-news headlines ("Council debates bench placement for six hours", "Language cafe expands to second Tuesday"), gently warm, never mocking arrivals, toggled off in Settings. Personality that fits the institutional tone.
21. **[SMALL]** **Star ratings per run.** Give each finished run 1-3 stars on three independent goals (wellbeing, speed to net-positive, efficiency of funds spent), with a run-history strip of the best star combos. Gives gradual mastery targets on top of the existing personal best.
22. **[SMALL]** **Hidden Cards discovery.** Certain unusual capacity combinations at particular rounds (e.g. services and infrastructure both above 100 by round 30) reveal a secret named "Civic Milestone" card in a collection panel. Discovery is the fun, and it stays cosmetic.
23. **[SMALL]** **Budget tie-break decision popups.** When funds cannot cover both a housing and a services purchase in the same round, offer a two-button "Council vote" with a short flavor line and a tiny modifier for the chosen path. Adds clever choice moments to routine rounds.
24. **[SMALL]** **Season shifts.** Rounds cycle through four seasons that tint the region visual and modestly shift income/arrivals (winter housing pressure, harvest income), letting players time big builds. Adds rhythm and a reason to look ahead.
25. **[SMALL]** **Cosmetic region skins.** Unlock building palettes (Seaside, Alpine, Desert, Neon Future) through achievements, selectable in Settings. Cosmetic meta-progression tied to played goals.
26. **[BIG]** **Emergency Response minigame.** During a surge round, a 3-step quick decision panel (open temporary shelter, request mutual aid, ration services) with each option a distinct cost and effect on strain. It replaces "just advance" with a burst of tense, meaningful choices at the moments that matter.
27. **[BIG]** **Long-game "Legacy Map".** The region visual becomes a persistent map that grows across runs: districts you unlocked or perfected appear on a shared meta-map, and the map is what carries into the next run's starting bonuses. Stronger identity than a numeric unlock tree.
28. **[BIG]** **Cooperative "mentor" ghost.** After reaching Thriving, load your own past run as a ghost mentor whose per-round build order shows faintly in the UI; matching or beating it gives bonus Legacy Points. Turns your history into a competitor, using the existing save-state and subscore log.
29. **[SMALL]** **Confetti on band change.** Crossing into a higher wellbeing band triggers a short confetti/ripple over the gauge, and a small "band up" chime is left optional/silent per the audio limits. Small dose of celebration for the key progress states.
30. **[SMALL]** **Turn-time "fast forward".** A "Play 5 rounds" button that auto-advances with the current allocation and stops early if strain rises a level, so veterans can breeze through calm stretches and only engage when tension appears. Improves pacing dramatically for the 100-round timeline.

**Notes:**

Overlaps: Loop 1/2/4/10 and Drift 1/4/9/27 are the same shape (draft traits, meta-unlock tree, prestige) and could share a "run modifiers + unlock tree" module across Loop, Drift, Thaw and Herd; Loop 3 and Drift 2/26 (telegraphed shocks) likewise share an event-deck engine, and Loop 7 / Drift 12 (deterministic daily/weekly seeds) can reuse Loop's existing weekly featured-category logic. Loop 9 and Drift 5 (idle autopilot) are the same idea for two games, and "Rewind token", "Near-miss", and cosmetic unlocks recur so build the shared helper once in `shared/` if desired.

---

# PART 2 — Round 3 for every game

## A. SOL

1. **[BIG]** Solar events as a roguelike layer: each prestige run rolls a "System Anomaly" (solar flare halves Mercury-side output, asteroid bloom doubles Belt yield but cracks ecology, Venus dust storm blocks trade) that lasts a few dozen ticks. Players pick a counter from a small hand of 2-3 one-shot "contingency cards" drawn from the Prestige Tree, so no two runs pace alike and Governor personalities suddenly matter for different reasons.
2. **[SMALL]** Show the next anomaly's forecast a few ticks ahead in a slim toolbar strip ("Flare in 12 ticks") so the player can pre-position. It reads as tension, not a timer gate, since it only warns about a modifier and never blocks progress.
3. **[BIG]** Prestige "Mutators": before each New Game+ run the player picks 0-3 opt-in rule twists (Thin Atmosphere: ecology decays 40% faster; One-Way Trade: routes only run in one direction; Blind Governor: Governors can't see ecology) that each raise the run's prestige-point payout. This turns the existing challenge toggle into a dial with a reason to keep turning it up.
4. **[SMALL]** Give each mutator a tiny glyph shown beside the prestige badge in the title, so screenshots of the Stats & Share card advertise what the run was played under.
5. **[BIG]** A "Mission Board" of rotating optional objectives per planet, such as "Terraform Mars using zero Sky Cities" or "Reach 60% terraform on Venus while ecology never drops under 50%". Completing one grants a permanent, cosmetic-plus-small-perk "Charter" stamp that lives in the Overview cards, so mastery has a target between milestones.
6. **[SMALL]** Add a "reroll mission" button that costs a small amount of a currently-abundant resource, so a bad draw is a tiny decision rather than a wall.
7. **[BIG]** Governor "Doctrines" as a research-unlocked layer above personalities: chain rules like "if ecology < 30% then pause purchases and ship Water from the richest planet". Players script a tiny if/then list per planet (max 3 rules early, more via the Prestige Tree), and the Governor Report shows which rule fired. This is automation-tinkering for veterans and pairs directly with the trade-route automation layer.
8. **[SMALL]** Add a dry-run button on the Doctrine editor that simulates 30 ticks headless and prints "would have fired 4 times", so testing a rule costs nothing.
9. **[BIG]** A meta "Observatory" shared across prestiges that slowly reveals hidden data about the system: undiscovered "Lagrange Points" (bonus building slots) and rogue comets (one-shot windfalls). Each prestige yields "Survey Data" spent on unmasking one more anomaly on the star chart, so exploration of the map itself is a long-term collection game.
10. **[SMALL]** When a comet windfall appears, show it as a tappable streak on the Overview that fades if ignored for a while, rewarding attention in a light Cookie-Clicker way without any idle gate.
11. **[BIG]** A "Scarcity Run" mode: a fixed-seed daily challenge system where the resource mix, ecology decay and starting planet loadout are seeded from the calendar date, everyone plays the same puzzle, and a completion time posts to the (TODO) leaderboard. Fits the speedrun crowd and gives a reason to come back tomorrow.
12. **[SMALL]** Show "Today's seed" as a short pronounceable word ("amber-orbit-7") on the Stats card so friends can compare notes verbally.
13. **[BIG]** Late-game "Megaprojects": each of 3-4 huge buildings (Orbital Mirror, Ring Habitat, Dyson Sail, Deep Core Tap) demands resources from many planets at once and gives a game-warping perk (e.g. all Sky Cities count double). Picking which to build first is a real branch, and completing all four earns a secret ending variant of the epilogue.
14. **[SMALL]** Give each Megaproject a construction progress ring on the Overview, filled by whichever planets are contributing that tick, so contribution is visible at a glance.
15. **[BIG]** "Rival Colonies" as a soft, non-hostile pressure: three named AI corporations claim Lagrange Points and out-produce the player's exports on shared markets, pushing trade prices down unless the player specialises. Play stays no-timer and recoverable, but the trade layer gains a decision (contest, ignore, or partner) instead of pure exchange.
16. **[SMALL]** Give the rivals one-line ticker gossip in the log ("Helios Combine reports record Belt yields"), for personality with zero mechanical cost.
17. **[BIG]** A "Time Capsule" mechanic for veterans: at any moment the player can freeze the current state as a named capsule (max 3), replay from it in a sandbox branch, and compare outcomes. A "what if I'd gone Governor-first" lab for optimisers, built on the existing save-state machinery, with the branch never counting for achievements.
18. **[SMALL]** Add a one-click "diff vs capsule" line showing resources/terraform gap between now and the capsule after N ticks.
19. **[BIG]** A hidden "Codex" of secrets: seven cryptic clues in flavour text (each planet's description has a trailing odd sentence) that, when acted on (visit Pluto at exactly 0% ecology, build 13 of one thing, terraform Venus last), unlock a silly secret building or a fake achievement. Discovery play for the kind of player who reads everything.
20. **[SMALL]** Give the Codex a "clues found: 3/7" line hidden until the first is discovered, so the mystery itself is a reveal.
21. **[BIG]** Prestige "Eras" replace a flat level counter with named epochs (Pioneer, Steward, Architect, Custodian) that visibly re-theme the shell: palette shift, new title tagline, and a permanent ambient soundless starfield tweak. Gives long-running players a sense of a growing personal story across runs, not just a bigger number.
22. **[SMALL]** A cheeky "Governor mood" one-liner in the report ("Mars Governor: 'Please stop clicking me.'") that changes with personality and how much the player micromanages.
23. **[BIG]** A "Blueprint Swap" import/export: players serialise their whole build plan plus Doctrine list plus mutator picks into a short shareable code, and others can load it as a ghost overlay in the Build Plan checklist. It turns optimisation into a community sport with no backend.
24. **[SMALL]** Add a "copy as text spreadsheet" button to the Build Plan for people who like pasting it into notes.
25. **[BIG]** A "Chain Reactions" combo system: performing the right sequence across planets within a short window (dump Ice on Venus, then trade Water to Earth, then click Mars) triggers a bonus, discovered by experimentation. A tiny skill layer on top of the automation curve that keeps manual clicking relevant late, with a "combos found" collection page.
26. **[SMALL]** A soft click-streak meter that adds a very small yield bonus for staying in rhythm, with a "reduce motion" fallback that is text-only.
27. **[BIG]** Ecology "Stress Tests" as an optional endgame arena: a one-shot scenario where a cascade of anomalies hits every planet and the player must hold combined ecology above a line using only Governors already set, no clicking. Score by margin held, an opt-in exam for people who've tuned their Doctrines, bridging the Close Call achievements into an actual mode.
28. **[SMALL]** After a stress test, show a per-planet heatmap strip of when each dipped, so the player sees which Governor failed.
29. **[BIG]** A wildcard "Ghost Run" mode: race a recorded replay of your own personal best (or an imported friend's blueprint code) on a split track showing lead/lag in terraform percent every 25 ticks. Not multiplayer, but a stepping stone for the multiplayer direction and a fresh reason to re-run the same speedrun.
30. **[SMALL]** Speedrun splits panel: lap times per planet unlocked, with a green/red delta against personal best, hidden unless "Show timing" is enabled in Settings.
31. **[SMALL]** Make achievements more visible and stylized. Give the achievements panel real visual presence instead of a plain scroll list: a small "trophy shelf" strip of the most-recently-earned badges pinned near the top toolbar (not only the existing "(N/M)" toggle-button count), each badge rendered with SOL's own gradient-glow treatment, plus a brief particle/glow flourish at the moment of unlock instead of only a toast.

---

## B. Canopy

1. **[BIG]** Session library with a compare view. Every finished session (Session Summary) is stored as a compact record (final values, playstyle badge, difficulty, grid size, the three report-card series) in a "My Forests" list. Pick any two and see them side by side using the existing report-card sparklines, which gives Run A/B snapshots and the legacy bonus (B15) a proper history home.
2. **[SMALL]** Legacy bonus visibility. Show the current legacy multiplier (e.g. "+12% from your last forest") as a chip in the header, with a tooltip naming where it came from and how close it is to the +25% cap. Right now it is a silent number that only shows up in the math.
3. **[BIG]** Forest replay scrubber. Use the capped forest_log plus periodic per-plot snapshots to let the Session Summary replay your forest as a time-lapse: a slider that scrubs the grid through the session, plots greening and clearing in sequence. It turns the hope-angle payoff into something visual you can watch and screenshot.
4. **[SMALL]** Shareable forest image. Extend the PNG-style snapshot idea from the shareable badge snippet (B18) to render the final grid, badge, and three headline numbers into one downloadable image card. It hooks into the existing "Copy badge" area and needs no backend.
5. **[BIG]** Custom-rules sandbox. A "Forest Lab" panel where the player tunes the numbers that already exist as constants (soil degradation per clear, maturity speed, request frequency, season strength) with sliders, then plays a session under those rules. Sandbox sessions are marked as such and kept out of personal bests and percentile stats. It gives the tinkerers a toy and a natural way to build harder or gentler variants of Ranger mode.
6. **[SMALL]** Request-interval slider in Settings (Relaxed / Normal / Frequent) that scales `STAKEHOLDER_EVENT_INTERVAL_TICKS`. Players who find the Pass 3 pacing too busy or too idle can fix it without a difficulty change, and it is saved with the difficulty tag so stats stay honest.
7. **[BIG]** Full keyboard and screen-reader play. Extend B16's shortcuts into a complete grid cursor: arrow keys move a focus ring across plots, Enter/C/R clear or replant, and an aria-live region announces state changes, incoming requests, and season shifts in plain text. A full mouse-free session makes the game genuinely accessible, and the coordinate labels (B2) already give the vocabulary to speak.
8. **[SMALL]** A high-contrast plot-state option in Settings. It adds bold outlines and text glyphs (B / R / M) on every plot so state is readable without relying on the green gradient, sitting beside the text-scale and reduce-motion controls. It complements the already-audited colorblind result with a stronger low-vision mode.
9. **[BIG]** Statistics dashboard tab. A lifetime page aggregating all sessions in localStorage: total plots cleared/replanted, hours played, average standing value by difficulty, badge distribution as a bar, best season, and a per-request-type accept/decline rate. It uses the same panel idiom as the achievements panel and finally answers "what kind of forester am I overall".
10. **[SMALL]** Soil-quality heat overlay toggle. A button that recolors every plot border by remaining soil quality (with numeric badges for accessibility), so multi-clear damage across the 9x8 grid is legible in one glance. It solves the "do players notice degradation" open question from Pass 1 in a way that stays optional.
11. **[BIG]** Two-tier "Scenario seeds" of pre-made starting forests (Clear-cut Valley: 60% bare, Fragmented Farmland: checkerboard, Old-Growth Remnant: one intact core). Pick one at session start; each has its own personal-best slot on the report card. It reuses the plot/dict save format and gives the grid a reason to be revisited, unlike Grid's scenario select being unique to that game.
12. **[SMALL]** Season-aware forecast strip. A tiny line under the season indicator showing the next two seasons' multipliers ("Summer 1.05x in 12 ticks, then Autumn 0.95x"). It makes B17 plannable and costs nothing in state.
13. **[BIG]** Pause-and-plan mode. A toggleable "Survey" state that freezes the tick and lets the player queue actions (clear this, replant that, decline the next request) and then commit them all when unpaused, with a projected value delta shown first. It supports slower, more deliberate play and pairs with the counterfactual math already in the Session Summary.
14. **[SMALL]** Sortable request history. A table in the forest history panel listing every stakeholder request with plot, kind, your choice, and the value delta afterwards, sortable and filterable. It extends B3's log with the "did I choose well" audit view.
15. **[BIG]** Multi-slot saves inside the shared save widget. Let a browser keep up to three named forests (e.g. "Ranger practice", "Preservationist run") and switch between them from a small menu, each with its own difficulty and grid size. The shared save-widget already handles codes, so this is a local slot manager layered on top, cleaner than resetting the session to try a new setup.
16. **[SMALL]** Plot tooltip cards on hover/focus showing coordinates, state, age, soil %, biodiversity rate, specialization, and clear count in one compact card. It replaces having to click through the action panel to inspect a single plot and reuses the B26 hover tracking.
17. **[BIG]** A visual refresh art direction pass: layered canopy sprites (per-state tree art with sway, subtle depth shadow, seasonal foliage colors) replacing flat tinted tiles, keeping icons for state encoding. It reads like a living forest instead of a spreadsheet and hooks into the existing seasonal palette (B30) and wildlife sprites.
18. **[SMALL]** Ambient soundscape toggle (off by default): soft wind, birds keyed to biodiversity level, rain in spring. It is a single mute switch in Settings using generated Web Audio tones, so no asset files are needed. Wildlife log entries could play their own quiet call once.
19. **[BIG]** Long-term "Forest Rank" track. Lifetime seeds/XP from sessions (standing value, seasons survived, badge variety) fill a rank ladder (Sapling Warden through Grove Keeper) that unlocks cosmetic frames for the badge card and unlockable palette themes. It gives sessions-long progress without adding gameplay advantages and slots under the achievements panel.
20. **[SMALL]** Achievement progress bars. Each locked achievement in the panel shows a numeric progress line ("3 of 5 plots specialised") when its condition is countable, so goals feel reachable. It is a display-only change on the framework.
21. **[BIG]** Snapshot-vs-now timeline chart. A large, interactive version of the three report-card sparklines available at any time (not just at summary), with hover values, season bands, and event markers for each clear, request, grant, and specialist choice. It joins forest_log data with report history and lets players study cause and effect mid-run.
22. **[SMALL]** Tick-speed-independent "catch up" on tab return: if the tab was hidden for a while, show a summary chip ("While away: +214 value, 1 request expired") instead of silently jumping numbers. It makes the idle loop friendlier and prevents surprise state.
23. **[BIG]** Cross-game legacy: a "Climate Steward" shared profile counter that reads optional data from other climate games' saves (e.g. Canopy standing value, Tide restored coastline) to display one hub-level portrait. It needs coordination with Y/Z, so it might live in the hub shell rather than Canopy, but Canopy would expose its summary fields.
24. **[SMALL]** Plot notes: a right-click or long-press adds a short text label to any plot (max 20 chars, shown as a corner dot). It supports players who want their own reminders on the big grid without introducing adoption's full mini-history.
25. **[BIG]** Request negotiation depth. Instead of accept/decline only, each clear-request offers a third counter-offer ("clear half the plot area" or "give me two nearby bare plots instead") whose outcomes are deterministic and previewed with numbers. It adds nuance to the ethical-weighing pillar while staying inside the existing stakeholder-relations math.
26. **[SMALL]** Numbers-format and units setting: compact numbers (1.2k), thousands separators, or full precision. It is a Settings dropdown that helps late-game values stay readable on the mobile dock.
27. **[BIG]** Adaptive "Coach" hints that read your session and quietly flag patterns in the summary ("You cleared the same plot 3 times in one season; soil there is now 55%"), shown as dismissible notes in the report card rather than pop-ups. They are opt-in via Settings and never block play, and they replace tutorial text for returning players.
28. **[SMALL]** Larger click targets and a pointer-friendly action panel on mobile: a plot long-press opens a bottom sheet with big Clear/Replant/Adopt buttons instead of a small side panel. It addresses phone play without touching desktop layout.
29. **[BIG]** Custom grid shapes: an editor to paint which of the 9x8 cells exist (island, ring, plus-sign, river-split), saved as named layouts with their own personal-best slot. It multiplies replay variety from one already-built renderer since plots are already indexed by position.
30. **[SMALL]** Performance guard: auto-throttle wildlife sprite animation and value-pop effects when the tick loop lags or the tab is on a low-end device, with a "Performance mode" indicator in Settings. It keeps the Large grid smooth without the player having to find the reduced-motion switch.
31. **[SMALL]** Make achievements more visible and stylized. Give Canopy's achievement cards a forest-themed visual upgrade: a small leaf/wildlife glyph per earned badge (reusing the existing wildlife-sprite art) instead of plain text rows, laid out like a "grove wall" that visually echoes the plot grid rather than a flat scrolling list.

---

## C. Grid

1. **[BIG]** Run history library. Each finished career run stores its funds/clean-share/demand series, scenario, grade, and points earned, listed in the Career panel and viewable as a stacked trend chart to compare runs. Since the career already banks points, this gives the mastery layer a memory beyond one number.
2. **[SMALL]** Career perk preview. Locked perks show exactly how many points away they are and what the next level would do numerically ("+8% seed capital, ~+24 funds"). It turns the four-perk shop into something planned instead of guessed.
3. **[BIG]** Post-run "what if" analyzer. After Finish Run, replay the same demand and weather rolls (seeded from the run's stored RNG) with three canned alternative strategies (all-renewable-early, no-retire, storage-first) and show final grade and funds next to yours. It extends C25's projection into a real counterfactual and makes replays less abstract.
4. **[SMALL]** Supply/demand mix legend upgrade: hovering a bar segment in the plant-mix chart highlights that plant's row and shows its share of capacity, revenue, and emissions. It links two views that already exist without new state.
5. **[BIG]** Full keyboard and screen-reader operation. Tab order through plant rows, arrow-key adjust for build/retire counts, an aria-live region announcing each round's outcome (demand met, disruptions, weather delta), and a spoken-friendly summary of the gauges. It makes a numbers-heavy game playable without a mouse and follows the ConfirmDialog pattern.
6. **[SMALL]** Number-format and unit toggle: MW vs "units", compact vs full figures, and an option to show funds per-round deltas as coloured arrows plus text. It uses the Settings panel and avoids hue-only encoding.
7. **[BIG]** Statistics dashboard tab. A lifetime page aggregating all runs: average grade per scenario, rounds survived, most-built plant, disruptions weathered by cause, and a heatmap of clean share by round number. It complements the Career panel and reads from the same grid_career_v1 store.
8. **[SMALL]** Round recap toast that collates every automatic change (scheduled maintenance, demand-response effect, arbitrage income, weather delta) into one expandable line instead of separate logs. It reduces scanning when automation from the round-3/4 systems stacks up.
9. **[BIG]** Custom scenario builder. Set starting funds, plant mix, demand level, growth rate, and weather variability with sliders, save as a named scenario, and share it as a copyable code the shared save-widget can import. It extends C13's scenario select into user-authored content while staying on the same GridState constructor.
10. **[SMALL]** Difficulty presets bundle: Relaxed / Standard / Operator that toggle the existing options (weather variability, steeper demand growth, aging risk) with one dropdown at run start. It gives new players a sane setup and veterans a one-click hard mode, with the chosen preset shown in the header.
11. **[BIG]** Grid visualization redesign. Replace the row-only plant list with a compact single-line schematic (generators feeding a bus into a demand block, with flow thickness by output and arbitrage storage shown as a tank), animating each round change. It gives the numbers a physical picture and doubles as the shareable result image.
12. **[SMALL]** Trend-graph overlays selector: checkboxes to add or remove emissions, funds, demand, and clean share lines, with the C12 best-round marker staying visible. It handles the case where four series get noisy on one axis.
13. **[BIG]** Multi-slot saves. Up to three named runs in localStorage (e.g. "Coal legacy practice", "Emergency retry") with a slot switcher, each carrying its own scenario and career-independent state. It makes trying different setups painless and reuses the save widget's serialisation.
14. **[SMALL]** Plant fleet overview table: sortable list of every plant type with count, age tiers (the three wear icons), breakdown risk %, next scheduled maintenance, and revenue per round. It is a bird's-eye version of what currently lives in each row.
15. **[BIG]** Round-by-round timeline scrubber. After a run, slide through past rounds and watch the fleet, demand, weather, and disruption log update to that round's state. It pairs with the operator report to explain why a grade happened and can be built from the stored per-round history.
16. **[SMALL]** Career reset with export: a "Reset career" button behind ConfirmDialog that first offers to copy the career JSON, and an import field to restore it. It guards against losing meta-progress to a cleared browser.
17. **[BIG]** Long-term operator ranks. Lifetime grid-hours and grades feed named ranks (Junior Dispatcher to Chief Engineer) that unlock cosmetic panel themes and a signature header. Unlike perks, ranks give no gameplay edge; they sit next to the career points as a status track.
18. **[SMALL]** Achievement progress readouts: countable achievements show "3 of 5 rounds" progress in the panel, and locked ones show the next milestone. It is a display change to the framework and helps players chase them.
19. **[BIG]** Accessible data-view mode: every chart and gauge gets a "table view" toggle showing its underlying numbers in a plain table and a short text description of the trend. It supports screen-reader users, colour-blind and low-vision players, and gives the curious raw data to check their arithmetic against.
20. **[SMALL]** Sticky key-stats header on scroll: funds, demand, capacity, and round number stay visible as a slim bar when the plant list is scrolled. It fixes the mobile problem where the action rows hide the numbers you are optimizing.
21. **[BIG]** Coach mode for returning players. An opt-in advisor panel that reads the current state and offers one plain-language observation per round ("Coal fleet 70% worn; breakdown odds 22%"), collapsible, never blocking. It reuses existing risk numbers and helps people who skip the tutorial.
22. **[SMALL]** Confirm-dialog memory: a "don't ask again for retiring plants under 20% wear" checkbox in Settings that skips low-stakes confirmations while keeping the last-unit warning. It reduces friction for players who retire often.
23. **[BIG]** Visual overhaul of round transitions: an animated round-advance sequence (sun arc for solar, wind streaks for wind, demand curve drawing itself) lasting under a second, skippable in Settings and off under reduced motion. It gives each round a rhythm and makes the weather roll legible before the log line.
24. **[SMALL]** Print/export the operator report as a clean single-page view (print stylesheet plus copyable text) with scenario, grade, resilience, and career points earned. It rounds out the shareable end-of-run moment without needing a backend.
25. **[BIG]** Cross-game "Climate Portfolio" hook: Grid exposes its best clean-share, grade, and resilience as a small structured summary the hub can read and show alongside Canopy and Tide results. It needs coordination with the hub and Z1 aggregate endpoint but makes each game's records part of a larger picture.
26. **[SMALL]** Load-time guard and integrity chip: if a save is missing fields (the round-3 save bug class), show a small "repaired N fields" note in the changelog panel rather than silently defaulting. It builds trust in persistence and helps debug.
27. **[BIG]** Balance tuning panel (sandbox): sliders for cost decay, breakdown chance, demand growth, and revenue per unit, with runs tagged Sandbox and excluded from career points and percentile stats. It lets curious players stress-test the learning-curve model and is a natural spot to compare against real cost data.
28. **[SMALL]** Colour theme picker for the trend graph and plant-mix chart (default, high-contrast, grayscale with patterns). It adds a small pattern-fill option to bars, which strengthens the colour-independent cues from the C8 icons.
29. **[BIG]** Instant-replay share code. Compress a run's key decisions and seeds into a short string that anyone can paste to watch the same run play back in a read-only viewer, with the grade result at the end. It is the single-player groundwork multiplayer would later reuse, and it needs the seeded RNG history already stored per run.
30. **[SMALL]** Performance and mobile polish: batch DOM updates per round, lazy-render the log panels, and show a light "loading round" state in slow Pyodide moments. It keeps late-run rounds with many plants and logs responsive on phones.
31. **[SMALL]** Make achievements more visible and stylized. Restyle Grid's achievement cards around its own skyline-HUD visual language: earned badges render as small lit-building icons against the city-skyline palette, with a brief "power up" flash on unlock, instead of the current plain card list.

---

**Notes.** Overlaps with the gamified list are avoided, but several ideas here touch shared hub concerns: multi-slot saves, keyboard/screen-reader play, statistics dashboards, custom-scenario/sandbox modes, and replay/share codes (Canopy 1/15/29, Grid 1/13/29) would each be built once as shared components. Canopy 23 and Grid 25 depend on Y/Z aggregate endpoints and the multiplayer pass, so they are best treated as hub-level items. Grid 3 and 15 resemble the deferred C21 "grid twin" comparison and share its scoping question.

---

## D. Tide

1. **[BIG]** **Harbor Ledger: full season-by-season history.** A new panel lists every season of the current session as a sortable table (funds, acidity, fish yield, damage, rows dry, population, tier, what you invested in) with a small chart per column. It reads from the same per-season data the trend graphs and D7 delayed-consequence timeline already use, so players can finally answer "which season did I lose it?" without scrolling the ticker.
2. **[BIG]** **Session library and two-run overlay.** Finished sessions are saved to a local list (scenario, lag mode, storm toggle, final score), and any two can be overlaid on the acidity/fish-yield graphs as solid vs. dashed lines. It extends the D18 comparison-baseline checkpoint from "within one run" to "between runs," and is the natural home for run comparison over time.
3. **[BIG]** **Shareable session code with ghost import.** A completed session exports a compact code (scenario, per-season investment choices, outcome) that a friend can paste into a "Load Ghost" box to view as a read-only faint overlay or step-through against their own run. It reuses the save/checkpoint snapshot format and the hub's export/import-code pattern, and is comparison without needing any backend or multiplayer.
4. **[BIG]** **Season scrubber replay.** A timeline slider under the coastline lets the player drag back to any earlier season of this session and see the grid, meters, tier badges and heritage tiles exactly as they stood then, without altering the live run. It builds on the D27 checkpoint snapshots plus the chronicle, and turns the game into something you can study after a bad storm.
5. **[BIG]** **Tide Workshop: custom ruleset sliders.** An opt-in panel with sliders for starting funds, lag length, sea-level rate, storm surge size and fish sensitivity, showing a live "difficulty rating" and applying a score label ("custom rules") instead of blocking play. Hard-lag (D9-era toggle) becomes just one preset, and D19's three scenarios become quick-fill buttons.
6. **[BIG]** **Season planner (draft budget projection).** Before pressing Advance, a "Plan" tab lets the player stage the next 3 to 5 seasons of allocations and see the projected acidity, fish yield, and rows-at-risk curves. It is deterministic because lag is known, so it is a spreadsheet-style what-if for min-maxers, and it never writes to game state until "Commit season 1."
7. **[BIG]** **Full accessibility pass: screen reader and keyboard grid.** Announce each season's result through a live region, describe the coastline as text ("Row 5 dry, seawall tier 2, lighthouse protected"), and make investment buttons, tiles and the D7/D10 graphs reachable and operable by keyboard with visible focus. Extends the existing reduced-motion and text-scale Settings into a real non-visual path through the whole game.
8. **[BIG]** **Named coastlines as scenarios.** Beyond D19's conservative/moderate/severe trajectories, pick a real-flavored coast (low delta town, rocky headland, atoll, dredged port) each with its own elevation profile, heritage sites, economy weights (fishing/tourism/industry), and storm frequency. Sea-level scenario and coastline combine into a grid of starting setups, giving replay value from tuning rather than new mechanics.
9. **[BIG]** **Harbor Almanac: lifetime records.** A persistent tab tracking lifetime seasons survived, rows saved, heritage sites protected, storms weathered, and the personal best per scenario plus lag mode, with the tier combination that produced it. It is the long-term view the per-session summary lacks, and it feeds the hub achievements dashboard without adding backend.
10. **[BIG]** **Bronze/Silver/Gold achievement ranks.** Each existing achievement gains three tiers (e.g. survive a storm; survive 3; survive 3 with no row lost), giving old players a reason to revisit earned goals. The round-3 mechanics (heritage, retreat, diversification, monitoring, population) currently have no achievements, so this also gives those systems a tiered mastery ladder.
11. **[BIG]** **Autosave history and recovery.** Keep the last three per-season autosaves plus the manual checkpoint, and if a load fails validation show a "Restore previous save" panel with each slot's season and funds instead of silently resetting. Uses the existing `get_state()`/`load_state()` validation, and makes the growing list of round-3 state fields (heritage, storms, retreat, population) safer to ship.
12. **[BIG]** **Customizable dashboard layout.** Players choose which panels (meters, graphs, tide indicator, ticker, chronicle) are pinned, reorder them, and switch between "Compact", "Analyst" (all graphs) and "Postcard" (coastline only) presets. As the round-3 features pile up, this addresses screen clutter without removing anything, and it's remembered in localStorage.
13. **[BIG]** **Living harbor scene.** The coastline backdrop gets a slow sky cycle tied to the season of the year (pale spring, hazy summer, grey autumn, low winter sun), water tint that shifts toward greener/murkier with acidity (with a hatch pattern redundancy for colorblind audit), and a stormy sky during storm seasons. Purely presentation, layered behind the grid renderer with a Settings toggle.
14. **[SMALL]** **Keyboard shortcuts with cheat-sheet.** Press A to advance a season, 1/2/3 to invest, R to open the report, ? to show the overlay of all keys. There are no key handlers now, so this is a quick win for repeat players and pairs with the accessibility pass.
15. **[SMALL]** **Fast-forward with auto-stop.** An "Advance x5" button repeats quiet seasons and halts automatically at a storm forecast, a fish-yield warning, a heritage site at risk, or a monitoring report. Saves clicks in the long, calm stretches of a 20-season run.
16. **[SMALL]** **High-contrast and dyslexia-friendly toggles.** Two extra Settings switches: a high-contrast palette for grid tiles and meter bars, and an alternate readable font. Extends the existing text-scale/reduced-motion panel.
17. **[SMALL]** **Ticker filter chips and search.** Chips above the delayed-effect ticker filter to Fish / Sea / Economy / Storm / Chronicle, and a text box finds a past message. The ticker grows long across 20+ seasons, so this makes it a usable log.
18. **[SMALL]** **Copy chronicle and summary as text.** One button copies the settlement name, chronicle and end-of-session summary to the clipboard as plain text for pasting into a journal or chat. Cheap sharing without images or accounts.
19. **[SMALL]** **Seasons-to-afford on each tier.** Beside each adaptation tier and diversification level, show "affordable in 3 seasons at current income" with a pin to keep one target highlighted. Similar in spirit to Aftermath's runs-until-affordable estimate, reusing Tide's income figure.
20. **[SMALL]** **Net-funds preview chip.** When hovering or selecting an investment, show a chip with funds after purchase and after this season's upkeep (heritage, tier upkeep). Prevents the "I can't afford the storm cost" surprise, and extends D22's live preview idea to all spending.
21. **[SMALL]** **Graph crosshair readout.** Hovering or tapping a trend graph shows a vertical line and a tooltip with the exact acidity, yield, damage and funds for that season. Touch-friendly and needs no new data.
22. **[SMALL]** **Graph range selector.** Toggle the trend graphs between "last 10", "last 20" and "all seasons" so long or extended sessions stay legible. Applies to the D7 timeline and D10 average-line graphs.
23. **[SMALL]** **Series markers and dash styles toggle.** Optional distinct line dashes and point shapes per series (circle/square/triangle) as a redundant encoding beyond color. Continues the D11/D28 colorblind-safety pattern into the graphs.
24. **[SMALL]** **Live tab title and favicon status.** The browser tab reads "Tide S12 - fish warning" and switches its favicon when a storm is forecast or a warning fires. Useful when the player is in another tab during a long session.
25. **[SMALL]** **Personal-best line in session summary.** The end summary adds "Best for this scenario: 14 seasons dry. You: 11" pulled from the Almanac data. A one-line context for every result.
26. **[SMALL]** **Mobile layout polish.** Sticky Advance Season bar at the bottom, 44px minimum tap targets on tiles and invest buttons, and swipe between Coast / Meters / Log panels. Aligns with the hub's mobile-dock work and the crowded new panels.
27. **[SMALL]** **Remembered collapsed panels.** Each `<details>` panel (D7 timeline, chronicle, heritage, diversification) remembers open/closed across reloads. Cuts repeat-session friction.
28. **[SMALL]** **Delta breakdown popover.** Clicking any meter change (acidity +4) opens a small popup listing the contributors ("+6 output, -2 reduction, +0 aquaculture"). Explains the economy's moving parts using the terms the game already tracks.
29. **[SMALL]** **Plain-language label mode.** A Settings switch renaming jargon (dampening, lag, OUTPUT_MIX-type labels) to everyday words in buttons and tooltips. Helps new players without changing any mechanic.
30. **[SMALL]** **Pause animations when tab hidden.** Stop the wave cue, tide ripple and any looping effects when the page is hidden or the device reports low power, and resume on return. Invisible but improves battery and performance on phones.
31. **[SMALL]** Make achievements more visible and stylized. Give Tide's achievement cards an ocean-themed visual upgrade: a small coral/wave glyph per earned badge and a coral-reef-accent border reusing the existing coastline art, with a brief ripple flourish on unlock, instead of the current plain card rows.

---

## E. Aftermath

1. **[BIG]** **Lifetime statistics dashboard.** A stats tab aggregates all saved runs: damage taken per event category, average mitigation per event type, best and worst event matchups, KP earned over time, and average score by skill-strength band. Built from the existing run history and event logs, it turns Review Past Runs from a list into an analysis tool.
2. **[BIG]** **Pannable skill-tree map with path highlighting.** The tree becomes a zoomable, pannable graph where selecting any locked node lights up the cheapest route and total KP needed, and categories (weather/social/economic) can be filtered. It builds directly on the pin feature and the E1/E3 branches, which have outgrown a list.
3. **[BIG]** **Purchase route planner.** From the pinned skills, propose an ordered buy list with running KP total and an estimated "runs to complete" based on average earn rate. It extends the runs-until-affordable estimate from one skill to a whole plan, and updates as you play.
4. **[BIG]** **Shareable run code.** After any run, export a code containing the event schedule, severity draws and result; a friend pastes it to play the identical schedule and compare scores. Uses the export/import progress-code plumbing, and needs no multiplayer or server.
5. **[BIG]** **Full accessibility pass.** Screen-reader announcements of each event resolution ("Flood hit, 42 damage, 18 prevented"), keyboard operation of allocation buttons and the tree, focus management when panels open, and a plain-text schedule strip. Extends the existing text-scale and reduced-motion settings into non-visual play.
6. **[BIG]** **Custom run sliders with score multiplier.** Pick event count, starting resources, damage scale and growth income in an opt-in panel; the game shows a difficulty multiplier applied to KP and tags the run as "custom" in history. Generalizes extended-run mode and the E7 lifetime scaling into an open tuning surface.
7. **[BIG]** **Settlement Chronicle book.** A persistent, scrollable timeline for the named settlement across all runs: first flood survived, worst disaster, skills adopted, generational-memory callbacks (E5), records broken. Extends E25's settlement identity from a name into a living history, viewable and copyable.
8. **[BIG]** **Location-driven settlement art.** Once E17a/E17b scenarios ship, the settlement illustration changes with the chosen location (coastal harbor, inland farm town, dense city), with a per-event weather overlay when resolving. Makes scenario choice visible and gives replay a visual payoff beyond numbers.
9. **[BIG]** **Difficulty-adjusted score.** A secondary "adjusted score" normalizes each run by how severe its drawn schedule was (using severity draws and lifetime widening), so run 3 and run 30 compare fairly. History and the toughest-run badge show both raw and adjusted numbers.
10. **[BIG]** **Multiple player profiles.** Up to three named profiles per browser, each with its own skill tree, history, pins and achievements, switched from a header menu. Useful for shared family or classroom devices and for testers, and separates progress without a backend account.
11. **[BIG]** **Skill ranks through use.** Each skill has three ranks; rank-ups come from proven use (Early Warning ranks up after N events where the preview was accurate, category skills after preventing damage of that type). Gives owned skills a long-term arc and reward for veterans past the point of buying everything.
12. **[BIG]** **Disaster Codex.** A collection page for each event type showing times faced, average damage, best mitigation achieved, and short real-world-grounded notes that unlock as you face it. Ties the info page content into play as a discoverable reference and a long-term completion target.
13. **[BIG]** **Schedule builder.** Compose your own event order from the event library (up to a set length), save it by name, and run it; results are tagged "custom schedule" and can be exported with the run code. Complements built-in scenario packs by letting players stress-test their own tree.
14. **[SMALL]** **Keyboard shortcuts.** Number keys for allocation, Enter to resolve, T for tree, H for history, ? for the key list. There are no shortcuts today, so repeat runs get much faster.
15. **[SMALL]** **Allocation step buttons.** Add x1 / x5 / Max next to resilience and growth so a run of ten clicks is one. Respects existing costs and the resource cap.
16. **[SMALL]** **High-contrast and readable-font toggles.** Two extra Settings switches alongside text scale and reduced motion.
17. **[SMALL]** **Schedule strip hover details.** Hovering an upcoming event on the strip shows its type, the expected-damage range at your current build, and category mitigation bonus. Builds on E14's confidence range.
18. **[SMALL]** **Damage waterfall on resolve.** The resolution panel shows base damage, then severity change, then each mitigation source subtracted, ending in final damage as a stacked bar. Explains exactly what each skill did.
19. **[SMALL]** **Tree search and filters.** Search box plus chips for Affordable / Pinned / Owned / Category. Lightens the bigger post-E1 tree.
20. **[SMALL]** **Side-by-side run compare.** Tick two runs in Review Past Runs to see events, damage and score in two columns with differences highlighted. Extends toughest-run-yet comparison to any pair.
21. **[SMALL]** **History sort, filter, and archive.** Sort by score, date or mode, filter to extended or custom runs, and archive old runs from the list without deleting their KP credit. Keeps long histories manageable.
22. **[SMALL]** **Run notes.** A short text field per run ("tried all-in on flood skills") saved to history and shown in the list. Personal experiment tracking.
23. **[SMALL]** **KP earn breakdown.** The end-of-run panel itemizes how KP was earned (base score, streaks, achievements), so the live-preview number is explained line by line.
24. **[SMALL]** **Copy run summary.** One button copies the settlement name, run number, score and event list as text.
25. **[SMALL]** **Allocation presets.** Save named allocation plans ("Flood plan: 3 resilience, 1 growth") and apply them in one click before an event. Speeds repeat play without changing decisions.
26. **[SMALL]** **Mobile sticky Resolve bar.** Keep Resolve and resources in a bottom bar on phones and enlarge tap targets.
27. **[SMALL]** **Live tab title status.** "Aftermath - Run 7, event 3 of 6 (Flood next)" in the tab title.
28. **[SMALL]** **Unspent-resources confirm.** If you hit Resolve with a large unspent balance, an opt-out prompt asks "Keep 80 resources unspent?". A guard against accidental waste, with a Settings switch to disable it.
29. **[SMALL]** **Skill tooltip: helps against.** Each skill's tooltip lists which upcoming events it would soften and by roughly how much for the current schedule. Turns tree reading into planning.
30. **[SMALL]** **Save health indicator.** A small "Saved 12s ago / storage full / unsaved changes" badge with a one-click export prompt if local storage fails. Makes the persistence layer visible for a game where the tree is everything.
31. **[SMALL]** Make achievements more visible and stylized. Tie Aftermath's achievement cards visually to the skill tree: earned badges show as small lit nodes on a mini tree-shaped strip near the toggle button rather than a plain list, so mastery reads at a glance the same way the real skill tree does.

---

**Notes:** Tide #2/#3 and Aftermath #4/#20 (session/run codes, comparison overlays) share one "export a result as a code and import it as a ghost" helper that could live in `shared/`; Tide #10 (tiered achievements) and Aftermath #11 (skill ranks) are both "long-term mastery ladders" and could share UI. Tide #8 and Aftermath #8/#13 depend on or extend the open scenario-pack TODO items (D19-style scenarios, E17a/b), and both accessibility passes (#7 / #5) should be built once as a shared keyboard/live-region pattern.

---

## F. Herd

1. **[BIG]** **Difficulty tuning panel (sliders).** A "Ranch Rules" section in the Settings panel lets the player set starting funds, weather/season swing strength, pressure-penalty severity and growth-cost slope, with a one-line summary ("Custom rules, scores marked unranked"). Scores from default rules stay eligible for the Z1 community stats; custom runs are tagged so the percentile comparison stays fair.
2. **[BIG]** **Multi-run history and trends view.** A "Ranch Ledger" tab stores a compact summary of every finished session (final funds, methane, score vs baseline, levers used, poultry yes/no) and charts the trend across runs, with a filter by mode (cap / seasons / plain). Uses the same summary already fed to the report card and the localStorage pattern from Thaw's personal best.
3. **[BIG]** **Round-by-round replay and scrubber.** After the game (or mid-game), a timeline slider replays the farm state per round: pasture cow count, gauge needle, haze and funds, with markers where a lever was bought or a policy advisor choice was made. Lets the player see exactly which decision bent the curve, using the existing methane_history and counterfactual paths.
4. **[BIG]** **Shareable "farm card" image.** A one-click export renders the final report card (gauge, trend sparkline, score vs baseline, levers, achievements count) into a PNG or printable page. Builds on the shared printable-summary component already proposed in round 2 and the report-card panel, so a result can be posted or pasted into coursework.
5. **[BIG]** **Save-code challenge sharing ("Farm Snapshots").** Export a mid-run state as a compact challenge code others can load and play forward from, with the sender's best result attached as the score to beat. Rides the existing shared save-widget/save-code path, so a friend or classmate can try to out-decouple your exact position; a natural precursor to the multiplayer direction.
6. **[BIG]** **Full "explain this number" inspector.** Clicking any number (income, methane, coupling ratio, pressure loss) opens a breakdown tree: base value, each lever's contribution, season multiplier, welfare bonus, supply-chain bonus. Ties together the many systems added in round 3 (breeding, poultry, welfare, supply chain, seasons) so the player can always audit why a value is what it is, reusing the investment-consequence preview math.
7. **[BIG]** **Lever balance "dry-run" planner.** A planning drawer where the player queues up several rounds of purchases on a scratch copy of the farm and sees the projected gauge, funds and methane curve for 5-10 rounds ahead before committing. Extends the F18 before/after preview from one purchase to a whole plan, and pairs with the counterfactual line as a reference.
8. **[BIG]** **Mixed-herd allocation UI.** Once poultry is unlocked, a single allocation slider (beef/dairy vs poultry vs plant-based share of output) with a live stacked bar showing income, methane and welfare per segment. Consolidates the separate poultry panel and pivot into one strategic view and shows portfolio effects (poultry welfare vs dairy upkeep) instead of two disconnected panels.
9. **[BIG]** **Policy advisor deck expansion.** The 8-round advisor gains a pool of distinct offers (carbon-credit contract, feed-price hedge, organic label trial, welfare grant) drawn without repeats and shown in a small "advisor history" list, each with a visible real-world tag. Makes the existing advisor event a recurring decision layer rather than one binary choice, and the choices show in the report card.
10. **[BIG]** **Full keyboard and screen-reader play.** Every lever, Advance Round, panel toggle and dialog reachable by keyboard with visible focus, arrow-key control on the gauge/lever list, and aria-live announcements of round results ("Round 9: methane down 4, funds up 12"). Extends the colorblind audit and settings panel into a genuinely accessible pass and adds a shortcut cheat sheet in How to Play.
11. **[BIG]** **Beginner / Standard / Expert profiles with adaptive hints.** A profile at new game sets how much on-screen guidance appears: Beginner shows a "next best lever" hint chip derived from current state, Expert hides previews and tooltips entirely. Reuses the existing onboarding tooltips and consequence previews as toggled layers rather than new content, so newcomers and veterans get different densities.
12. **[BIG]** **Offline-first play with sync status.** The service worker pre-caches Pyodide and game files so a first load works without network, with a small status pill ("offline, community stats paused") and a queued stats/feedback submit that flushes when reconnected. Makes the community-comparison features degrade gracefully and helps classroom wifi.
13. **[SMALL]** **Cost-per-methane-saved column.** The lever list shows a tiny "funds per methane saved" figure for each lever so feed, caps, capture, breeding and biofilters can be ranked at a glance. Pure display from formulas already used by the previews.
14. **[SMALL]** **Colourblind-safe pattern fills.** The methane trend graph, welfare bar and supply chain bar get optional hatch patterns and shape markers toggled in Settings. Extends the earlier colorblind audit's "no change needed" to a belt-and-braces option.
15. **[SMALL]** **High-contrast and dyslexia-friendly font options.** Settings adds a high-contrast theme that overrides the pastoral glass panels and an optional readable-font toggle. Uses the same text-scale persistence path (localStorage) as A-/A/A+.
16. **[SMALL]** **Pin-a-stat header.** Let the player pin up to three readouts (funds, welfare, income per round) into a sticky strip that stays visible while the extras panel is open. Cuts scrolling on mobile and pairs with the mobile layout.
17. **[SMALL]** **Lever history log.** A collapsible list of "Round 4: bought Capture Systems (-40)" entries under the extras panel, filterable by lever. Gives a purchase audit trail using the same feed as the achievements' trackers.
18. **[SMALL]** **Confirm-before-big-spend threshold.** A Settings option to require confirmation for any purchase above N percent of current funds, using the shared confirmation dialog. Prevents accidental double-clicks, especially on touch.
19. **[SMALL]** **Bulk-buy stepper.** A x1/x5/max toggle beside Grow Herd and lever buttons, with the total cost shown before clicking. Removes repeated clicking late-game and reuses the rising-cost preview.
20. **[SMALL]** **Compare-with-last-round delta chips.** Small +/- chips beside funds, methane, welfare and pressure after each Advance Round that fade after a few seconds, with a "pin" click. Easy scanning of what changed; extends the F18 arrows to the round-level.
21. **[SMALL]** **Season calendar strip.** In seasons mode, a 12-round strip showing upcoming income swing and plant-demand surge values as coloured (and icon-coded) cells. Turns the deterministic swings into plannable information instead of a surprise.
22. **[SMALL]** **Poultry vs cattle comparison mini-card.** Side-by-side card of per-unit income, methane-equivalent and welfare effect for each herd type, shown in the poultry panel. Helps decide when to spend on the second herd.
23. **[SMALL]** **Breeding progress ring.** A circular timer on the breeding lever showing rounds left before it matures (3-round delay), replacing plain text. Clearer feedback for a slow-burn lever.
24. **[SMALL]** **Cap-mode headroom bar.** Under the 20-methane cap, a bar shows the remaining headroom and "rounds until you must decouple" at the current growth pace. Turns a hard block into forecastable pressure.
25. **[SMALL]** **Settings export/import.** One button copies all Herd local settings (text scale, motion, toggles, personal bests) as a short code and another restores them. Handy across devices without an account.
26. **[SMALL]** **Slow-device "lite mode".** Settings toggle that turns off the haze overlay, methane wisps and cow-graze animation and reduces the pasture to a static image. Improves battery and low-end phone performance; complements reduced motion.
27. **[SMALL]** **Achievement progress on hover.** Hovering an achievement in the panel shows a mini progress bar and the exact number left ("6 of 10 rounds under 0.5"). Uses ACHIEVEMENT_PROGRESS already in each game's hook.
28. **[SMALL]** **Session timer and pace estimate.** A discreet "about 3 min left at this pace" note on the round counter, with a "save and quit" nudge every 10 rounds. Helps short class sessions and plays nicely with save codes.
29. **[SMALL]** **Plain-language glossary popovers.** Terms like "coupling ratio", "counterfactual", "welfare" and "capture" get dotted underlines opening a one-line definition; a full glossary in How to Play. Extends the onboarding-tooltip pass to every label.
30. **[SMALL]** **Failed-save/corrupt-state friendly recovery.** If a save code fails validation in load_state, show a plain reason ("welfare value out of range, defaulted") and an option to load with defaults rather than a generic error. Surfaces the robustness work already in load_state to the player.
31. **[SMALL]** Make achievements more visible and stylized. Give Herd's achievement cards a farm-themed visual upgrade: small livestock/pasture glyphs per earned badge and a barnyard-accent border, with a brief flourish on unlock, instead of the current plain card rows.

---

## G. Thaw

1. **[BIG]** **Multi-session history dashboard.** A "Field Notes" tab charts every finished run: temperature saved, tipped regions, average acceleration factor and lever mix over time, with per-region bests. It is the presentation layer for G23's archive (not the mechanic), reading the same summaries and reusing Herd's proposed Ranch Ledger structure.
2. **[BIG]** **Overlay compare-any-two-runs view.** Pick two past runs (or one run against the Region D counterfactual) and overlay their temperature curves on one graph with the melt gridline, and show a per-round divergence readout. Extends the mini-graph and gridline into a full comparison chart, distinct from the community comparison.
3. **[BIG]** **Round replay and annotated timeline.** A scrubber replays the three regions across rounds with scientist's-log entries pinned at their rounds (tipping, milestones, first dampening). Turns the capped 40-entry log into a navigable narrative of the run.
4. **[BIG]** **Explain-this-number inspector.** Click a region's warming rate or acceleration factor and see a stacked breakdown: background rise, feedback contribution, dampening reduction, monitoring effect. Makes the trickiest math in the set (the feedback loop) fully inspectable and ties into the info-toggle copy.
5. **[BIG]** **Forecast planner with what-if lines.** A planning drawer lets the player draw hypothetical funding splits and see dashed projected temperature curves for 10 rounds on each region, next to the existing next-round tooltip. Extends the single-round preview to a horizon and pairs with preset previews.
6. **[BIG]** **Difficulty tuning panel.** Sliders for background rise, feedback strength, starting funds and monitor cost in Settings; presets Gentle / Standard / Severe. Custom runs are tagged and excluded from Z1 percentile comparisons, keeping stats fair.
7. **[BIG]** **Shareable run report / poster export.** A one-click printable or PNG card with the three region graphs, final temperature saved, best region and top log lines. Uses the shared printable-summary pattern and the best-region message, suitable as BCM evidence.
8. **[BIG]** **Save-code scenario sharing.** Export a mid-run state as a challenge code so a friend can take over from round N and try to beat your temperature-saved. Uses the shared save widget, and is a step toward the multiplayer direction.
9. **[BIG]** **Scientist-mode data layer (presentation).** A view toggle that replaces friendly labels with real units (degrees C anomaly, Gt carbon proxy) plus small footnotes on where each constant came from. Presentation and constants documentation only; G7's real-curve overlay stays its own item.
10. **[BIG]** **Full keyboard and screen-reader play.** Every invest button, preset, Advance Round and panel reachable via keyboard with focus rings, and aria-live announcements of tipping, critical tier and round results, with a text alternative for each mini-graph (a summary sentence). Extends the tier icons and colorblind work into full accessibility.
11. **[BIG]** **Long-run performance and snapshot compaction.** Cap history arrays by decimating older rounds into summary points so graphs stay fast in long sessions, with a status readout of memory use in a developer panel. Makes G9's longer-game mode safe to run on phones without slowing.
12. **[BIG]** **Region-vs-region "board room" comparison table.** A table with sortable columns (temperature, acceleration, dampening, funds, rounds since tipping, best-ever) and mini-sparklines per row, with Region D as a greyed reference row. Consolidates the scattered per-region readouts into one at-a-glance view.
13. **[SMALL]** **Unit toggle (Celsius/Fahrenheit).** A Settings option to display temperatures in F, with the gridline and thresholds converted. Tiny accessibility and locale fix.
14. **[SMALL]** **Graph pattern and marker options.** Region lines get distinct dash patterns and end markers in Settings for colour-independent reading. Extends the earlier colorblind audit.
15. **[SMALL]** **High-contrast and readable-font themes.** Overrides the glass panels for readability, persisted like text scale. Mirrors the equivalent option in Herd.
16. **[SMALL]** **Graph hover crosshair.** Hovering a mini-graph shows a round-by-round crosshair with the exact temperature and dampening at that round. Detail on demand without clutter.
17. **[SMALL]** **Larger single-region focus view.** A button expands one region's graph and readouts to full width with lever controls beneath. Helps small screens and presentation.
18. **[SMALL]** **Log filter and search.** The scientist's log gets filter chips (tipping, milestones, invest) and a text search, plus export as plain text. Makes the 40-entry capped log more useful.
19. **[SMALL]** **Log entry pinning.** Pin important entries so they survive the 40-entry cap and appear in the run report. Small addition using the log's existing structure.
20. **[SMALL]** **Preset "custom" slot.** Save your own preset split for Region B/C beside Growth/Preservation/Balanced with the same preview tooltip. Removes repeated slider work.
21. **[SMALL]** **Best-run comparison chip.** During play, a faint "personal best pace" line on Region A's graph, from the stored best run. Extends the personal-best record into an in-run target.
22. **[SMALL]** **Pace-of-run indicator.** A discreet note on the round counter for estimated session length and a "safe to save" nudge. Helps short class sessions.
23. **[SMALL]** **Confirm-before-big-spend option.** A Settings threshold using the shared confirmation dialog for large investments. Guards touch misclicks.
24. **[SMALL]** **Acceleration-factor sparkline.** A tiny sparkline next to the acceleration readout showing its recent trajectory, not only the current value. Uses the running average already tracked.
25. **[SMALL]** **Settings export/import code.** Copy and restore all Thaw local settings and personal bests as a short code for moving between devices. No account needed.
26. **[SMALL]** **Lite mode for low-end devices.** Turns off backdrop blur, starfield animation and graph transitions. Complements reduced motion; helps phones.
27. **[SMALL]** **Achievement hover progress.** Progress bars and remaining amounts on locked achievements. Uses ACHIEVEMENT_PROGRESS.
28. **[SMALL]** **Glossary popovers.** Underlined terms (dampening, acceleration factor, melt threshold, monitoring) open one-line definitions; full glossary in How to Play. Extends onboarding-tooltip coverage.
29. **[SMALL]** **Friendly corrupt-save recovery.** Save-code validation failures explain which field failed and offer load-with-defaults. Surfaces load_state robustness to the player.
30. **[SMALL]** **Community-compare history.** The G11 acceleration comparison keeps your last five percentiles in a mini list so you see improvement over runs. Adds a personal trend to an existing feature.
31. **[SMALL]** Make achievements more visible and stylized. Give Thaw's achievement cards an arctic-themed visual upgrade: small frost/permafrost glyphs per earned badge and an icy-accent border matching the region map's palette, with a brief flourish on unlock, instead of the current plain card rows.

**Notes:** Herd 2/5/7/29 and Thaw 1/2/8/29 are twin pairs (history ledger, save-code challenge sharing, planner, save recovery) and should share hub components (ledger store, snapshot-code format, planner drawer), as should the replay scrubber (Herd 3, Thaw 3), inspector (Herd 6, Thaw 4), difficulty panel (Herd 1, Thaw 6), share card (Herd 4, Thaw 7) and accessibility pass (Herd 10, Thaw 10). Herd 5 and Thaw 8 lean toward the multiplayer direction the user marked "later". Thaw 1 is the display layer for open G23 and Thaw 9 deliberately avoids G7's overlay.

---

## H. Loop

1. **[BIG]** **Chain history archive.** Every finished or reset chain is stored as a compact record (goods category, cycles to close, total extraction, final score, investment mix) and browsable in a "Past Chains" panel with a small line chart overlaying the circular-fraction curves of your last 5 chains. It gives the lifetime counters (chains completed, categories tried) real depth and lets you see whether you are actually getting better.
2. **[BIG]** **Sandbox Tuner.** An opt-in panel with sliders for starting funds, production target (30-80), the damage multiplier cap (currently 2.5x) and investment costs, so players can make Loop easier for a relaxed session or brutal for a personal challenge. Tuned chains are tagged "custom" and excluded from personal bests and difficulty-sensitive achievements (matching Z27), with the tuning saved in the save code.
3. **[BIG]** **Multi-cycle Planner.** A queue panel where you stack a plan of investments across the next 3-5 cycles and see a projected supply-fraction line, extraction cost and funds balance before committing anything. It extends the existing "time to close the loop" projection and cost-per-unit readout from one static number into an interactive what-would-happen tool.
4. **[BIG]** **Accessible Chain view.** A fully keyboard-and-screen-reader path: the ring, trade partners and meters are mirrored as an ordered list/table with an aria-live "Cycle 14 complete: 62% circular, extraction down 4" summary after every advance. Players who cannot use the animated ring (or prefer plain text) get the complete game, extending the text supply map already built.
5. **[BIG]** **Multi-slot chains.** Three named chain slots inside one save (e.g. "Clothing run", "Electronics run") with a slot switcher in the header, each showing last-played time and current circular %. Players can keep a long chain going while trying a different category, and the save code carries all slots.
6. **[BIG]** **Full-page style switcher.** Beyond the space theme, offer alternate whole-page looks (Blueprint, Paper Craft, Retro Terminal) selectable in Settings, each restyling panels, ring, meters and starfield via CSS variables only. Desktop gets the ornate versions, mobile keeps a lighter set, echoing the simple-versus-rich split already chosen for H25/H29.
7. **[BIG]** **Comparison cards.** A "Share result" button exports a short result code (category, cycles, extraction, score, per-cycle circular fractions) that a friend pastes into a "Compare" panel to see two sparkline curves and stat rows side by side. It is a no-backend social feature that reuses the save-code plumbing and the score-source pie chart.
8. **[BIG]** **Assist mode.** A three-level toggle (Off / Hints / Guided) where Hints highlights the investment with the best marginal supply gain this cycle and Guided also explains why in one line, using the loop efficiency audit's own calculations. Runs with assist are tagged, keeping mastery records honest while lowering the barrier for first-timers.
9. **[BIG]** **Career records board.** A lifetime dashboard of per-category bests (fastest close, lowest total extraction, highest score, longest zero-extraction streak) with date and settings tag, plus a heat-strip of every cycle you have ever played coloured by circular %. It turns counters into a personal "trophy wall" without adding any new mechanic.
10. **[BIG]** **Cycle ledger with export.** A table of every cycle (funds in/out, units by source, damage, multiplier, which trade partner was used) with sorting and a "Copy as CSV" button, positioned as the detailed sibling of the audit panel. It serves players who like to analyse and makes balance discussions possible.
11. **[BIG]** **Mobile-first layout pass.** A dedicated phone layout that collapses the ring, meters and investment buttons into a swipeable three-tab bottom dock (Chain / Invest / Stats) with a persistent HUD strip of cycle, funds and circular %. Complements the 320px audit in Z18 by redesigning what the small screen shows rather than just fixing clipping.
12. **[BIG]** **Long-term "Founder Rank" ladder.** Lifetime play earns non-mechanical ranks (Apprentice, Engineer, Director...) from cumulative cycles, chains closed and categories mastered, displayed as a small badge on the hub title card and inside Loop. It provides slow-burn progression that does not touch the balance or duplicate the achievements list.
13. **[SMALL]** **Keyboard shortcuts.** Space advances a cycle, 1/2/3 buy Repair/Reuse/Recycle, T triggers trade, all listed under the shared `?` help convention. Repeated actions become fast for veterans.
14. **[SMALL]** **Buy multiple.** Shift-click (or a x1/x5/x10 chip) applies an investment several times at once with a running total shown on the button. It removes a lot of tedious clicking late in a chain.
15. **[SMALL]** **Extraction cost breakdown tooltip.** Hovering the extraction cost shows "base 10 x damage multiplier 1.8 (cap 2.5)" as a small worked equation. It makes the core cost rule legible in one glance without opening the audit panel.
16. **[SMALL]** **High-contrast theme toggle.** A Settings switch that boosts text, panel border and ring node contrast and removes the starfield behind text panels. It sits next to text-size and reduce-motion in the existing settings panel.
17. **[SMALL]** **Dyslexia-friendly font option.** A Settings toggle swapping the body font to a system dyslexia-friendly stack with slightly wider letter spacing, persisted like the other settings. Cheap, high-value inclusion.
18. **[SMALL]** **Flow animation speed slider.** Separate from reduce-motion, a Slow/Normal/Fast/Off selector for the chain particles. Some players want calm ambience, others a lively flow, and low-powered devices can drop it.
19. **[SMALL]** **Shape-coded particles.** An optional mode where circular-path particles are rings and linear-path particles are squares, so the two flows differ by shape and not only colour. Belt-and-braces for the colourblind-safe audit's conclusion.
20. **[SMALL]** **Spend confirmation threshold.** A Settings option that asks "Spend 120 of 140 funds?" whenever a purchase exceeds a percentage of current funds (default off). Prevents the misclick problem without a rewind token.
21. **[SMALL]** **Panel collapse memory.** Every panel (audit, score, trade network, vignette) gets a collapse chevron whose state is remembered in `localStorage`. Players tailor the screen and the UI declutters further than the earlier pass.
22. **[SMALL]** **Live tab title.** The browser tab reads "Loop - C14 - 62% circular" and updates each cycle. Handy for multi-tab players and free to build.
23. **[SMALL]** **Wordle-style text summary.** "Copy summary" produces plain text like "Loop Clothing - closed cycle 18 - score 940" plus one block-character row of per-cycle circular fraction. It is a lightweight sharing hook that needs no image export.
24. **[SMALL]** **Next-up achievement chip.** A small header chip showing the closest unearned achievement and its progress ("Zero-extraction streak 3/5"). It surfaces goals inside the panel-only approach the user prefers over callouts.
25. **[SMALL]** **Chain size picker.** Choose Short / Standard / Long at chain start (production target 30/50/70), with scores normalised per unit so records stay comparable and labelled by size. Lets players match a session to their available time.
26. **[SMALL]** **Per-node investment sparklines.** Hover a ring node to see a tiny sparkline of your spending in that node across cycles. Extends the "most-invested node glows" feature with history.
27. **[SMALL]** **Load-time integrity check.** If a save code is corrupt or from an older version, show a friendly "repaired X, reset Y" note listing what was restored instead of silently defaulting. Player-visible robustness on top of the existing save-load audit.
28. **[SMALL]** **Cycle notes.** A one-line optional note field per cycle ("tried recycling heavy") shown in the ledger and history. Gives note-takers a place for their own strategy thinking.
29. **[SMALL]** **Performance auto-mode.** The game samples frame times and, if the ring animation is struggling, suggests "Switch to light animation?" with a one-click accept saved to settings. Keeps older phones smooth without asking players to hunt for options.
30. **[SMALL]** **Coach marks replay.** A Settings button "Replay tips" resets the one-time onboarding tooltips (Regional Partner, hard ceiling, etc.) so returning players can see them again. Closes the gap for players who dismissed them too quickly.
31. **[SMALL]** Make achievements more visible and stylized. Give Loop's achievement cards a circular-economy visual upgrade: earned badges render inside a small closed-loop ring icon (echoing the loop-closure visualization) rather than a plain card, with a brief flourish on unlock.

---

## I. Drift

1. **[BIG]** **Run archive and analytics.** Every completed run is stored (region name, difficulty, final band, round of net-positive, ROI split, trend curves) and browsable in a "Region Archive" with an overlay chart comparing wellbeing curves from any 3 runs. It turns the single localStorage personal best into a history that shows growth.
2. **[BIG]** **Scenario Builder.** Sliders for starting housing/services/infrastructure, income, background severity rate (currently 0.5 per round) and horizon (50/100/150 rounds) that produce a shareable scenario code. Built scenarios are tagged custom so records and achievements stay honest, and the recipient loads the code from the setup screen.
3. **[BIG]** **Planner assist.** A three-level toggle (Off / Suggest / Explain) that recommends this round's allocation from the existing forecast curve and ROI dashboard, with a one-line reason such as "arrivals pending will exceed services by 6". Assisted runs are tagged and excluded from personal bests, giving new players a foothold.
4. **[BIG]** **Region report export.** At the end of a run, generate a formatted "Region Report" (name, difficulty, key rounds, subscore trends, ROI table, coda choices) as a printable card and a copy-as-text version. It doubles as a sharing feature and BCM-friendly evidence of play, extending the coda without altering it.
5. **[BIG]** **Non-visual play mode.** A screen-reader-first layout where the region visual, arrival stream and gauges are mirrored as labelled tables, with an aria-live round summary and full keyboard allocation control. It goes beyond the audit in Z15 into a complete alternative way to play.
6. **[BIG]** **Multi-slot regions.** Three named save slots (using the I23 region name) with last-played time and current band, switchable from the header, all carried in the save code. Lets players explore Standard and Crisis Start regions side by side without losing progress.
7. **[BIG]** **Desktop district view.** A richer desktop-only rendering of the region visual with pan/zoom, day/night lighting, and arrival dots that travel along roads to the buildings that house them, with the existing simple visual kept for mobile. Follows the simple-versus-rich split the user asked for on Loop.
8. **[BIG]** **Round ledger.** A full-run table (funds in/out, allocation split, arrivals, integrated, pending, strain, subscores) with sorting, filtering and Copy-as-CSV. It is the detailed sibling of the ROI dashboard for analytically minded players.
9. **[BIG]** **Named difficulty tiers.** Gentle / Standard / Rigorous / Demanding presets that bundle existing toggles (accelerated severity, crisis start, second wave, policy toolkit) into one clear choice, with a summary line of what each tier changes and personal bests tracked per tier. Makes the many harder-mode options understandable and respects Z27's difficulty-aware achievements.
10. **[BIG]** **Split-screen dual-region layout.** For I1's second region, a desktop two-column view with linked highlighting (hover a subscore in one and see the equivalent in the other) and a tabbed single column on phones. It solves the layout problem the second region will cause.
11. **[BIG]** **Terminology and tone settings.** Settings let the player choose vocabulary ("arrivals / newcomers / new residents") and a numbers-only mode that hides vignettes and the dot stream, matching this game's institutional-tone sensitivity. Also gives teachers a version fit for their classroom.
12. **[BIG]** **Annotated trend graph.** Marker flags on the trend graph for events (first net-positive round, band changes, strain peaks, reallocations, second-wave start) with hover detail and toggleable layers (strain, wellbeing, control region, ROI). It brings the many recorded events into one readable story view.
13. **[SMALL]** **Keyboard allocation.** Arrow keys move funds between housing/services/infrastructure, Enter advances the round, and `?` lists shortcuts per the shared convention. Makes repeated rounds fast without a mouse.
14. **[SMALL]** **Budget templates.** Save up to three named allocation presets ("Services-first") and apply them in one click each round. Manual convenience that lives beside any future autopilot.
15. **[SMALL]** **Clear pending allocation.** A single "reset this round's changes" button restoring the last-committed split before advancing. Prevents fiddly manual undo without a rewind token.
16. **[SMALL]** **Graph range chips.** The trend graph gets Last 10 / Last 25 / All chips and a crosshair tooltip showing exact values at each round. Makes the 100-round timeline readable.
17. **[SMALL]** **Round recap line.** A one-sentence, collapsible recap after each advance ("Housing 12 short; 8 integrated; strain steady"). Gives context to the numbers without reading every gauge.
18. **[SMALL]** **Copy run summary.** A plain-text summary with a block-character wellbeing curve, region name, tier and final band for pasting anywhere. A lightweight social hook.
19. **[SMALL]** **Density toggle.** Compact / Comfortable spacing in Settings beside text size, useful on small laptops and phones. Cheap layout accessibility.
20. **[SMALL]** **High-contrast and dyslexia-font switches.** Two Settings toggles that boost contrast on gauges and panels and swap to a dyslexia-friendly font stack. Persisted like existing preferences.
21. **[SMALL]** **Animation speed selector.** Slow / Normal / Fast / Off for the arrival-dot stream and building transitions, separate from reduce-motion. Handles both preference and low-end devices.
22. **[SMALL]** **Mobile sticky HUD.** A slim persistent bar on phones showing round, funds, strain level and wellbeing band as the player scrolls the allocation controls. Keeps context visible on small screens.
23. **[SMALL]** **Segmented arrivals pipeline.** The pending-versus-integrated bar is split by age bands (this round, 2-3 rounds, 4+ rounds) so bottlenecks are obvious. Improves legibility of a core existing system.
24. **[SMALL]** **Live tab title.** The tab reads "Drift - R37 - Stable - Region Name", updating each round. Free and useful for multitasking.
25. **[SMALL]** **Records by tier.** The personal-best readout becomes a small table per difficulty tier, showing best band, fastest net-positive round and date. Pairs with named tiers.
26. **[SMALL]** **Subscore sparklines.** Each of the three composite subscores shows a tiny 20-round sparkline beside its trend arrow. Adds history at a glance without opening the graph.
27. **[SMALL]** **Save-slot timestamps.** Show "saved 3 min ago" with a manual-save nudge if the player has advanced more than 10 rounds since. Makes the save widget's state visible.
28. **[SMALL]** **Large-move confirmation.** Optional confirm when a reallocation moves more than a set share of committed capacity, tied to its cost. Guards against accidents without a token.
29. **[SMALL]** **Glossary popovers.** Tap-or-hover terms (capacity, strain, integration, control region) open a one-line definition popover with a link to The Real Story where relevant. Improves onboarding for new players.
30. **[SMALL]** **Load-time integrity check.** Corrupted or old-version saves show a friendly "restored X, reset Y" note instead of silently defaulting. Visible robustness on top of the existing save audits.
31. **[SMALL]** Make achievements more visible and stylized. Give Drift's achievement cards a visual upgrade tied to its own map/region art: a small route or milestone glyph per earned badge, with a brief flourish on unlock, instead of the current plain card rows.

**Notes:**

Overlaps: Loop 8 and Drift 3 (assist/planner) sit beside the gamified Autopilot/idle ideas but differ in being recommendations, not automation, so build them independently; Loop 1/9 and Drift 1/25 (history, records, per-tier bests) share the same stats-archive shape and could reuse one localStorage schema (per-game, not a shared module, per Z3/Z5). Loop 7/23 and Drift 4/18 (result codes and text summaries) extend Loop's ghost-code and Drift's rival-line ideas only lightly and should share the save-code encoder. Loop 2/25 and Drift 2/9 (tuner, tiers) should carry "custom" tags consistently for Z27.

---

## J. Trade Empire

1. **[BIG]** Contracts as a mini-roguelike: each "Bidding Round" offers 3 randomly-drawn exclusive contracts with different risk/reward (high margin but need a rare good; low margin but chain two colonies), the player picks one and its terms reshape the next stretch of routes. Combines with the Trade Guild TODO by giving it rarity tiers and a reason to skip the safe option.
2. **[SMALL]** Show contract card rarity by a border shape and a text label ("Rare"), never colour alone, matching the colourblind-safe conventions already in use.
3. **[BIG]** A "Cartel Board" endgame system: the player builds a market-cornering tech tree that lets them deliberately manipulate a good's price (buy out stockpile to spike, dump to crash rivals), with backlash if the same good is squeezed twice in a short window. Extends Market Speculation into strategy where the market is the puzzle, not a background.
4. **[SMALL]** A "price memory" ghost line on each sparkline showing where the price was before your last manipulation, so cause and effect is legible.
5. **[BIG]** A "Chain Builder" puzzle mode: the player draws multi-hop production chains (Ore to Alloy to Machinery) with intermediate refining colonies, scored by throughput per ship. A deeper logistics puzzle that changes how the five-good economy is read, rewarding topology thinking over button-mashing.
6. **[SMALL]** Add a "throughput per ship" number on the Ledger per chain so the score has a home before the mode exists.
7. **[BIG]** Fleet "Captains": each ship earns a randomly-drawn perk (Frugal, Lucky Trader, Night Owl, Perfectionist) at veteran-hauler milestones, and captains can be swapped between ships once per session. Adds collectable, roguelike-ish personality to the fleet, with trade-offs per archetype from the Fleet Composition TODO.
8. **[SMALL]** Show captain perks as a short quote on the ship panel ("Every crate counted twice"), for humour.
9. **[BIG]** Scenario campaign "Trade Crises": handcrafted starting boards (Grain Famine at Aurum, Isotope Glut in Kepler, a Broken Automation Network) with a par target for a gold/silver/bronze medal. Gives short replayable puzzles independent of the long main arc, and pairs with achievements for medals.
10. **[SMALL]** A "restart scenario" hotkey and best-medal chip on each scenario card.
11. **[BIG]** "Corporate Espionage" as a non-violent rivalry layer: a shadow NPC firm (named Meridian Freight) contests the same routes, revealed through market prices moving in ways the player didn't cause. The player can out-price it, sign exclusives via Trade Guild contracts, or leave it be, and no combat or piracy is needed, keeping the design rule intact.
12. **[SMALL]** A rival ledger line ("Meridian moved 340 units this cycle") that is just flavour until you've researched Market Intel.
13. **[BIG]** "Prestige Charters" beyond the flat legacy bonus: after the endgame, the player picks one permanent Charter (Hardened Fleet, Frontier Speculator, Master Diplomat) that also changes the starting board (e.g. one colony pre-developed, a locked good). Each replay feels like a new run instead of the same curve faster.
14. **[SMALL]** Show the active Charter's crest next to the game title, and list past Charters on the Ledger as a career log.
15. **[BIG]** A "Terraforming Bridge" crossover: importing the SOL prestige level (via a save code paste) grants one cosmetic-plus-small perk here, as the lore tie made mechanical but optional. Uses no shared code, only a typed short code, and reinforces the hub as a family of games.
16. **[SMALL]** A "Visitor from SOL" one-line log entry when a valid code is redeemed.
17. **[BIG]** A "Market Weather" system beyond seasonal demand: unpredictable one-off booms and slumps (a festival at Verdant, a strike at Ferrum) that last 20-40 ticks and cascade through dependent colonies, with the Almanac hinting at leading indicators. Players who read the ledger closely can front-run them, which rewards attention and mastery.
18. **[SMALL]** A "news ticker" chip on the map with a one-line headline ("Strike at Ferrum: ore output down"), styled as text so it stays motion-free.
19. **[BIG]** "Ship Blueprint Lab": a research-unlocked tuning screen where players allocate points among speed, hold, and efficiency to design a custom hull, then name and save it. Multiple hull designs per run make Fleet Composition a creative decision, and each optimum shifts with the current market.
20. **[SMALL]** Add a "compare to average hull" bar chart on the Lab screen so trade-offs are one glance.
21. **[BIG]** A "Hub & Spoke" strategic layer: the player can designate one colony as a Distribution Hub that halves transit between it and its neighbours but caps its own stockpile; different hub choices favour different networks. Introduces topology decisions on the map and changes how Fleet Priority routes ships.
22. **[SMALL]** Draw the hub's node with a thicker ring and a tooltip stating its current bonus, so its effect is inspectable.
23. **[BIG]** An "Expedition" side-mode: send one ship on a long multi-tick exploratory run away from the routes, with a probabilistic reward table (new good, one-time windfall, research points, nothing). It's a risk/reward gamble with the opportunity cost of that ship's income, and it makes the idle-manual-ship warning meaningful.
24. **[SMALL]** Show an "expedition odds" tooltip on the send button to keep the gamble honest.
25. **[BIG]** "Colony Personalities": each colony gets an evolving temperament from its trade history (Grateful, Demanding, Opportunistic) that changes its price premium and how it reacts to Colony Investment or Loyalty events. It gives the five worlds character, and a reason to route differently to each.
26. **[SMALL]** A small emoji-free mood glyph shape (circle/triangle/square) on each colony node, keyed to temperament with a legend.
27. **[BIG]** A "Second Economy" endgame tier: once the fourth cluster exists, unlock an interstellar commodities exchange where the player sets standing buy/sell orders that fill on their own, turning the endgame from watching a machine to programming one. Ties Player-Run Trade Post, Speculation and Automation into one mature system.
28. **[SMALL]** An "order book" mini-table with the last five fills, so the exchange feels alive.
29. **[BIG]** A "Blackout Challenge" hard mode: opt-in, the map and market sparklines are hidden except through purchased Market Intel research, and prices display as ranges, not exact figures. Trades become judgment calls, the opposite of the almanac-heavy default, aimed at veterans wanting a tense replay.
30. **[SMALL]** A "dark run" achievement and Ledger stamp for completing the endgame under Blackout, with the badge showing on the title screen.
31. **[SMALL]** Make achievements more visible and stylized. Give Trade Empire's achievement cards a space-commerce visual upgrade: earned badges render on a small "Ledger" ribbon strip near the toggle button (echoing the game's own Ledger/title-screen stamp language), with a brief flourish on unlock, instead of a plain card list.

---

**Notes:** SOL's Doctrines and Stress Tests overlap thematically with Continuum's and Loop's automation ideas, so sharing an "if/then rule" UI component across games is worth considering. Trade Empire's Charters and Blackout Challenge mirror SOL's Mutators and Scarcity Run as opt-in difficulty dials; a shared "run modifier" pattern could serve both. The Time Capsule and Ghost Run ideas should be revisited once multiplayer is scoped.

---

## K. Continuum

*(Round 3. Assumes all of round 2's K list plus the eighth-era build are done. Ideas marked (T) lean into the tech-professional / California audience lens without changing the game's SDG 11 identity.)*

1. **[BIG]** (T) A "policy scripting" rules engine: the player writes simple if/then standing orders ("if food surplus < 10%, shift labour to Provision; if unrest > 30, pause new districts") that run automatically each season. It gives a systems-minded player a reason to automate and optimise, and a failed script is a satisfying bug to hunt. It hooks into the research tree (each script slot or trigger type is unlocked by a research node) and logs its firings into the policy log.
2. **[BIG]** A "Dynasty" meta-progression layer: every completed or failed run banks Legacy points that buy permanent starting perks and new starting scenarios (a hardier tribe, a river-valley start, a library heirloom). It gives replays a growth arc beyond the score. Perks are shown in the settlement archive and can be switched off for purists, and hard mode runs earn extra Legacy.
3. **[BIG]** A crisis deck: each era draws from a randomised deck of era-specific shocks (drought, plague, market crash, fire, grid outage, solar storm) and the player pre-drafts a small hand of mitigation policies before the first shock lands. This adds tension and a "what did I draw this time" replay hook. The crises reuse the civic-engineering-challenge framework, and surviving them feeds achievements.
4. **[BIG]** (T) A "technical debt" mechanic in the Digital and later eras: quick, cheap infrastructure builds accrue hidden debt that silently raises maintenance and failure odds until the player schedules a refactor season. It mirrors a real engineering trade-off the audience knows well and gives a fresh growth-vs-sustainability tension. Debt appears as a line on the planner's dashboard and a hazard tint on the civic infrastructure map.
5. **[BIG]** Living ruins: buildings from earlier eras persist as heritage sites in the 3D scene and on the infrastructure map. They give culture bonuses if preserved, or free land and materials if demolished, at a livability cost. This makes the one-continuous-city idea physical, and it uses the Look Back UI to preview what each ruin was.
6. **[BIG]** Era doctrines: at each era transition the player picks one doctrine (Maritime, Highland, Caravan, Scholarly) that reshapes which research branches are cheap and which buildings unlock. Two runs then genuinely diverge. It pairs with Dynasty perks and the founder's log, which records the choice.
7. **[BIG]** Neighbouring settlements: 2-3 AI cities with their own eras and needs appear on a small regional map. The player trades, shares research, or competes for a contested resource. It adds a new decision axis now and is deliberately the same interface a later multiplayer mode would use, so the AI slots are the stand-ins for real players.
8. **[BIG]** An advisor council of 3-4 named characters (a farmer, an engineer, a merchant, a scholar) who give conflicting recommendations each season. The player tracks who they trust, and each advisor's track record is scored against real outcomes. It is an optional, story-toggle-friendly layer that gives a face to the sustainability tradeoffs without lecturing.
9. **[BIG]** (T) A time-lapse run replay: the whole playthrough is scrubbed back as a 3D timelapse with the policy log, founder's log entries and research unlocks pinned to a timeline. A 20-second clip or image strip can be exported. It builds directly on the shareable snapshot card and the settlement archive, and it is exactly the kind of thing this audience posts.
10. **[BIG]** A daily seed challenge: one fixed seed, scenario and modifier per day (for example "Scarcity + plague at year 40"), with a par score to beat. It is async and needs no multiplayer, only the Z1 stats endpoint for a "you vs. everyone" percentile. It gives a reason to return without any streak guilt.
11. **[BIG]** (T) A scenario editor and "mod codes": sliders for starting resources, event frequency, era length and a handful of rule toggles, exported as a short share code. A player builds a brutal scenario and challenges a friend to beat its par. This uses the existing save-code mechanism and is a natural bridge to multiplayer challenges.
12. **[BIG]** A generated map with biomes: rivers, coasts, mountains and desert change which resources are cheap, where districts can go, and how disasters hit. This changes the opening moves every run. The Three.js scene and the 2D infrastructure map both render it, and consulting-mode cities come with their own inherited geography.
13. **[BIG]** An endless "Beyond" mode after the last era: instead of a completion state, the eras keep procedurally escalating with generated eras (each with a themed sustainability mechanic) and rising entropy, and the score is how many eras a city survives. It answers "rather than closing it, keep making more eras" with unlimited replay. The archive records a "furthest era reached" ladder.
14. **[BIG]** (T) A "post-mortem" screen after any run: an auto-generated retrospective (what went well, what went wrong, root cause of the biggest livability drop, three decisions to redo) built from the policy log and the livability-vs-growth scatter. It borrows the language of an engineering post-mortem, which this audience will appreciate, and it makes each loss actively useful.
15. **[BIG]** Specialisation of citizens: named citizens are generated with a trade and a personal thread (an apprentice becomes a guild master; a child becomes the engineer of the next era). The player can invest in a few "notable citizens" who follow the city across eras and unlock small bonuses. This gives the story system a recurring cast, can be switched off, and the founder's log can reference them.
16. **[SMALL]** (T) A "why did that change" explainer: hovering a stat delta shows its top three contributing factors as a little waterfall. It fits the optimiser mindset, needs no teaching text, and makes cause and effect discoverable.
17. **[SMALL]** A limited-use "rewind one season" token, earned through achievements or a Dynasty perk, so a hasty decision is not a run-ender. It softens frustration while still costing something valuable.
18. **[SMALL]** (T) A data export button: CSV/JSON of per-season stats and policy-log entries for anyone who wants to pull the run into a spreadsheet. It costs very little and sits well with this audience's tendency to analyse.
19. **[SMALL]** A side-by-side compare of two archived settlements, with stats deltas highlighted, so a player can see exactly what their hard-mode run did differently from their first one.
20. **[SMALL]** Cosmetic city banners and skyline flourishes unlocked by achievements and Dynasty rank, displayed in the archive and on the shareable card, for cheap prestige and personalisation.
21. **[SMALL]** A "screensaver" mode: the 3D city runs itself with a slow orbit camera and ambient soundscape, with all UI hidden, for leaving on a second monitor.
22. **[SMALL]** Per-era ambient soundscapes (wind and fire for Tribal, market chatter for Medieval, hum of servers for Digital) as an opt-in layer with its own volume slider and a mute default, adding atmosphere without needing any voice or speech work.
23. **[SMALL]** (T) Easter-egg flavour in the Digital era's log lines and building names (a legacy-server closet, a co-working guild hall) that a tech-industry player will smile at, kept subtle and switchable with the story toggle.
24. **[SMALL]** A named-settlement feature: a name generator with era-flavoured suggestions and a free-text option, shown on the plaque, archive, and share card, so the city feels like the player's own.
25. **[SMALL]** Hidden achievements: a small set of unlisted achievements ("Survived a plague without a granary", "Never demolished a building") that only reveal on unlock, adding discovery to the existing 19-plus achievement panel.
26. **[SMALL]** (T) A "par time" badge for speed-focused players: finish the run in fewer real minutes or fewer seasons than a par set per scenario. It pairs with the time-played readout and gives the speedrun-minded a target.
27. **[SMALL]** Sparklines next to every stat on the planner's dashboard showing the last 20 seasons, so trends are visible at a glance without opening the graphs.
28. **[SMALL]** A "citizen of the season" spotlight card in the log: one named resident, one line of colour tied to a recent event, purely flavour and removable with the story toggle.
29. **[SMALL]** A "blitz" opt-in timer per season for hard-mode players: decisions must be made in 30 seconds or the default policy applies. It is a pure adrenaline variant and earns a dedicated achievement.
30. **[SMALL]** (T) A hotkey remapping panel in Settings next to the "?" cheat-sheet, so a keyboard-fluent player can bind advance-season, view switches and camera presets to their own keys.
31. **[SMALL]** Make achievements more visible and stylized. Give Continuum's achievement cards a civic/era-themed visual upgrade: earned badges render with a small per-era icon and the violet-glass accent already used elsewhere in the shell, laid out like a small "monument row" rather than a plain card list.

---

## L. Le Champ de Mots

*(Round 3. Assumes the full round-2 L list is built, including the placement test, music/reading quiz game, streak calendar, marathon, phrasebook, quick-water and conversation simulator. Learning value is kept central since this is for FREN151/152.)*

1. **[BIG]** A farm economy: mastered plots produce harvest coins, spent at a market stall on cosmetic decor, watering upgrades (a bigger can that hits adjacent plots' review reminders) and new plot skins. It makes long-term consistency feel like building something, and it feeds off the existing practice-progress ledger without touching SRS scheduling.
2. **[BIG]** Boss fights: at the end of each chapter a "market-day boss" combines that chapter's vocab, grammar and phonetic items into a multi-round fight with lives and a special attack when the player chains a combo. Defeating it grants a plot skin and an achievement. It reuses the combo bonus, adaptive distractors and proficiency-test question pool.
3. **[BIG]** A roguelike "Voyage" mode: the player crosses France city by city with a deck of question cards, picks relic power-ups between rounds (a free hint, a second try), and each run is different. Everything answered flows back into the SRS and the practice ledger, so replaying is study in disguise.
4. **[BIG]** An "error detective" mode: the game shows a French sentence with one planted mistake (a gender, an agreement, an accent, a wrong auxiliary) and the player taps the wrong word and fixes it. It trains recognising errors, which is a different skill from recalling answers, and it can draw its mistakes straight from the error-pattern digest.
5. **[BIG]** A village with named NPCs and quests: recurring characters (the baker, the postman, the vet) request items and phrases across days, and the player builds a friendship level by answering correctly. A light story thread runs through it and can be turned off, and it extends Café Rush's and Boutique Dash's customer idea into persistent characters.
6. **[BIG]** A daily mots croisés: one procedurally generated mini-crossword or word-search a day built from words the player has unlocked or is currently learning, with a par time. It gives a habit-forming, low-pressure daily puzzle and feeds the practice ledger.
7. **[BIG]** Cloze stories: short generated paragraphs built from mastered vocabulary with a few gaps to fill, ordered from easy to hard, which builds contextual understanding. It works alongside the reading-quiz game from L1 and can share its open-source story library.
8. **[BIG]** A mock-exam simulator: a timed test built in the style of FREN151/152 exams, drawing from a chosen chapter range and giving a predicted grade, a per-topic breakdown and a "fix these three things" list. It differs from cram mode by mimicking exam pressure and pacing.
9. **[BIG]** An exam-date planner: the player enters their exam date and a what-if slider ("if I study 15 minutes a day, I'll have N% of plots at Automated by then"). The game projects the harvest from the actual SRS state and suggests the minimum daily effort. It complements the study-buddy coach with a longer horizon.
10. **[BIG]** A conjugation matrix puzzle: a grid of persons by tenses with some cells blanked, the player fills them in against the clock and earns combos for whole rows or diagonals. It trains the pattern-recognition side of verbs, which a flashcard style covers badly, and it can be the fifth family entry next to Verb Racer.
11. **[BIG]** A farm layout and customisation sandbox: earned decor (scarecrows, fences, fountains) can be placed freely around the plots, and the farm can be screenshotted as a card. It personalises the study space and makes achievements feel tangible.
12. **[BIG]** Classmate farm visits: a share code lets a classmate view a read-only snapshot of your farm and leave a "care package" (a challenge set of 5 of their toughest words for you). It is a small, safe first step toward the multiplayer direction and needs only a backend snapshot table.
13. **[BIG]** A personal mnemonic notebook: for any plot the player can write their own mnemonic or memory sticker, which the game shows on a failed answer and offers to auto-suggest from past failures. Self-made hooks are stronger than supplied ones and it strengthens the phrasebook.
14. **[BIG]** A daily quest board: three small goals a day ("water 5 grammar plots", "beat 90 in Blitz", "answer 3 liaison items") each granting coins or practice score. It is habit-forming without streak guilt because missed days just leave the board empty, not broken.
15. **[BIG]** A "faux amis" minigame and plot flag: a rapid-fire mode where the player decides if a word is a real cognate or a false friend, with a stack of increasingly sneaky examples. It targets a classic English-speaker mistake and makes a fun arcade variant.
16. **[SMALL]** A "faux ami" warning badge on affected plots on the farm grid, using the same icon system as the vocab/grammar/phrase/phonetic type markers.
17. **[SMALL]** A "golden plot" of the day: one random due plot is highlighted, and answering it correctly gives double practice score. It is a friendly nudge toward a plot the player might otherwise skip.
18. **[SMALL]** Leech detection: an item failed many times in a row becomes a "stubborn weed" with a special treatment (a mnemonic prompt, a chunked re-teach card, or a hint that it might be suspended for a while) so the player is not stuck grinding it.
19. **[SMALL]** A typo-forgiveness token: once per session a "that was a slip" button lets the player undo a wrong typed answer that was clearly a keystroke error, without penalising the SRS interval.
20. **[SMALL]** An on-screen accent bar (é, è, ç, œ) beside every typed input, with a toggle to make accents strictly required or lenient. It removes a mechanical annoyance on phones and desktops.
21. **[SMALL]** A weekly recap card: a one-screen, non-guilt summary (plots watered, best combo, new plots automated, hardest word) with a share image. It is shown once a week and is easy to dismiss.
22. **[SMALL]** A Pomodoro-style study timer that makes crops visibly grow while it runs, with a small bonus on completion and a stop button that carries no penalty.
23. **[SMALL]** A scarecrow mascot with a few reaction animations (cheers a combo, slumps at a weed) and unlockable outfits from achievements, adding personality to the farm's UI.
24. **[SMALL]** A filter and sort control on the farm grid ("weakest first", "due today", "by type") so the player can jump straight to what needs attention.
25. **[SMALL]** An opt-in "hardcore" mode: strict grading everywhere, no hints, no multiple-choice fallback, and a dedicated achievement for the whole week completed under it. It gives advanced students a mastery challenge.
26. **[SMALL]** Player titles that rise with the practice ledger (Apprenti, Jardinier, Fermier, Maître de Ferme) shown in the header and on shared cards.
27. **[SMALL]** A session "highlight reel" on the results screen: best combo, quickest answer, and the toughest word beaten, giving each study session a small, positive sign-off.
28. **[SMALL]** An exam countdown widget in the header that shows the number of days to the entered exam date and the current projected coverage, hiding itself if no date is set.
29. **[SMALL]** A weak-items export: a CSV or Anki-compatible deck of the player's flagged items for use in another study tool, since the player's own study habits may not stay within one app.
30. **[SMALL]** Rotating seasonal farm sprites and weather (autumn leaves, snow) tied to the real calendar or the semester's stage, purely cosmetic and controlled by the visual-style switcher.
31. **[SMALL]** Make achievements more visible and stylized. Give Le Champ de Mots' achievement cards a warmer, farm-themed visual upgrade — small crop/harvest glyphs per earned badge instead of plain rows — themed consistently across all four visual styles (High-def/Low-poly/Text-based/Cartoon), the same "restyle, not rebuild" discipline the visual-style switcher itself already established.

---

**Notes on overlaps.** Continuum's neighbouring settlements (K7), scenario share codes (K11) and daily seed (K10), and Le Champ de Mots' classmate farm visits (L12), all lean on the same async share-code and Z1-stats plumbing and are natural stepping stones to the multiplayer direction. Continuum's Dynasty (K2) and Le Champ's farm economy and titles (L1, L26) are the same meta-progression pattern and could share a hub-level "legacy/rank" component. Continuum's hidden achievements and Le Champ's boss fights should ride the existing `achievements.json` manifest, with no backend change.

---

## M. New Game Ideas

**Five fresh pitches, none reused from rounds 1-2.** Per your standing preference these lean *fun first* — mechanics and personality, not lessons. As before, a "yes" here means "worth a groundwork plan" (a new `planning/<game>-plan.md`), not "add this to an existing game." Each says which existing hub pattern it could reuse.

1. **Heist Committee** — a turn-based crew-planning game: you pick a target (a vault, a museum, a casino barge), recruit a crew of five oddball specialists with clashing personalities, then plan the job on a timeline by dragging each person's action into slots. The heist then plays out step by step, and things go wrong in funny, chain-reaction ways that your plan either absorbed or didn't. Replay comes from a rotating pool of targets, crew traits and complications. Pyodide-friendly (pure turn logic), reuses the achievements/settings/confirm-dialog stack; the timeline UI is the only new thing.
2. **Lighthouse** — a cozy idle/management game about one keeper on one rock. Storms roll in, ships pass, and you allocate oil, repairs and lamp-hours while a growing cast of passing sailors leaves you letters, gifts and small mysteries. It is deliberately quiet, with a strong sense of place: the fun is the tension of a bad night and the satisfaction of a clear one. Closer in shape to SOL's idle loop than to any climate game, with a story layer that can be switched off.
3. **Cryptid Hunt** — a deduction roguelite. Each run, a hidden creature is generated from a handful of traits (habitat, diet, active hours, weakness); you gather evidence from a small procedural map (tracks, sounds, photos) using a limited number of field days, then commit to a trap. The satisfaction is the "aha" of narrowing candidates, and runs are short and endlessly different. Reuses the roguelite meta-progression idea (unlock gear and clue types between runs) inside this one game only.
4. **Pocket Bazaar** — a fast merge-and-fulfil game: a small market stall where customers arrive with orders, you combine basic goods into better ones on a merge board, and you race the clock and their patience. Streaks, combos and a rotating "festival" modifier keep it snappy. It is the most arcade-like of the five, with a quick session length (3-5 minutes), and pairs naturally with the hub's mobile-dock and settings work.
5. **Dead Reckoning** — a navigation puzzle game: you are a ship's navigator with only speed, heading and time (no map reveal), plotting a course across a chart with currents, wind and hazards, then "sailing" it and seeing how far your estimate drifted from the truth. Later charts add fog, tides and multiple ships. It is a satisfying skill/precision game with an honest sense of mastery, and the core is a small pure-Python simulation with a clean chart UI.

---

## N. Seasonal/Real-World-Date Events (originally its own doc, seeded from TODO.md's Z23; folded in here and the standalone file deleted 2026-09-22 — this section is now the only copy)

Your own Round 2 answer set the shape: *"a 'holiday' lasts a week and something like christmas they have to play canopy in a mode for getting christmas trees to get the 'christmas 2026' badge on their profile."* Every idea below follows that shape exactly — a real-world date window, a flavor-only change to existing UI/text, and a reward that's a badge or small cosmetic, never a new balanced mechanic. It rides the achievements framework's existing zero-backend-cost plumbing (`achievements_earned`), so a badge here costs nothing new to store. The 8 climate-quartet games each get one idea tied to a real, dated awareness day; SOL and Le Champ de Mots get one idea fitting their own theme; Trade Empire and Continuum are deliberately skipped (neither has a natural "climate holiday" hook).

1. **[SOL]** New Year "New Horizons" nudge (Dec 31 – Jan 6). A one-line seasonal banner next to the Prestige button; starting a prestige run during the window grants a "New Horizons 2027" badge. No numeric bonus — a nudge toward something already possible, timed to a real date.
2. **[Canopy]** Christmas "Holiday Tree-Planting Drive" (Dec 20–27) — the exact case from your own answer. Forest-request flavor text swaps to holiday-themed asks, the Replant button gets a small string-of-lights reskin for the week (cosmetic only, no cost change). Replanting 5 plots during the window earns the "Christmas 2026" badge. The cleanest fit in the hub: Canopy's real mechanic (replant, watch it recover) already *is* tree-planting.
3. **[Grid]** Earth Hour "Lights Out" week (last Saturday of March, ±3 days — a real dated annual event). One round per session gets a flavor overlay about the city switching off for an hour; finishing that round with the grid above 50% clean share earns an "Earth Hour 2027" badge.
4. **[Tide]** World Oceans Day "Reef Watch" week (Jun 8, ±3 days — a real UN-recognized date). Ticker/button text swaps to a beach-cleanup flavor, the acidity meter gets a small coral accent for the week. Investing in adaptation infrastructure during the window earns an "Oceans Day 2027" badge.
5. **[Aftermath]** International Day for Disaster Risk Reduction week (Oct 13, ±3 days — a real UN-designated day, a strong thematic match). Event-sequence narration frames around "community preparedness" for the week. Unlocking any skill-tree node during the window earns a "Disaster Risk Reduction 2026" badge.
6. **[Herd]** World Environment Day "Methane Watch" week (Jun 5, ±3 days — real, UN-designated). Round-event text frames the week's pressure narration around environmental awareness; the methane meter gets a small leaf-accent border. Investing in any decoupling measure during the window earns an "Environment Day 2027" badge.
7. **[Thaw]** International Polar Bear Day week (Feb 27, ±3 days — real, dated, Arctic-specific). A seasonal ticker note plus a small polar-bear-silhouette accent on the region map; purely cosmetic, doesn't touch the feedback-loop math. Investing in a permafrost-preserving measure during the window earns a "Polar Bear Day 2027" badge.
8. **[Loop]** Global Recycling Day "Closed Loop" week (Mar 18, ±3 days — real, dated). Circularity-investment buttons get a seasonal callout; the loop-closure visualization gets a seasonal highlight when it improves. Raising circular-vs-new-extraction percentage during the window earns a "Recycling Day 2027" badge.
9. **[Drift]** World Refugee Day "Welcome Week" (Jun 20, ±3 days — real, UN-designated, and thematically the strongest fit of the set). Integration-service flavor text swaps to welcome-week framing. Investing in integration services during the window earns a "Refugee Day 2027" badge.
10. **[Le Champ de Mots]** Bastille Day "Quatorze Juillet" week (Jul 14, ±3 days). The existing cultural-notes toggle gets extra Bastille-Day content for the week; completed review sessions during the window get a small tricolor plot-border accent. Completing a review session during the window earns a "Quatorze Juillet 2027" badge.
11. **[BIG]** Build the shared mechanism this all rides on. Not built yet — the shape below is a starting sketch, not a spec. A game that opts in declares a small `EVENTS` list next to where `achievements.json` is already referenced:
    ```python
    EVENTS = [
        {
            "id": "canopy-christmas-2026",
            "start": "2026-12-20", "end": "2026-12-27",
            "flavor": {"request_intro": "A family wants a tree for the town square this Christmas..."},
            "badge_id": "christmas-2026",
            "qualifies": lambda state: state["replants_this_event"] >= 5,
        },
    ]
    ```
    A tiny shared `shared/seasonal-events.js` (dropped in unchanged, same as `shared/save-widget.js`) would: check today's date against each declared event's window; if active, swap in the `flavor` overrides and show a small banner; and once `qualifies` passes, call the existing achievement-grant path — no new backend, no new save field, no new account-side storage beyond what achievements already have. Keeps the whole feature opt-in per game and every event cosmetic-only.

---

## O. Replayability follow-up (originally its own doc, seeded from TODO.md's Z7 audit; folded in here and the standalone file deleted 2026-09-22 — this section is now the only copy)

The Z7 read-only audit found 10 of the 12 games already have enough of a reason to play twice (or correctly don't need one — a teaching tool where one thorough playthrough *is* the point): SOL's Prestige/NG+, Canopy's legacy-forest carryover, Grid's Operator Career + scenarios, Tide's scenarios + checkpoint-replay, Aftermath's run-based skill tree, Herd's/Thaw's/Le Champ de Mots' teaching-tool shape (replay isn't the right lever), Loop's category-picker + streak, and Drift's built-in comparison-region payoff. Only two games came out with a real, specific gap — both below.

**Trade Empire** — a full 14-milestone sandbox economy with **zero prestige/legacy/meta-progression**; once the automated trade network runs itself, there's no mechanical reason to found a new corporation and do it again (this concretizes the already-open `J21` backlog item rather than inventing a new ask).

1. **[BIG]** Charter renewal (concretizes J21). On reaching the endgame state, offer a "Renew the Charter" reset — same shape as SOL's Prestige button, confirm-dialog gated. Pick **one** small inherited advantage (a pre-established trade route, a discount on the first automation system, starting reputation with one colony type) once per charter, not stacked freely.
2. **[SMALL]** Founding-conditions variety on renewal: each charter randomizes which two colonies start connected and what they specialize in, so the first logistics bottleneck differs charter to charter.
3. **[BIG]** Lifetime ledger: a small permanent stats page (mirrors SOL's lifetime stats surviving Prestige) tracking cumulative goods moved, routes established, and charters completed across every past playthrough on this browser.
4. **[SMALL]** An opt-in "harder charter" toggle, unlocked only after the first endgame — same shape as SOL's New Game+ Challenge (faster market saturation, shorter colony-need cadence) for players who want a tougher run rather than a bonus-boosted easier one.

**Continuum** — real scenario/mode variety already exists (K12's three starting scenarios, K18's hard mode, K22's consulting-mode cases) plus a settlement archive, but **no in-game "start a new settlement" control anywhere** — the built variety currently has no front door back to it short of clearing browser storage by hand.

5. **[BIG]** An actual "Found a New Settlement" control: a confirm-dialog-gated action (same pattern as SOL's Reset This World/Prestige) that archives the current settlement if needed, then starts a brand-new `Campaign` — the missing front door back to K12's scenario picker, K18's hard mode, and K22's consulting mode.
6. **[SMALL]** Surface the archive as a jumping-off point, not just a record: a "Found a new settlement" button next to each archived entry on the Civilization Summary panel, not only a passive read of past runs.
7. **[BIG]** A light "founder's legacy" carryover, in the spirit of Canopy's B15 legacy-forest pattern — a new settlement's opening season starts with one small, named bonus derived from the previous settlement's peak achievement, capped small and singular like SOL's one-node-at-a-time Prestige tree.
8. **[SMALL]** A fourth starting scenario, unlocked only after reaching Space Age once, for a returning player who's seen every era and wants a deliberately different opening than the existing Standard/Harsh Frontier/Fertile Valley set.

**Notes.** If Trade Empire's charter-renewal idea (1) is accepted, it directly resolves the open `J21` line in `TODO.md` — check that item off rather than tracking both separately. Items 1-4 and 5-8 don't overlap or need shared scaffolding.

---

## P. Signal — open questions (approved round-2 M3, full plan in `planning/signal-plan.md`)

*A five-minute daily deduction puzzle: hidden transmitters broadcast on a grid, you can only "listen" at a few spots, and work out where they are from the summed signal strength.* Recommended mechanic (Option A, "Triangulate"): 9x9 grid, 3 hidden transmitters, 8 pings, each ping returns the *sum* of every transmitter's signal at that cell — an analog-sum puzzle distinct from Wordle/Mastermind/Minesweeper. Daily seed is a pure function of the UTC date (no backend, works offline); one deliberate stack exception is plain vanilla JS instead of Pyodide, since a daily puzzle needs to open instantly. The full plan has the complete data model, 14 launch achievements, and an 8-milestone build order — nothing below repeats that, only the genuinely open calls.

1. Plain-JS exception OK, or do you want Pyodide anyway for consistency (costs a multi-second first load on a "quick daily" game)?
2. Theme: retro radio-room (recommended) or something else (submarine sonar, alien SETI)?
3. UTC daily reset acceptable, or prefer each player's local midnight (then different time zones get different puzzles, killing "same puzzle for everyone" share talk)?
4. Want an optional non-daily "endless" practice mode beyond the archive?
5. Should the launch date (puzzle #1) be tied to a specific day for the 2-week visibility cadence?
6. Is Option A the mechanic you want, or should we prototype Option B ("Tuner", slider-based) briefly first?

---

## Q. Undersleep — open questions (approved round-2 M4, full plan in `planning/undersleep-plan.md`)

*Run one slightly overcommitted person's day: slot work, food, friends and naps into a schedule while their body clock quietly judges you, and optionally let the game mirror your own real sleep and mood.* Your own answer asked for more: *"there is a lot that can be done to make this more and better and it could also be made somewhat like a life tracker too."* The plan is deliberately split into two separable layers — **Layer A, the game** (a circadian-curve sim, fully playable with zero real data) and **Layer B, an optional Journal** (a 10-second daily sleep/mood/energy check-in, local-only by default, that can cosmetically or numerically mirror into the game only behind explicit opt-in toggles). No medical claims anywhere; the "teaches sleep debt" framing from the original pitch is dropped in favor of pure fun/comedy. The full plan has the complete meter/event/progression design, privacy controls, and a 10-milestone build order (1-7 ship a complete game with no tracker; 8-9 add the journal as a fully cuttable add-on).

1. Journal cloud sync: allow it at all (via the existing save system, separate opt-in), or keep the journal strictly local plus manual export/import?
2. If sync is allowed, are you comfortable with that data in the Neon database given it's more personal than game saves? (Want it encrypted client-side with a passphrase?)
3. Should the game start with the tracker hidden ("Just play" default, recommended) or present at first run?
4. Tone: deadpan-absurd (recommended) or warmer/cozy?
5. Character: one persistent character, or a roster with "retire and inherit"?
6. Is a hard "Not medical advice" gate at first Journal open (one-time acknowledge) acceptable, or too heavy?
7. Any real-life journal tags you specifically want (caffeine, exercise, screen-late...) or leave to my defaults?
8. Story mode: a light arc (new job, new city) or sandbox only at launch?

---

## S. Overclock — open questions (approved round-2 M6, full plan in `planning/overclock-plan.md`)

*A roguelike deck-builder: draft a run-specific deck of abilities, fight through procedurally arranged encounters of escalating difficulty, permadeath-and-retry — pure build-crafting-and-combat satisfaction, "this run vs. the last one." Fun-first, no educational framing.* You said you want "some kind of gimmick that makes this game special" and lean space or cult, but neither is chosen yet, and this plan deliberately doesn't define cards, energy rules, enemy design, encounter shape, or theme — those all wait on your answers below. The full plan has the complete technical foundation (seeded-RNG run engine, run/meta state split, content-as-JSON pipeline) and a 7-milestone baseline build order that's genre-agnostic; a second milestone set starts only once the gimmick is picked. This plan's own section 4 is also the **shared baseline checklist** that Last Line and Deep Descent below both reference rather than repeat.

1. Space or cult (or something else)? This sets tone, palette, favicon glyph and ambient background.
2. What is the one mechanic that makes it not-just-Slay-the-Spire (e.g. a resource that overheats/corrupts, a shared deck between runs, a ritual/sacrifice loop)?
3. Run length target: ~15 minutes (quick, mobile-friendly) or 45+ minutes? Drives whether mid-run saves matter.
4. Meta-progression between runs: unlocks only (new cards), permanent stat upgrades, or none (pure skill)?
5. Story/flavor text on or off by default?

---

## T. Last Line — open questions (approved round-2 M7, "same as 6", full plan in `planning/last-line-plan.md`)

*Classic tower defense: place and upgrade defenses along a winding path against escalating waves, chase a personal-best wave-survived count. Arcade-strategy fun, leaderboard-friendly, no narrative.* Shares Overclock's full baseline checklist (save/settings/achievements/changelog/tutorial/confirm-dialog/mobile-dock/colorblind rules/test harness/feedback/hub integration) rather than repeating it. The one big genre-specific technical fork already resolved in the plan: a tick-driven deterministic sim stepped by a fixed-step `step(dt_ticks)`, with Fast-forward/Pause/"Send next wave" controls from day one, since real-time proved a poor fit for how this stack loads games. What's still open:

1. What is the gimmick that differentiates it (e.g. the path can be rerouted, towers decay, a shared resource with the player's own "last line" unit)?
2. Fixed handcrafted maps, or seeded procedurally generated paths?
3. Real-time waves, or wave-by-wave turn-based (the biggest technical fork — see the plan's section 3)?
4. Endless mode with a best-wave leaderboard only, or also a campaign of finite levels?
5. Is a hub-wide leaderboard wanted (needs a new backend table — currently no such thing beyond ratings/saves)?

---

## U. Deep Descent — open questions (approved round-2 M10, "same as 6", full plan in `planning/deep-descent-plan.md`)

*Roguelite dungeon-crawler: procedurally generated floors, permadeath runs, loot and ability pickups that change each attempt's build. Exploration-and-combat fun; replayability comes entirely from randomization.* Also shares Overclock's full baseline checklist. Turn-based on a tile grid is the assumed shape (consistent with real-time being a poor fit here), but movement/combat rules are undecided; rendering is planned as a DOM monospaced text-grid (roguelike ASCII look), not canvas, for testability and accessibility. What's still open:

1. What is the hook (e.g. light/darkness, a rising hazard chasing you down, floors that remember your previous runs)?
2. Grid-step turn-based (roguelike classic), or room-to-room node navigation (closer to Overclock's map)?
3. How much meta-progression: pure permadeath, or a hub between runs that unlocks classes/items?
4. Fog of war and line-of-sight: yes or no (affects generation and rendering cost)?
5. Overlap check with Overclock: both are permadeath runs with loot — how do these two feel distinct on the same hub?

---

## Z. Games (cross-game patterns, things worth doing across many or all games)

1. **[BIG]** A shared "seeded run" module: every game's randomness routes through one `shared/seed.py` that accepts a short seed string (e.g. `TIDE-K7F2Q`), so a run can be replayed exactly. Players get a "copy seed" button on run-end screens and a "start from seed" field on the new-game screen; this is the foundation for every async-multiplayer idea below and needs no backend at all.
2. **[BIG]** Async challenge links: a player finishes a seeded run, taps "Challenge a friend," and gets a URL (`/games/tide/?challenge=<seed>&beat=<score>`) that opens the game on the same seed with a "beat 4,210" banner. A tiny `POST /challenges` stores the seed/score/username so the result comes back as a "friend beat you" note in Continue Playing; no live connection, so it fits a static site.
3. **[BIG]** Ghost runs as a shared pattern: record a compact per-turn "trace" (score or key stat per season/tick) into the save state and let any game replay someone else's trace as a faint line on its existing chart. Ships once as a shared trace recorder and ghost-overlay renderer, then each game opts in with two lines; friends' ghosts come via challenge links, and the site's own "median run" ghost comes from the stats endpoints.
4. **[BIG]** Per-game leaderboards with a privacy tier: a shared `POST /scores` + `GET /leaderboard/{game}/{board}` where every board entry is anonymous by default ("Player 7F2Q") and the player can flip a single account setting to show their username. Seeded-run boards (daily seed, weekly seed, all-time) and personal-best rows are built once; each game just declares its board names and a score-validation function.
5. **[BIG]** Daily seed for every game: one deterministic seed per UTC date derived from the date string (no server needed to generate it), with a "Today's run" button on each game's start screen and a hub strip that shows which daily runs you have done today. A streak counter rewards coming back without any punishment for missing a day.
6. **[BIG]** Weekly "hub-wide challenge rotation": each week the hub picks one game and one modifier (e.g. "Herd, no antibiotics" or "SOL, half starting energy") from a shared JSON schedule, and every game already supports a `modifiers` list via one shared loader. It pairs with the event-badge system from round 2 but is a weekly rhythm, not a holiday one, and gives a reason to visit that isn't a new game.
7. **[BIG]** A shared "player profile" data model that lives in the account and aggregates across games: total time played, achievements per game, favourite game, longest streaks, badges. The profile page (see Y) reads it, but the important cross-game work is defining the schema once and having a small `profile.update()` helper each game calls at save time, rather than the hub scraping each save blob.
8. **[BIG]** Cross-game "cameo" unlocks that keep each game's own look: earning a milestone in game A can unlock a tiny cosmetic or flavour item in game B (a Tide tide-pool creature that appears in Drift's ocean, a Canopy tree species named in Thaw's log). Each game renders the cameo in its own art style; a shared `unlocks.json` only stores the flag, so nothing homogenises.
9. **[BIG]** A shared save-schema versioning and migration harness: every save state carries `schema_version`, and `shared/migrate.py` runs a chain of tiny per-game migrations on load with a fixture-based test that loads every historic save shape ever shipped. Failed migrations fall back to a "we couldn't read this save, here's the raw code to send to the developer" screen instead of a silent reset.
10. **[BIG]** A save "time machine": the save widget keeps the last 5 auto-snapshots (locally, plus on the backend for signed-in players) and offers "restore an earlier state" with timestamps and a one-line summary from each game. This is the safety net that makes opt-in autosave feel low-risk, and it recovers from the classic "autosaved right after the mistake" case.
11. **[BIG]** A shared Playwright/fake-DOM "smoke everything" test harness that boots each game headlessly, runs N scripted turns with a random-action fuzzer, asserts no exceptions and no NaN/negative-resource states, and runs all 12 in one command. It replaces the per-game hand-verification the dev logs describe with a regression net that catches cross-cutting breakage (a shared file changing) immediately.
12. **[BIG]** A performance budget with enforcement: a script measures each game's Pyodide boot time, first-interactive time, and payload size (a table in `planning/` regenerated by hand like the other scripts) and fails loudly if any game exceeds a written budget. Includes trying Pyodide's package pre-loading/caching in the service worker so repeat visits skip the biggest download.
13. **[BIG]** A localisation-ready string layer: the shared UI (save widget, confirm dialog, tutorial, achievements panel) reads from a `strings.json` per language with English as default, and `shared/i18n.js` exposes `t("key")`. Le Champ de Mots doesn't need it, but a Spanish/French pass on the climate quartet would fit the site's education angle and can start with the shared widgets only.
14. **[BIG]** A shared "spectate a run" replay format: a game records its player inputs plus seed (not state) so any run can be replayed deterministically in a read-only "replay" mode with play/pause/speed controls. Works for challenge links, admin bug repro (a player's report attaches a replay), and community highlights that show a real run rather than a text stat.
15. **[BIG]** A shared achievement tier system: every achievement gets a bronze/silver/gold rarity label computed from its live "% of players" figure (once that exists), so labels adjust as more players arrive instead of being hand-assigned. Hidden achievements reveal their description only after the first player earns them, and each game keeps its own icon art.
16. **[BIG]** A shared "co-op via shared save" experiment: two players open the same read-mostly "world code" for a game (starting with a low-stakes one such as Canopy's forest or Drift) and each submits a turn per day, with the backend merging into one world state. Turn-based and asynchronous means no websockets; it is the smallest honest step toward real multiplayer.
17. **[BIG]** A shared "bug report with context" flow: the in-game report button (Z16) attaches the current save code, schema version, browser/viewport and last 20 log lines automatically, and posts to a `/bug-reports` endpoint that the admin page lists. It turns vague "it broke" feedback into reproducible reports, with a clear preview of exactly what will be sent.
18. **[BIG]** A shared "practice sandbox / freeplay" toggle where a game exposes a `sandbox()` hook that removes fail states and unlocks all tools without touching the real save or achievements. Games with steep learning curves (Grid, Continuum, Trade Empire) benefit most, and a single toggle pattern keeps it opt-in per game.
19. **[SMALL]** A shared `prefers-reduced-motion` and `prefers-contrast` honouring stylesheet fragment (`shared/a11y.css`) that games import so animations and flashes calm down automatically, layered over each game's own settings toggle rather than replacing it.
20. **[SMALL]** A shared "copy result as text" helper that produces a Wordle-style emoji/text summary of a run ("Tide, seed K7F2Q, 4,210 pts, 3 storms survived") for pasting in chat, one function every game calls from its end screen.
21. **[SMALL]** A tiny shared `shared/perf-mark.js` that logs Pyodide boot milestones to `performance.mark` and to the console in one consistent format, so the boot-time budget script and any future admin diagnostics read the same names.
22. **[SMALL]** A "saved 2 minutes ago" indicator inside the shared save widget that shows when the last successful save (manual or auto) happened and turns to a plain-text warning if the last save attempt failed, so nobody plays an hour believing they're saved.
23. **[SMALL]** A shared "touch target and tap-delay" CSS baseline (min 44px hit areas, `touch-action: manipulation`) applied via one stylesheet include, then a quick sweep of each game's tiny buttons.
24. **[SMALL]** A shared `console.warn` "dev overlay" (enabled by `?debug=1`) that shows FPS, state size in bytes, and the last save payload length in a corner box, handy for the save-portability audit and for spotting runaway state growth while developing.
25. **[SMALL]** A shared error boundary: uncaught Python or JS exceptions inside any game show a friendly "something went wrong, your save is safe" panel with a copy-details button, instead of a frozen page, using one small wrapper included by every game.
26. **[SMALL]** A shared "quiet mode" mute switch that sits in the shared UI corner and applies to any audio a game adds later, defaulting to muted-until-first-tap so no game ever blasts sound on load.
27. **[SMALL]** A shared achievement "share" button that copies a one-line text ("I earned 'Last Stand' in Tide, 3.1% of players have it") plus a game link, using the live rarity figure once available.
28. **[SMALL]** A shared "pause when tab hidden" helper for any game with a real-time loop (SOL, Trade Empire, Continuum's animation), so background tabs don't burn CPU or silently advance the simulation.
29. **[SMALL]** A shared "print-safe game info" footer snippet: every game's info/help panel shows its version/changelog date, seed (if any) and site URL at the bottom, so screenshots and printouts submitted as evidence are self-identifying.
30. **[SMALL]** A shared `data-testid` naming convention on the shared components (save widget, confirm dialog, achievements panel, tutorial) documented in `planning/game-template.md` so the smoke-test harness and future e2e tests don't depend on fragile selectors.

---

## Y. Home (the hub shell)

1. **[BIG]** A public player profile page (`profile.html?u=name`) showing a player's badges, per-game achievement counts, favourite game and member-since date, off by default with a single "make my profile public" switch. Signed-in players get a "share my profile" link; everyone else sees only what the owner opted to show.
2. **[BIG]** A hub "Today" strip above the game grid: today's daily seed status per game, the week's rotating challenge, any active event badge, and your current streak, all in one compact row. It gives returning visitors a reason to open the hub before picking a game, and it is a single data-driven JSON feed the admin edits.
3. **[BIG]** A hub-wide leaderboards page (`leaderboards.html`) with a game picker, board picker (daily / weekly / all-time) and a "friends only" tab using a username-based friend list. Anonymous-by-default rows follow the privacy tier from Z, and the hub page is the one place all of them live.
4. **[BIG]** A friends list on the account: add by username, see a small "last played" line and current-streak for each, and receive challenge links inline. Requests are mutual-accept, with no messaging, keeping moderation load at zero for a solo developer.
5. **[BIG]** A personalised "For you" row on the lobby: a rule-based recommender (no ML) that suggests the next game from your tags, what you have finished, what your similar-tag players finished, and games you haven't touched. It builds on onboarding survey answers and the aggregate stats and always shows why ("because you finished Canopy").
6. **[BIG]** Per-game "hub info pages" (`/game/tide` style static pages, or hash routes) with a description, screenshots, average rating, %-completed, top achievements and a big "Play" button. Each page gets its own social card and search-engine title, so the hub has one shareable URL per game rather than only the grid.
7. **[BIG]** Real social-share cards: generate per-game 1200x630 PNG cards with a small Python script (like the other `scripts/`), and set Open Graph / Twitter meta on the hub, each game page and the roadmap. Link previews are the cheapest possible marketing for a static site and cost nothing at runtime.
8. **[BIG]** A sitemap, robots.txt, and structured-data (`VideoGame`/`WebApplication` JSON-LD) pass generated by a script from `game-manifest.json`, plus a Search Console verification file. Pure static work that helps the site actually be findable, and a good piece of BCM206 public-availability evidence.
9. **[BIG]** Offline "play any game without internet" mode: the service worker pre-caches a game's Pyodide bundle when the player taps a "Download for offline" button on its card, showing an honest size estimate and a storage-used readout. Opt-in per game, so the cache doesn't balloon for someone who only plays one.
10. **[BIG]** A hub "settings" page consolidating site-level prefs in one place: theme, reduce motion, text scale default, autosave default, analytics opt-in, announcement/tour reset, "clear local data" and "export everything." It gives the opt-in-first philosophy a single visible home instead of scattered toggles.
11. **[BIG]** A community "activity feed" on the hub: anonymised, rate-limited lines such as "someone just earned Christmas 2026" or "a Herd farm hit 90% methane reduction," generated from the stats tables. It makes the site feel alive with zero chat and zero moderation risk because nothing is free text.
12. **[BIG]** A season/event hub: a `events.html` page with the current holiday event, a countdown, a per-event badge gallery (including missed ones shown greyed out with "returns next year") and a link to each participating game's event mode. A single `events.json` drives both the page and the badge display already on the profile.
13. **[BIG]** An admin dashboard v2 with time-series: daily plays, signups, saves, feedback and bug reports as sparkline charts, a "top errors this week" table from the bug-report endpoint, and a moderation queue for feedback/answer reports. All sourced from existing tables with `GROUP BY date` queries, still direct-URL only.
14. **[BIG]** A "data export and delete my account" flow in account settings: download everything the server holds on you as JSON (saves, achievements, feedback, profile) and a confirmed permanent delete. It backs up the terms page's promises with real controls and is a very honest trust signal.
15. **[BIG]** A "Help / FAQ" page with searchable answers (how saves work, autosave, why accounts exist, how to move devices, what's stored) fed by the same deep-search index the lobby uses. Every "how do I…" that comes through the feedback box gets a permanent answer instead of a reply.
16. **[BIG]** A mobile-first "app shell" polish pass on the hub: bottom navigation bar on phones (Games / Today / Profile / More), pull-to-refresh via service-worker revalidate, and safe-area padding for notched devices in installed-PWA mode. The mobile dock already exists in games; this brings the same feel to the hub itself.
17. **[BIG]** A web-push-free "notify me" alternative: an opt-in email-less digest by letting a signed-in player pin "tell me when this game updates," surfaced as a badge on the What's New link and their profile. It reuses the new-since-visit logic per game, no push permission or email infrastructure needed.
18. **[BIG]** A "collections" feature: players tag games into their own lists ("cozy," "play on phone," "class evidence") stored in the account, and filter the lobby by them. It gives long-time players a personal organisation layer without changing the shared tags.
19. **[SMALL]** Add keyboard shortcuts to the hub itself (`/` focuses search, `g` then `r` opens roadmap, `?` shows the list), matching the in-game convention from Z4.
20. **[SMALL]** A "copy my site stats" line on the profile ("12 games, 87 achievements, joined Sept 2026") for sharing.
21. **[SMALL]** A `<noscript>` and old-browser fallback message on the hub explaining exactly what needs JavaScript/WebAssembly and listing the games anyway, so failures aren't a blank page.
22. **[SMALL]** A per-title-card "estimated session length" chip (5 min / 20 min / long-form), taken from a manual field in `game-manifest.json` and filterable in the lobby, helping the "quick vs deep" preference from the onboarding survey.
23. **[SMALL]** A tiny "What's Popular this week" caption under the sort dropdown that shows the leader of each sort (top rated, most saved, most played) so the sort options feel meaningful even before someone changes them.
24. **[SMALL]** A "was this helpful?" thumbs-up/down on each What's New entry, saved to the feedback table with the entry id, telling you which shipped changes players actually care about.
25. **[SMALL]** An offline indicator banner ("You're offline, cached games only") driven by `navigator.onLine`, which greys out cards that aren't cached instead of leaving them to fail.
26. **[SMALL]** A hub "reduce data" note in settings that skips loading the stats/community endpoints for players on data saver (`navigator.connection.saveData`), quietly doing it by default without any prompt.
27. **[SMALL]** A small "site status" dot in the footer (green/amber) reflecting whether the FastAPI backend responded to a lightweight `/health` ping, with a one-line explanation for why ratings/saves may be unavailable rather than silent failures.
28. **[SMALL]** A "print my achievements" stylesheet for the profile/dashboard page: clean black-on-white list with progress bars, using the shared print CSS from Z21, for anyone who wants an evidence printout.
29. **[SMALL]** A "credits & thanks" page section (or a footer link) listing tools, fonts, Pyodide, and playtesters who consent to being named, kept separate from the Z29 sources aggregation page.
30. **[SMALL]** A "last verified" line on the terms/privacy page auto-filled from the file's git date and a link to a short "what changed" list, so trust content visibly stays maintained.

---

**Notes on overlaps.** Z1-Z5, Z14 and Z16 form one multiplayer stack (seeds, challenge links, ghosts, leaderboards, replay format, shared-world) and pair directly with Y2-Y4 (Today strip, leaderboards page, friends list); build the seed module first, as everything else layers on it. Z7/Z15 (profile data model, tiers) feed Y1/Y20 (profile page), and Z9/Z10 (migrations, time machine) support the opt-in autosave already on the TODO. Z12/Z21 (perf budget, offline) overlap Y9 (offline-per-game) and Y16 (mobile shell).

---

## X. Warframe Build Tracker (fun-and-power round)

*(Personal project, not part of the hub; answers route into `planning/TODO.md`'s X section like everything else.)* This round leans into "go bigger" per your earlier notes: what the parts *become*, the meta, and using the imported account data (X-b) for more than a resource count. Nothing here repeats an item already shipped or still open in the X list. I have not verified game-data specifics against the wiki, so anything that depends on exact numbers should be checked against real sources when built.

1. **[BIG]** A "meta build planner": pick a known community build for an Amp, Zaw or Kitgun (with its named mods/parts) and see the whole chain — parts still to farm, resources still needed, forma/mod costs — as one plan with a single completion bar.
2. **[SMALL]** A "what am I building this week" pin: star up to three builds and keep them at the top of the page.
3. **[BIG]** A weapon/warframe/companion crafting tracker (the direction you described for X17), starting with a manual list of foundry items and their component needs, with the imported `lastData.dat` marking what's already owned.
4. **[SMALL]** A "foundry timer" note: enter when you started a craft and get a simple "ready at" time, with a browser notification option.
5. **[BIG]** A Void-relic planner for prime parts: given the parts you want, list which relics carry them, how many you own, and a refinement/farming order.
6. **[SMALL]** A "credits and endo budget" line beside every plan so you can see whether a build is credit-limited or farm-limited.
7. **[BIG]** A drop-source optimizer that, for your whole wishlist, suggests a farming session ("do these three missions in this order, expect to cover 60% of your needs"), building on the route-planner idea already on the list.
8. **[SMALL]** Mastery-rank checklist: tick off weapons and frames mastered, with a simple "items until next rank" readout.
9. **[BIG]** An arcane/mod inventory tracker driven by the import: show duplicates, unranked mods worth ranking, and a "trade or fuse" suggestion list.
10. **[SMALL]** A "recently completed" strip showing your last five finished builds, with the date.
11. **[BIG]** A forma planner: for a chosen build, lay out the polarity slots and the forma sequence needed, with a running forma total across all your active builds.
12. **[SMALL]** A tiny "plat value" estimate per completed build, using a manual price you type in (no live market dependency).
13. **[BIG]** A "trader schedule" tab for the rotating vendors: a manual list of what you're watching for and a reminder line ("Baro is due back in N days") based on a date you enter.
14. **[SMALL]** A one-click "copy my wishlist as text" that formats builds and needs for pasting into a clan chat.
15. **[BIG]** A progress history chart: snapshot your completion percentage each time you import, and graph it, so you can see your farming pace over weeks.
16. **[SMALL]** A "lucky drop" counter — log when a rare drop lands and show your running tally, purely for the fun of it.
17. **[BIG]** A "clan/friend shared goals" view: export a shareable code of your wishlist so a friend can import it and see who can help farm what.
18. **[SMALL]** A per-resource "I have enough" toggle so surplus stockpiles stop showing as needs.
19. **[BIG]** A companion/kubrow/kavat breeding and imprint planner, if the import exposes the data; otherwise a manual log of pets and their mods.
20. **[SMALL]** A short "farming tips for this resource" note that appears on hover, written by you, stored in the tracker's own data file.
21. **[BIG]** Build-loadout notes: attach your own mod list and playstyle notes to each finished build, so the tracker doubles as a personal armory.
22. **[SMALL]** A colour tag per build (for example "daily driver", "fun", "sell") with a filter.
23. **[BIG]** A "what changed since my last import" diff view: after you upload a fresh `lastData.dat`, show new items, new resources and everything that ticked forward.
24. **[SMALL]** A "long-term goals" list separate from active builds, so aspirational items don't clutter the shopping list.
25. **[BIG]** A daily/weekly checklist tab (standing caps, rotating missions, daily login) with automatic reset times, since it's the natural home for routine tasks around farming.
26. **[SMALL]** Keyboard shortcuts for the common actions (search, mark built, add to wishlist), with a "?" cheat-sheet like the games have.
27. **[BIG]** A cross-checked "am I wasting anything?" audit: flag resources you're overstocked on, duplicate mods that could be fused, and blueprints you own but never built.
28. **[SMALL]** A tiny changelog of your own tracker edits ("added 3 builds today") for the satisfaction of a visible history.
29. **[BIG]** An "endgame readiness" score that combines owned frames, weapons, forma count and mod ranks into one playful number with a breakdown, purely as a personal benchmark.
30. **[SMALL]** A "export everything to a file" and matching restore button, so a backup exists outside the hub's account/save system.

---

# PART 3 — Returning later

## R. Returning Later (everything parked in `planning/LATER.md`, for you to re-decide)

Nothing here is new; these are the items you (or I) deferred earlier. Each one needs one word from you: **now** (move it to the TODO), **later** (keep it parked), or **drop**. A few have already changed status since they were parked; those are marked so you don't spend an answer on them. Numbering is fresh for this round; the original label is in brackets.

**Audio (one decision unlocks seven items).** The standing question is still open: browser audio in this stack means the Web Audio API or `<audio>` tags triggered from JS, which is realistic for short effects and hard for precise timing. If you say "now" here I'll write up exactly what's feasible and cost it per item.
1. Should audio be built at all, as an opt-in, default-off feature with a mute control in every game's settings panel? *(unlocks items 2-8)*
2. [SOL A5] a light click/coin-drop sound effect.
3. [Canopy B5] a minimal recovery/wildlife chime.
4. [Continuum K4] a distinct audio cue per era transition.
5. [Continuum K11] an optional ambient audio bed per era.
6. [Thaw G7] a minimal ping for the tipping-point moment.
7. [Le Champ de Mots L21] a pronunciation-practice mode (slowed TTS playback plus a visual syllable breakdown).
8. [New game M9, Offbeat] the rhythm/timing arcade game, blocked on both audio and Pyodide timing precision.

**Per-game items**
9. [SOL A7] a "+X since last save" delta readout right after loading a save (you said you didn't understand it; the idea is a quick "+540 Iron, +12 Auto-Miners since this save was made").
10. [SOL A12] a personal-best "fastest full playthrough" timer.
11. [SOL A13] a "never touched automation" pure-clicker challenge achievement, kept easy per your rule for achievements.
12. [SOL A18] a "reset this world only" option. *Status changed: it was built anyway, but an audit found you had said "later," so it needs your keep-or-revert call.*
13. [Continuum K3] a full-playthrough integration test (Tribal through Space Age in one run); an engineering task, not player-facing.
14. [Continuum K7] viewing a revisited era's snapshot in the 3D layer. *Status changed: an audit found it was built despite "later"; confirm keep or revert.*
15. [Grid C6] a "later" with no comment; it needs a real answer.
16. [Grid C11] aggregate clean score across players. *Status changed: now covered by the Z1 stats backend and Grid's community comparison, so nothing left to decide except cleaning the stale entry.*
17. [Grid C14] confirm-before-retiring-the-last-plant, "undo or 'are you sure?' with don't-show-again". *Status changed: the shared confirm dialog now covers this.*
18. [Tide D10] a "later" with no comment; needs a real answer.
19. [Tide D20] a light visual flourish on the endgame ("maybe later").
20. [Aftermath E5] an Aftermath idea marked "later" with no comment. The label may point at the wrong idea; I'll re-read the original and restate it for you.
21. [Herd F4] a "later" with no comment; needs a real answer.
22. [Herd F10] a full "Restart Farm" reset, where you said "maybe prestige rather than full reset". Herd has since gained a certification unlock and a poultry flock, so a prestige layer may now fit; want one?
23. [Herd F20] swapping the intro blurb once methane crosses a threshold (you weren't sure what it changes; it means the top-of-game sentence would react to how the session is going).
24. [Thaw G8] an in-game reset/restart button (a convenience over reloading or loading a blank save code).
25. [Loop H16] a "later" with no comment; needs a real answer.
26. [Drift I4] an in-game "Start New Region" reset, marked "maybe"; same category as Thaw's G8, so one answer can cover both.

**Round-2 items you deferred**
27. [Canopy B5, round 2] compare the forest's standing value against the site-wide average. You wanted "a full multiplayer pass soon" first.
28. [Grid C21, round 2] a "grid twin" split-view comparing two strategies side by side. You left it as my judgment call on whether it's too much for the player; I parked it for a scoping conversation.
29. [Tide D3, round 2] a multi-settlement mode (two coastal settlements at once); the same judgment-call reasoning as C21.
30. [Tide D25, round 2] a "shared coastline" cooperative community stat, saved for the multiplayer update.
31. [Aftermath E11, round 2] a "mutual aid network" positive event, waiting on multiplayer.
32. [Thaw G25, round 2] a "counterfactual world tour" previewing Region D's trajectory on the other regions' starting conditions ("no but maybe later").
33. [Continuum K30, round 2] a "peer city" async ghost overlay; you said it could be good but confusing, and want multiplayer scoped first.
34. [Warframe tracker] a "riven disposition" reference column for completed builds ("maybe much later; right now it's a crafting and resource tracker").

**Site-wide and new-game items**
35. [Hub L5, round 1] a site-wide dark/light theme toggle. *Status changed: you approved it in round 2 and it is now TODO item Y11; nothing to decide here.*
36. [Hub L9] whether and how to apply for real ads. *Status: the AdSense signup is the action item in `planning/FOR-YOU.md`; nothing to decide here.*
37. [New game M2, Silk Road] my read is it's too close to Trade Empire without a sharper hook. Is there a distinct mechanic you want to give it, or should it stay parked?
38. [New game M8, Contraption] a physics sandbox needs a JS physics engine (for example Matter.js), a bigger stack decision similar to Continuum adopting Three.js. Adopt one deliberately, or keep it parked?
39. **The multiplayer pass itself.** Six of the items above (27, 30, 31, 33, and the Continuum/Herd community items) wait on it. You said it's likely the next big development after this set. Want a scoping document written for it as the first step?

---

# PART 4 — Your Answers

Everything above, pre-titled and pre-numbered so you never have to write out a `## <SECTION>` header or an item number yourself. Just type after the number — "yes", "no", "later", or a word plus a short note — and leave anything you're not ready for blank. Same rules as always: "yes" builds it, "no" drops it, "later" parks it. For Part 4's own N/O/P/Q/S/T/U sections (the folded-in seasonal-events, replayability, and new-game-groundwork content), the same words apply, except "later" and "drop" for the new-game open questions (P/Q/S/T/U) just mean "leave that specific design fork undecided a while longer" rather than dropping the whole game, since those five games are already approved.

### GB — Canopy (gamified)
1. 
2. 
3. 
4. 
5. 
6. 
7. 
8. 
9. 
10. 
11. 
12. 
13. 
14. 
15. 
16. 
17. 
18. 
19. 
20. 
21. 
22. 
23. 
24. 
25. 
26. 
27. 
28. 
29. 
30. 

### GC — Grid (gamified)
1. 
2. 
3. 
4. 
5. 
6. 
7. 
8. 
9. 
10. 
11. 
12. 
13. 
14. 
15. 
16. 
17. 
18. 
19. 
20. 
21. 
22. 
23. 
24. 
25. 
26. 
27. 
28. 
29. 
30. 

### GD — Tide (gamified)
1. 
2. 
3. 
4. 
5. 
6. 
7. 
8. 
9. 
10. 
11. 
12. 
13. 
14. 
15. 
16. 
17. 
18. 
19. 
20. 
21. 
22. 
23. 
24. 
25. 
26. 
27. 
28. 
29. 
30. 

### GE — Aftermath (gamified)
1. 
2. 
3. 
4. 
5. 
6. 
7. 
8. 
9. 
10. 
11. 
12. 
13. 
14. 
15. 
16. 
17. 
18. 
19. 
20. 
21. 
22. 
23. 
24. 
25. 
26. 
27. 
28. 
29. 
30. 

### GF — Herd (gamified)
1. 
2. 
3. 
4. 
5. 
6. 
7. 
8. 
9. 
10. 
11. 
12. 
13. 
14. 
15. 
16. 
17. 
18. 
19. 
20. 
21. 
22. 
23. 
24. 
25. 
26. 
27. 
28. 
29. 
30. 

### GG — Thaw (gamified)
1. 
2. 
3. 
4. 
5. 
6. 
7. 
8. 
9. 
10. 
11. 
12. 
13. 
14. 
15. 
16. 
17. 
18. 
19. 
20. 
21. 
22. 
23. 
24. 
25. 
26. 
27. 
28. 
29. 
30. 

### GH — Loop (gamified)
1. 
2. 
3. 
4. 
5. 
6. 
7. 
8. 
9. 
10. 
11. 
12. 
13. 
14. 
15. 
16. 
17. 
18. 
19. 
20. 
21. 
22. 
23. 
24. 
25. 
26. 
27. 
28. 
29. 
30. 

### GI — Drift (gamified)
1. 
2. 
3. 
4. 
5. 
6. 
7. 
8. 
9. 
10. 
11. 
12. 
13. 
14. 
15. 
16. 
17. 
18. 
19. 
20. 
21. 
22. 
23. 
24. 
25. 
26. 
27. 
28. 
29. 
30. 

### A — SOL
1. 
2. 
3. 
4. 
5. 
6. 
7. 
8. 
9. 
10. 
11. 
12. 
13. 
14. 
15. 
16. 
17. 
18. 
19. 
20. 
21. 
22. 
23. 
24. 
25. 
26. 
27. 
28. 
29. 
30. 
31. 

### B — Canopy
1. 
2. 
3. 
4. 
5. 
6. 
7. 
8. 
9. 
10. 
11. 
12. 
13. 
14. 
15. 
16. 
17. 
18. 
19. 
20. 
21. 
22. 
23. 
24. 
25. 
26. 
27. 
28. 
29. 
30. 
31. 

### C — Grid
1. 
2. 
3. 
4. 
5. 
6. 
7. 
8. 
9. 
10. 
11. 
12. 
13. 
14. 
15. 
16. 
17. 
18. 
19. 
20. 
21. 
22. 
23. 
24. 
25. 
26. 
27. 
28. 
29. 
30. 
31. 

### D — Tide
1. 
2. 
3. 
4. 
5. 
6. 
7. 
8. 
9. 
10. 
11. 
12. 
13. 
14. 
15. 
16. 
17. 
18. 
19. 
20. 
21. 
22. 
23. 
24. 
25. 
26. 
27. 
28. 
29. 
30. 
31. 

### E — Aftermath
1. 
2. 
3. 
4. 
5. 
6. 
7. 
8. 
9. 
10. 
11. 
12. 
13. 
14. 
15. 
16. 
17. 
18. 
19. 
20. 
21. 
22. 
23. 
24. 
25. 
26. 
27. 
28. 
29. 
30. 
31. 

### F — Herd
1. 
2. 
3. 
4. 
5. 
6. 
7. 
8. 
9. 
10. 
11. 
12. 
13. 
14. 
15. 
16. 
17. 
18. 
19. 
20. 
21. 
22. 
23. 
24. 
25. 
26. 
27. 
28. 
29. 
30. 
31. 

### G — Thaw
1. 
2. 
3. 
4. 
5. 
6. 
7. 
8. 
9. 
10. 
11. 
12. 
13. 
14. 
15. 
16. 
17. 
18. 
19. 
20. 
21. 
22. 
23. 
24. 
25. 
26. 
27. 
28. 
29. 
30. 
31. 

### H — Loop
1. 
2. 
3. 
4. 
5. 
6. 
7. 
8. 
9. 
10. 
11. 
12. 
13. 
14. 
15. 
16. 
17. 
18. 
19. 
20. 
21. 
22. 
23. 
24. 
25. 
26. 
27. 
28. 
29. 
30. 
31. 

### I — Drift
1. 
2. 
3. 
4. 
5. 
6. 
7. 
8. 
9. 
10. 
11. 
12. 
13. 
14. 
15. 
16. 
17. 
18. 
19. 
20. 
21. 
22. 
23. 
24. 
25. 
26. 
27. 
28. 
29. 
30. 
31. 

### J — Trade Empire
1. 
2. 
3. 
4. 
5. 
6. 
7. 
8. 
9. 
10. 
11. 
12. 
13. 
14. 
15. 
16. 
17. 
18. 
19. 
20. 
21. 
22. 
23. 
24. 
25. 
26. 
27. 
28. 
29. 
30. 
31. 

### K — Continuum
1. 
2. 
3. 
4. 
5. 
6. 
7. 
8. 
9. 
10. 
11. 
12. 
13. 
14. 
15. 
16. 
17. 
18. 
19. 
20. 
21. 
22. 
23. 
24. 
25. 
26. 
27. 
28. 
29. 
30. 
31. 

### L — Le Champ de Mots
1. 
2. 
3. 
4. 
5. 
6. 
7. 
8. 
9. 
10. 
11. 
12. 
13. 
14. 
15. 
16. 
17. 
18. 
19. 
20. 
21. 
22. 
23. 
24. 
25. 
26. 
27. 
28. 
29. 
30. 
31. 

### M — New Game Ideas
1. 
2. 
3. 
4. 
5. 

### N — Seasonal/Real-World-Date Events
1. 
2. 
3. 
4. 
5. 
6. 
7. 
8. 
9. 
10. 
11. 

### O — Replayability follow-up (Trade Empire + Continuum)
1. 
2. 
3. 
4. 
5. 
6. 
7. 
8. 

### P — Signal — open questions
1. 
2. 
3. 
4. 
5. 
6. 

### Q — Undersleep — open questions
1. 
2. 
3. 
4. 
5. 
6. 
7. 
8. 

### S — Overclock — open questions
1. 
2. 
3. 
4. 
5. 

### T — Last Line — open questions
1. 
2. 
3. 
4. 
5. 

### U — Deep Descent — open questions
1. 
2. 
3. 
4. 
5. 

### Z — Games (cross-game patterns)
1. 
2. 
3. 
4. 
5. 
6. 
7. 
8. 
9. 
10. 
11. 
12. 
13. 
14. 
15. 
16. 
17. 
18. 
19. 
20. 
21. 
22. 
23. 
24. 
25. 
26. 
27. 
28. 
29. 
30. 

### Y — Home (the hub shell)
1. 
2. 
3. 
4. 
5. 
6. 
7. 
8. 
9. 
10. 
11. 
12. 
13. 
14. 
15. 
16. 
17. 
18. 
19. 
20. 
21. 
22. 
23. 
24. 
25. 
26. 
27. 
28. 
29. 
30. 

### X — Warframe Build Tracker
1. 
2. 
3. 
4. 
5. 
6. 
7. 
8. 
9. 
10. 
11. 
12. 
13. 
14. 
15. 
16. 
17. 
18. 
19. 
20. 
21. 
22. 
23. 
24. 
25. 
26. 
27. 
28. 
29. 
30. 

### R — Returning Later
1. 
2. 
3. 
4. 
5. 
6. 
7. 
8. 
9. 
10. 
11. 
12. 
13. 
14. 
15. 
16. 
17. 
18. 
19. 
20. 
21. 
22. 
23. 
24. 
25. 
26. 
27. 
28. 
29. 
30. 
31. 
32. 
33. 
34. 
35. 
36. 
37. 
38. 
39. 

