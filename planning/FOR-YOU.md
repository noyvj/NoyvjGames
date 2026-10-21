# For You — Things Only You Can Do, and Questions I Need Answered

I check this file whenever I'm doing site work. Two kinds of entries live here:

- **Action items** — real-world steps only you can take (an external account signup, a decision that needs your own login/credentials). Each one says why it's needed, exactly how to do it, and what to tell me afterward so I can pick the work back up.
- **Questions** — decisions I can't make for you. Type your answer directly under the `**Your answer:**` line for that question.

**Once you've done an action item or answered a question, I remove that whole entry the next time I'm in here** — so this file only ever shows what's still actually open. Nothing is ever silently dropped: once handled, the substance moves into the relevant commit, doc, or `planning/TODO.md`/`LATER.md` line, same as everything else. If you want to double check what got removed, `git log -- planning/FOR-YOU.md` has the full history.

---

## Action items

### 0. Clean up test rows my audit wrote to the live database

**Why:** during the 2026-10-06 playtest audit my random-click testing submitted some in-game feedback ("yes"/"no") rows and a few anonymous saves to production before I added a write-blocker. The API has no delete route, so only you can remove them (Neon SQL editor). Details and the exact SQL, with a preview query to run first, are at the bottom of `planning/AUDIT-261006.md`.

**Steps:** run the two `SELECT` previews, check the rows are test data (the date filter may also match real submissions from 5 Oct), then run the `DELETE`s. Tell me once done and I will remove this entry.

### 0c. PC version of every game: send screenshots when all are done

**Your answer (2026-10-07): later.** When every game has its Desktop layout (all 14 now have one, committed 2026-10-07; I have not taken the screenshots yet, they cost usage and I am saving it for the weekly reset), I send screenshots of all of them and you give your input. Nothing needed from you until then. Controller support: not yet; audio stays parked.

### 1. Apply for Google AdSense

**Your answer (2026-10-07): later.** Kept here so it is not forgotten.

**Why:** `planning/pwa-and-ads-setup.md`'s ad bar is already built and labeled everywhere on the site, wired up with placeholder IDs (`ca-pub-XXXXXXXXXXXXXXXX`) waiting for the real ones. The only blocker is the application itself, which needs your own Google account — I can't submit it for you.

**Steps:**
1. Confirm the hub is live over HTTPS at its real public GitHub Pages URL (it already should be — this is just a sanity check before applying).
2. Go to Google AdSense (google.com/adsense) and apply using that URL and your own Google account.
3. Approval can take anywhere from days to weeks — applying doesn't commit you to anything, so it's worth doing early even if you're not in a rush.
4. If AdSense asks you to add a verification snippet or an `ads.txt` file before/during review, hold off — send me the exact text they give you (see below) and I'll add it correctly rather than you hand-editing site files.

**What to tell me once you have it:**
- The `ca-pub-XXXXXXXXXXXXXXXX` client ID AdSense gives you.
- Your ad unit's slot ID.
- The exact `ads.txt` line, if AdSense gave you one.

I'll drop all of that into the ad bar and it goes live everywhere on the site at once, since it's a shared partial.

### 3. Which Warframe "meta" combos should the tracker pre-load?

**Why:** the build comparison ranks named combos by how close you are to finishing them. The Warframe Wiki names only one popular combo (the "177" Amp: Raplak Prism, Propa Scaffold, Certus Brace) and none for Zaws or Kitguns, and I will not invent community metas. You can already add your own in the tracker's "My combos" box.

**Your answer:** list any combos you want built in (name plus the parts), or say "just my own box is fine".

---

### Ch2. Chronicle: spot-check the weakest claims first: "Washington added 'so help me God'" (two of its three sources are opinion essays from one outlet)?

Open `games/chronicle/review.html` on the dev server and tell me keep, fix or drop.

### Ch3. Chronicle: spot-check the Sputnik to Apollo 11 cause link (no single source states the whole chain)?

Open `games/chronicle/review.html`; recommend keeping it labelled "contributing" unless you want it dropped.

### Ch4. Chronicle: spot-check the Lincoln-stayed-at-the-Wills-house claim (only NPS pages and one exhibition place him there)?

Tell me keep, fix or drop.

### Ch5. Chronicle: spot-check the Fort Sumter options claim (only two institutions) and the 1792 second-term decision (one Miller Center line plus one NCC line)?

Tell me keep, fix or drop for each.

### Ch6. Chronicle: are the 14 passage summaries in "Whose account?" fair and balanced in tone?

I wrote them from fetched page summaries, not whole pages, so a skim by you is the check.

### Sx1. Sound: please try the new generated sounds yourself (turn on "Sound effects made in code" in the hub Settings, then play Logic Gates, Hull Repair and Lighthouse) and tell me how they sound.

I cannot hear audio, so only you can judge it. Say "yes" if the tones are fine as they are. Otherwise say what to change in a comment: too loud or too quiet, too sharp or too dull, which cue (gate click, patch tone, bell, hum) or which game, and whether the Lighthouse hum should stay on by default.

### Dg3. Dream game: which main story do you want (three options are written in `planning/DREAM-GAME-PLAN.md`: 1 The Sleeping Caretaker, 2 The Ledger of the Cabin, 3 Why It Is Always Night)?

Recommended: Option 2 (the Ledger of the Cabin: a notebook you fill in, collecting and completing, no deadline), with Option 1's broken caretaker machine as a recurring character inside it. Say "2", another number, or a mix; keeper quests (TODO DG-4) wait on this.

### Se1. Google Search Console token (TODO Y-8, action for you)

The sitemap, robots file and per-game JSON-LD are done; the last step needs a verification token only you can get. Sign in to Google Search Console with your own account, add `https://noyvj.github.io/NoyvjGames/` as a property, choose the HTML-tag or HTML-file method and paste the token (or the file name) here. Say "later" to leave it parked.

### Q8_1b. Constellations: the game has the 88 official constellations (the Western list). Do you also want a few sky pictures from other cultures, such as Aboriginal Australian sky stories or Chinese constellations, added as optional charts with their sources?

Recommended: not yet. Those traditions belong to living communities, so they need careful, named sources and ideally their own wording, which is a bigger job. Say "yes" to add a few later, "no" to stay with the official 88. (Your Q8_2 note about wanting both hemispheres is covered: the atlas already has northern and southern skies.)

### Pb1. Pocket Bazaar: you asked to "move the tool buttons to the left side" (R4-PBMO-9); the audit built it as a Left-handed layout checkbox that reverses the dock so Hand over is on the left. Is that what you meant?

Recommended: yes. Say "no" and say what you wanted (for example moving all three buttons to a left-hand column).

### Pb2. Pocket Bazaar: should a rebound crate key (Settings, Controls) replace the 1 to 5 number keys?

Recommended: no. It currently adds to them, so the number keys always work.

### Pb3. Pocket Bazaar: you asked to "pull down the stall banner" to peek at the festival and regulars (R4-PBMO-5); it was built as pulling down the top row or the day message. Is that the banner you meant?

Recommended: yes. Say "no" and describe the banner.

### Hr1. Hull Repair: on a phone the old "Next room" button is hidden and replaced by the big "One more board" button (R4-HRMO-10). Is that OK, or should both show?

Recommended: yes, one button is enough. Say "no" to show both.

### Hr2. Hull Repair: the phone progress card (R4-HRMO-7) sits on the page behind the opening screen, not on the opening screen itself, because the shared opening screen has no slot for extra content. Is the in-page card acceptable?

Recommended: yes. Say "no" and I will add a slot to the shared opening screen.

### Lg1. Logic Gates: on Desktop, A, O and X now add an AND, OR or XOR chip, and Shift+N adds a NOT because plain N already means "Next level". Is Shift+N acceptable?

Recommended: yes. Say "no" and name the key you would rather use for NOT.

### Lg2. Logic Gates: clicking a truth-table row to set the switches counts as a switch flip in the stats. Is that fine?

Recommended: yes, it is still you flipping switches. Say "no" to leave those clicks out of the flips stat.

### Sm1. Station Medic: you asked for the condition sheet to open by pulling down (R4-SMMO-4); I built a fixed "Condition Sheet" tab that opens by tap or by dragging up, because a pull-down clashes with the browser's pull-to-refresh. Is the tab enough?

Recommended: yes. Say "no" and I will try a pull-down gesture anyway.

### Sm2. Station Medic: Z is now a free single-step undo on a keyboard (separate from Restore); should it also get a button on the phone layout?

Recommended: yes, a small Undo button next to Restore. Say "no" to keep it keyboard-only.

### Lh1. Lighthouse: the seven phone extras (lamp slider, wind crank, paper cards, letters drawer, battery saver, lamp rail, bigger Oil and Repair chips) are all off until switched on in Settings under "On a phone"; only the larger Oil and Repair chips show by default. Should any of them be on by default?

Recommended: no, keep them opt-in. Say "yes" and name which ones to turn on.

### Lh2. Lighthouse: is "Repair" meant as how sound the weakest part of the station is (0 to 100)?

Recommended: yes. Say "no" and say what number you wanted.

### Sm3. Station Medic: borrowing a supply (R4-SMMO-8) opens the shared centred confirm after you press and hold a shelf. Do you want a bottom sheet instead?

Recommended: no, the shared confirm is fine. Say "yes" for a bottom sheet.

### Rs1. Robot Script: the new bottom keypad lets you hold a step's letter and drag it to reorder, but repeat, until and if blocks still use their up and down arrow buttons. Should block steps also get the drag grip?

Recommended: yes, later. Say "no" to keep the arrows for blocks.

### Le1. Lexis: the transmission cards idea (R4-LEMO-1) asked for "tap to pause", but nothing in Lexis is timed so there is nothing to pause; is leaving it out fine?

Recommended: yes. Say "no" and say what you want paused.

### Le2. Lexis: should the Evidence board (R4-PX-19) get real message fragments on planets 2 and 3 and an actual identification step, as a new item?

Recommended: yes, later. Say "no" to leave it as the Pulse-planet pin board.

### Si1. Signal: the hold-to-aim bubble (R4-SIMO-1) shows the tile name and what is already known there; a real "ping preview" would be a free ping, which Signal never allows. Is the bubble enough?

Recommended: yes. Say "no" if you want a different kind of preview.

### He1. Herd: the Calm barn word (R4-HEMO-7) says "Healthy farm" only while methane pressure on income is under 25 percent, then "Methane is rising". Keep that, or always show "Healthy farm"?

Recommended: keep it, so the word stays honest. Say "always" to show the literal words every time.

### He2. Herd: the new thin top strip (R4-HEMO-2) replaces the shared funds, herd and methane bar on phones, and it leaves out herd size. Is that OK?

Recommended: yes. Say "no" to keep herd size in the strip.

### He3. Herd: "Pin as a goal" on a lever (R4-HEPC-3) only adds a visible Goal badge. Should a pinned goal also feed the pinned-stats strip or the report card?

Recommended: not yet. Say "yes" and name where.

### Th5. Thaw: Thaw has Invest buttons, not funding sliders, so the phone funds bar (R4-THMO-2) is an extra planning section that presses the Invest buttons; the normal Invest rows stay because investing cannot be undone. Is that fine?

Recommended: yes. Say "no" to hide the normal Invest rows on phones.

### Th6. Thaw: focus mode (R4-THMO-7) is opt-in with an "All" button as the default. Should phones start focused on Region A instead?

Recommended: no, keep "All" as the default. Say "yes" to start focused on Region A.

### Th7. Thaw: the four new per-device phone switches are not part of the exported settings code. Should they be added to it?

Recommended: not yet. Say "yes" to add them.

### La1. Herd, Canopy, SOL and Grid: should each get three play styles (Herd: Techie, Naturalist, Dealmaker; Canopy: Ranger, Naturalist, Planner; SOL: Hands-on miner, Trade baron, Hands-off overseer; Grid: Engineer, Economist, Campaigner) with their own goal list and badge, so every style can reach 100 percent? (R4-PH-5, R4-PC-6, R4-PS-3, R4-PG-5)

Recommended: yes, as goal lists only. Each style gets about six goals built from things the game already counts, all three lists are visible at once and can be done in any order, no style locks anything or changes a balance number, and in Grid a style only changes which numbers the dashboard highlights (no perks). Say yes and the local AI can build all four.

### La2. Canopy and Tide: should each get an extra space scenario (Canopy's Dome Garden on Mars with thin soil and hardy invented wildlife, R4-PC-4; Tide's Europa dome harbour under an icy moon, R4-PI-16)?

Recommended: yes, as a separate mode on the first screen from the start (not unlocked after finishing), about five levels each, with the main game untouched. Say yes and the local AI can write the level data and numbers for both; say "later" to keep them parked.

### La3. Le Champ de Mots: you said coins are cosmetic only and come from watering only (FY-46: "yes, cosmetic only"). The shop idea L-1 would add coins from mastered plots, a bigger can that reminds neighbours, decor and a market stall. Keep the earlier decision, or change it?

Recommended: keep it, plus one addition. Say "keep" and the local AI adds cosmetic decor to the Farm shop, bought with the same watering coins, and nothing else changes (no new coin source, the can stays cosmetic, nothing touches review timing). Say "change" and name which of the four parts you now want.

### La4. Le Champ de Mots: the visiting student (R4-PN-3) needs a meaning for "teaching". May it be a small pen pal who is shown a word, where you pick which of three hints to give (a picture, an example sentence, the English)?

Recommended: yes. It counts as one practice answer in the ledger so it visibly raises the practice score; the pen pal never fails and there is no penalty for a weak hint. Say yes and the local AI can build it; say "no" and describe what teaching should be.

### La5. Le Champ de Mots: the French skill tree (R4-PN-19) needs its nodes and levels. May it follow the four areas the arcade games already cover (Greetings and basics, Verbs, Boutique, Cafe), with each node levelling at 5, 15 and 30 grown plots in that area, nothing spent and nothing refunded?

Recommended: yes. The tree only reads the farm, so every plot you grow visibly counts and a wrong spend is impossible. Say yes and the local AI can build it.

### La6. Le Champ de Mots: the portrait minigame lobby (R4-CHMO-7) wants "your best score on each", but only Blitz and Sprint keep a best, and only until the page reloads. Should the bests be saved?

Recommended: yes, save one best per minigame (a small new save field that defaults to empty, so old saves load unchanged). Say "no" to show only this visit's bests.

### La7. Aftermath: the skill map already pans and zooms (E-2), with Ctrl+wheel to zoom so the page can still scroll. For the hover card on each skill (R4-AFPC-1), keep Ctrl+wheel, and show the skill's earned rank instead of "which runs used it" (the game keeps ranks by use, not a list of runs)?

Recommended: yes to both. Say yes and the local AI adds the hover card (cost, effect, rank) and the item is done; say "plain wheel" if you want the wheel alone to zoom.

### La8. Chronicle: three new draft sets (History of Computing with 8 claims, Ancient Greece with 7, History of Food with 3) have three sources per claim. Once they are built, will you skim them on `games/chronicle/review.html` and say which count as reviewed?

Recommended: yes. Mark Computing and Greece reviewed if the wording looks fair, and keep Food as a draft until it has more than 3 events. Say "later" to leave all three as drafts.

### La9. Chronicle: the archivist (R4-CLP-3) needs a look, with no generated images allowed. May it be a small lamp-like figure drawn in code (no face), who says one short line per shelf, and restoring a shelf means putting about five torn scraps back in place?

Recommended: yes. The lamp brightens as the shelf comes back, nothing is timed, and a wrong scrap simply slides back. Say yes and the local AI can build it; say "no" and describe the look you want.

### La10. Chronicle: the world mosaic (R4-CLP-8) gets one tile for every puzzle you solve in any set. Your note asked for several era maps and a one-location timeline map. May the first version be one world mosaic of simple coloured shapes (no borders, no country names), with era maps and the timeline map added later as separate items?

Recommended: yes. Say yes and the local AI can build the first mosaic; era maps and the location timeline then wait for your later answer.

### La11. Chronicle: the branching "letters from a witness" story (R4-CLP-12) needs one real documented person. May it be Samuel Pepys during the Great Fire of London (2 to 6 September 1666): five short letters, a choice in each, then a reveal of what his diary says he actually did?

Recommended: yes (his diary is a primary source, the story is calm and a little funny). Say yes and the work moves to Claude to find three sources per claim; or name another person.

### La12. Chronicle: the diplomat's seat (R4-CLP-22) needs one treaty with documented delegations. May it be the Treaty of Tordesillas (1494): you read the Spanish and then the Portuguese position before seeing what was signed, with a note on who was not in the room?

Recommended: yes (only two delegations, so it stays short). Say yes and the work moves to Claude to source it; or name another treaty.

### La13. Drift: the arrival mix (R4-DR-1) wants a bar showing who arrived. May it be three groups (households with children, single adults, older adults) that each need a different service (schools and childcare, housing, health), with the split fixed per round and the total arrivals unchanged?

Recommended: yes. Keeping the total unchanged leaves the existing balance numbers alone, and groups stay counts, never people. Say yes and the local AI can build it.

### La14. Drift: modular versus permanent housing (R4-DR-5). May modular units cost about 60 percent as much and add capacity at once but cost about 50 percent more to run each round, while permanent homes cost full price, finish two rounds later and are cheap to keep?

Recommended: yes, as a choice on the housing button with those starting numbers (the local AI tunes them with the balance tests). Say yes, or give your own numbers.

### La15. Drift: the neighbour book (R4-PD-1) is a card per housed household with an invented note, which breaks Drift's rule: "Institutions, not individuals ... Never individual migrant stories or named people." Keep the rule, or change it?

Recommended: keep the rule. Say "keep" and the local AI builds the same collector's book as a "service book": one page per kind of service you build (clinic, school, language class, bus line) with a short factual note. Say "change" only if you want invented household cards, which lifts the rule.

### La16. Drift: Arkship mode (R4-PD-4) retells the game as a space habitat taking in refugees from a failing colony. Could it be one more skin (words and colours swapped, ring-ships in place of towns, same rules) rather than a new mode?

Recommended: yes, as a skin using the existing skin switch, with no new art beyond colours. Say "later" to park it.

### La17. Drift: the region charter (R4-PD-5) says "every five-round council goal", but Drift has no five-round goal (the Mayor's Council offers one pick every 10 rounds). May it be one charter clause for each council program you adopt (nine at most)?

Recommended: yes. Say yes and the local AI can build it as a four-step chain.

### La18. Drift: a building search (R4-DRPC-5) as Ctrl+F would replace the browser's own find, and buildings have no names. May it be a small Find box, opened with the / key, that highlights buildings by kind (housing, services, infrastructure) instead?

Recommended: yes, and leave Ctrl+F alone. Say yes and the local AI can build it.

### La19. Herd: the three-round lever planner (R4-HEPC-7) is already largely built as the what-if planner, which looks 5 or 10 rounds ahead. Keep it as built, or add a 3-round view as well?

Recommended: add the 3-round view (a one-line change to `PLAN_HORIZONS = (3, 5, 10)`) and tick the item done. Say "keep" to tick it done with 5 and 10 only.

### La20. Canopy: the river (R4-CA-1) needs a shape. May it be a fixed river down one column, only on a new River level set, where plots beside it grow about 20 percent faster and clearing a plot upstream slows the plots directly downstream by about 10 percent until it is replanted?

Recommended: yes, River levels only, so the numbers the main game's tests pin never change. Say yes and the local AI can build it; or give your own percentages.

### La21. Canopy: access roads (R4-CA-2). May a road be a fixed line of tiles on a new Roads level set, where clearing a plot touching the road costs about 20 percent less but each road tile lowers the wildlife count on both sides a little, shown with a visible split line?

Recommended: yes, new Roads levels only. Say yes and the local AI can build it.

### La22. Canopy: natural regrowth (R4-CA-3) lets a bare plot beside three or more mature plots recover for free. Should it be an opt-in Settings switch, off by default, and never active in the Pacifist and Scorched challenges or the replant contract?

Recommended: yes, opt-in, with drifting seed specks that stop under Reduce Motion. Say "on by default" if you want it always on.

### La23. Canopy: wildlife rescue (R4-PC-1). May clearing a plot show a displaced animal that you tap and then drop onto any mature plot, with a shelter badge the first time each kind is rescued, an animal that is never moved simply waiting, and nothing timed?

Recommended: yes. Say yes and the local AI can build it.

### La24. Canopy: forest fog (R4-PC-7). May it be an opt-in Settings switch (off by default) that hides unexplored plots in pale mist, clears them when you tend a neighbour, and never blocks any action?

Recommended: yes, opt-in and still under Reduce Motion. Say yes and the local AI can build it.

### La25. Canopy: farmer partners (R4-PC-12). May there be three invented neighbouring farmers, each a card with a request (for example a tree line on their north edge) and a one-sentence reason from their side, planned on a practice board with a plain checklist and nothing penalised?

Recommended: yes. Say yes and the local AI can build it.

### La26. Canopy: the bed-time mode (R4-CAMO-7) hides numbers except one. Which one: "Mature trees" (for example 12 of 36)? It would reuse the existing dim and calm settings without editing the shared files.

Recommended: Mature trees. Say yes, or name a different number.

### La27. Signal: "hold Space" for the ping reach rings (R4-SIPC-5) clashes with Space, which already marks a tile. Which key instead? (Held Shift is already the distance ruler on the Desktop page.)

Recommended: G, for "guide". Say yes and the local AI can build it with the rings drawn only from your own pings.

### La28. Tide: should the three scenario speeds really follow the IPCC numbers (R4-TI-11)? Changing them would move the game's pinned balance tests; the planned note beside the picker already shows the IPCC figures (0.44, 0.56 and 0.77 m by 2100) with their source.

Recommended: no, keep the game's own simpler speeds and let the note show the real numbers. Say "change" to move the game's numbers too.

### La29. Tide: rescue boats (R4-PI-2). May storm seasons show one to three boats as dots, where you choose which of two gates to open for each, a wrong choice just leaves the boat waiting in harbour until the next season (nobody lost), and Restore stays available?

Recommended: yes. Say yes and the local AI can build it.

### La30. Tide: harbour mysteries (R4-PI-10). May there be six short cases, each with three tide-log entries and three possible causes to name, where every cause is a real natural thing with a named source and a wrong guess just lets you try again?

Recommended: yes. Say yes and the local AI can build it.

### La31. Tide: wreck sites (R4-PI-22) need a "survey". May you spend one free survey per season on a tile to reveal a site, with six invented sites of three salvage items each (no real shipwrecks)?

Recommended: yes. Say yes and the local AI can build it.

### La32. Tide: chart-reading puzzles (R4-PI-24). May there be eight hand-made puzzles where two bearings and a depth reading let you tap where the lighthouse stands, with a generous tolerance and a check button?

Recommended: yes. Say yes and the local AI can build it.

### La33. Tide: the boatyard (R4-PI-25). May it be six old boats, each needing four parts sorted from a shelf by a plain rule, each joining a shelf with the last captain's quiet log, nothing timed?

Recommended: yes. Say yes and the local AI can build it.

### La34. SOL: the signature buildings (R4-SO-3), one per world with a special rule. May each rule only change that world's own numbers (about plus 10 percent on one thing there), so the core simulation and other worlds never move?

Recommended: yes, in-world effects only (the Venus example about neighbouring ecology is skipped). Say yes and the local AI can build all eight; or say "cross-world" to allow effects between worlds.

### La35. SOL: alternate openings (R4-SO-11). May there be one first, a Mars start chosen from the new-game screen from day one (not unlocked later), with a fixed starting kit and its own early unlock order, and Venus later?

Recommended: yes, Mars only first. Say yes and the local AI can build it.

### La36. SOL: rescue worlds (R4-SO-13). May there be six hand-made puzzle scenarios (for example "Ceres starts with no water and 5 percent ecology; bring it above 50 percent with six buildings"), with no timer and a free retry?

Recommended: yes, six first. Say yes and the local AI can write them; Claude checks each is solvable.

### La37. SOL: the express opening (R4-PS-9). May it be a separate Quick start option on the new-game screen that teaches the first world by playing and opens the second system within five minutes, with the normal opening and its numbers untouched?

Recommended: yes. Say yes and the local AI can build it.

### La38. Grid: the dispatch puzzle (GC-3). May it be an optional step each round, with tap-to-order instead of dragging (tap a plant to place it next in the queue), where cheapest-first earns full revenue and any other order loses up to 10 percent of it, and a Skip button?

Recommended: yes. Say yes and the local AI can build it.

### La39. Grid: a siting map (GC-7) and transmission lines (R4-GR-3) both need places for plants. May one small 6 by 6 tile map serve both (tiles of ridge, desert, river and plain, the city on one tile), where a plant more than 3 tiles from the city delivers 80 percent unless you pay for a line, and coal or nuclear beside the city costs a little revenue?

Recommended: yes, as an opt-in Map mode at the start of a run, default off, so existing balance tests hold. Say yes and the local AI can build it.

### La40. Grid: neighbour trading (GC-22) has no "negotiated price" rule. May the neighbour instead offer one fixed take-it-or-leave-it price each round (no haggling), with the interconnector limit at 2 units?

Recommended: yes (no luck, no haggling). Say yes and the local AI can build it.

### La41. Grid: the winter and summer split (R4-GR-4) changes every demand and revenue test. May it be an opt-in Two seasons mode (default off) with the normal round untouched?

Recommended: yes. Say yes and the local AI can build it.

### La42. Grid: fault tracing (R4-PG-17). May a flicker show three dials (frequency, voltage, load) and three possible causes, where naming the right one adds about 5 percent revenue for that round and a wrong guess costs nothing?

Recommended: yes. Say yes and the local AI can build it.

### La43. Grid: equippable parts (R4-PG-20). May each plant have three slots and 12 parts in all, each unlocked by a fixed milestone (no random drops) and each changing one number by about 5 percent?

Recommended: yes. Say yes and the local AI can build it.

### La44. Grid: the Continental Grid endgame (R4-PG-22). May it open after you finish a normal run, run four regions one after another, and show numbers in billions with a plain "bn" label and no new mechanics beyond sums?

Recommended: yes. Say yes and the local AI can build it.

### La45. Grid: the parts catalogue (R4-PG-14) asked for 40 components, but the open EIA data covers only 17 real plant types that fit the game. Keep the 17 as the full catalogue, or name another source for the rest?

Recommended: keep the 17 and call that the catalogue. Say "NREL" to also look at NREL's technology baseline later.

### La46. Continuum: the relic hunt (R4-PO-2) needs 64 relics (eight per era). May they be invented objects of the settlement (a clay seed jar, a signal lamp) with a one-sentence description and no real-world claim, found by tapping a glowing object in that era's Look Back view, with a "relics left: n" counter so nothing is hidden?

Recommended: yes. Say yes and the local AI can draft the 64; Claude reads them over.

### La47. Continuum: the low-power 2D view (R4-COMO-6). Is the existing 2D diorama (plus the 2D/3D button and lite mode) enough, or do you want a new flat map with a tap sheet per building?

Recommended: the existing diorama is enough. Say yes and the item is ticked done; say "new map" to build the flat map.

### La48. Thaw: the Ice Core Archive (R4-PT-4) needs an unlock rule. May core number n open when your furthest round in any region reaches n + 1, so a long game (about 50 rounds) opens all 30?

Recommended: yes. It reads the existing archive progress, so nothing new is saved. Say yes, or give your own rule.

### La49. Thaw: the temperature chart legend (R4-THPC-2). There is no single chart to put a legend on, as each region draws its own graph. May the legend simply show and hide the four region cards instead of building a new combined chart?

Recommended: yes. Say "new chart" if you want one combined chart.

### La50. Thaw: graph zoom (R4-THPC-6). A bare mouse wheel would trap page scrolling. May zoom be Ctrl+wheel plus two buttons, "Last 10" and "All", with the plain wheel left alone?

Recommended: yes, the same rule as Aftermath's map. Say yes and the local AI can build it.

### La51. Lexis: the broken guardian (R4-PX-2), a quiet tragic log, needs a shape. May it be about eight short log entries from a damaged robot guarding the Pulse planet's beacon, optional to read, barely speaking but showing feeling, never explaining any sign?

Recommended: yes. Say yes and the local AI can draft it for you to read over.

### La52. Lexis: crew choices (R4-PX-3). May there be one short talk after each planet with two or three replies, from a captain who makes real mistakes, where the replies never change a puzzle, only what the crew says and a line in the crew log?

Recommended: yes, nothing missable. Say yes and the local AI can build it.

### La53. Lexis: your note on the branching voyage (R4-PX-7) says you reach every planet in the end, each opening with the same message in a different language. May planets 2 and 3 open in any order after the first (each marked Gentle, Medium or Hard), with the crew reacting differently to your order?

Recommended: yes. Say yes and the local AI can redesign the unlock order.
