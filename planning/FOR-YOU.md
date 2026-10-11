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

### Eh1. Evidence Hunt: restless rooms mark themselves the moment you step in; should finding them take a reading instead (harder)?

Recommended: keep it simple as is (they mark themselves). Say "yes" to go with that.

### Eh2. Evidence Hunt: the client's account gives a spirit's behaviours for free; should you infer them from room signs instead?

Recommended: keep the free account, and add inferring from room signs as an optional harder way later. Say "yes" to go with that.

### Eh3. Evidence Hunt: a bag holds 3 tools (4 in the big houses), which forces a choice; do you prefer taking everything?

Recommended: keep the limited bag, since the choice is part of the puzzle. Say "yes" to go with that.

### Eh4. Evidence Hunt: a second trip back to the van costs 1; do you prefer it free?

Recommended: make it free, since you dislike costs that feel like punishment. Say "yes" to go with that.

### Eh5. Evidence Hunt: keep the spirit kind names and the warm endings as written?

Recommended: keep them; say "no" and tell me which to change. Say "yes" to go with that.

### Zl1. Language: the new language chooser (English, Spanish, French) changes the shared game controls in every game, including Le Champ de Mots; should I limit it to the climate games and leave Le Champ de Mots in English only?

Recommended: yes, leave Le Champ de Mots in English, since it teaches French and mixing languages in its controls would be confusing. Say "yes" to go with that.

### Zl2. Language: the Spanish and French texts are machine-assisted and not yet proof-read; do you want to proof-read them yourself (a list of all 106 strings), or should they stay hidden behind the chooser until someone does?

Recommended: leave the chooser available but labelled "beta" until you have looked at the French at least.

### Sx1. Sound: please try the new generated sounds yourself (turn on "Sound effects made in code" in the hub Settings, then play Logic Gates, Hull Repair and Lighthouse) and tell me how they sound.

I cannot hear audio, so only you can judge it. Say "yes" if the tones are fine as they are. Otherwise say what to change in a comment: too loud or too quiet, too sharp or too dull, which cue (gate click, patch tone, bell, hum) or which game, and whether the Lighthouse hum should stay on by default.

### Q4_1. Reaction Bench: should the table cover only the 36 bench elements for 100%, or all 118 with the unused ones also given a use card?

Default: 36, the rest faint and optional. Say "yes" to go with that.

### Q4_2. Reaction Bench: is a free sandbox bench (type any formulas and have the ledger check them) wanted after chapter 5?

Default: no. Say "yes" to go with that.

### Q5_1. Rule Finder: should a wrong name ever show the hidden rule's words after several near misses?

Default: no, only the Answer rung does. Say "yes" to go with that.

### Q5_2. Rule Finder: add a free "write your own rule and test a friend" mode?

Default: no. Say "yes" to go with that.

### Q6_1. Slingshot: is 2D circular-orbit "simple but real" the right level, or do you want elliptical orbits for the inner planets?

Default: circular, said plainly on About. Say "yes" to go with that.

### Q6_2. Slingshot: reached-with-any-fuel counts as 100%; is "Thrifty" only a bonus?

Default: yes, bonus only. Say "yes" to go with that.

### Q7_1. Teach the Machine: is a small decision tree the right "tiny classifier", or do you want a nearest-neighbour model Pip can show as "looks most like these"?

Default: decision tree. Say "yes" to go with that.

### Q7_2. Teach the Machine: should the Fair Treatment shelf stay inside the game or become an optional extra shelf?

Default: inside, switchable off in settings. Say "yes" to go with that.

### Q8_1. Constellations: western (IAU) constellations only, or also a few figures from other sky traditions with their sources?

Default: IAU only for now. Say "yes" to go with that.

### Q8_2. Constellations: should the atlas show the real sky for the player's hemisphere?

Default: no, one fixed atlas. Say "yes" to go with that.

### Q9_1. Zero-G Shift: is a free Step back fine in a move-by-move puzzle (it is not a story choice)?

Default: yes, with Restart always free too. Say "yes" to go with that.

### Q9_2. Zero-G Shift: should the player also slide when they push a crate (recoil)?

Default: no, the player stops. Say "yes" to go with that.

### Q10_1. Mirror Lab: are decoy "must stay dark" sensors welcome, or should every sensor simply need lighting?

Default: decoys only in chapter 4 and after. Say "yes" to go with that.

### Q11_1. Radio Decode: should Wren's thread be a real story with an ending, or only loose log entries?

Default: loose threads per band with a short quiet ending line in the last message. Say "yes" to go with that.

### Q12_1. Picture Grid: mono pictures with a final tint, or true multi-colour nonograms for the last gallery?

Default: mono with tint (clearer, easier to read on dark). Say "yes" to go with that.

### Q12_2. Picture Grid: should Check mistakes be on by default for the first gallery?

Default: off, offered once in the tutorial. Say "yes" to go with that.

### Q14_1. Robot Repair Shop: should a friend's visit also unlock a tiny optional favour (like a free extra probe type), or stay purely a keepsake?

Default: a few gifts are tools, the rest keepsakes. Say "yes" to go with that.

### Q15_1. Fog Rescue: should this stay a standalone game or be set aside to become part of the foggy-forest dream game later?

Default: standalone now, reusable later. Say "yes" to go with that.

### Q16_1. Water Works: should every valley have a Fair share plan (everyone Content), or should a few late valleys be honest "no perfect plan" cases where Common ground is the best?

Default: a Fair share plan always exists, but the late ones are tight. Say "yes" to go with that.

### Q16_2. Water Works: should the voices be able to disagree with each other in text (a short exchange) or only react to the plan?

Default: react to the plan only. Say "yes" to go with that.

### Q17_1. Derelict Garden: should plants ever show a passive visual change over real time (a slow sway), or stay still unless you act?

Default: gentle sway only, toggleable, never progress. Say "yes" to go with that.

### Q17_2. Derelict Garden: is a free "decorate" mode (move rocks and benches for looks only) wanted after a section is restored?

Default: no, to avoid perfectionism. Say "yes" to go with that.

### Q18_1. Memory Archivist: is a 40-memory story about a flawed caretaker AI the right tone, or should HALCY be gentler with less of a mistake behind it?

Default: a small, forgivable mistake, never a disaster. Say "yes" to go with that.

### Q18_2. Memory Archivist: should Check show how many scraps are right, or only Right or Not yet?

Default: the number. Say "yes" to go with that.

### Q19_1. Food Bank: should the diet and allergy rules use real-world categories (nut allergy, halal, vegetarian) or invented ones?

Default: a small set of real categories, handled respectfully. Say "yes" to go with that.

### Q19_2. Food Bank: is a "what would you change" voice from volunteers or families after each week wanted?

Default: yes, one short line per family. Say "yes" to go with that.

### Q20_1. Housing Board: should one late chapter include a round with no Common Ground (an honest tension) where Settlement is the best possible?

Default: no, every round has a Settlement and most have Common Ground. Say "yes" to go with that.

### Q20_2. Housing Board: is a policy-flavoured country setting (UK, US, neutral invented) preferred?

Default: a neutral invented town. Say "yes" to go with that.

### Q21_1. Anomaly Catalogue: should a few late rooms be gently unsettling (a figure that is there only in the Now frame) or stay strictly odd objects?

Default: odd objects only, nothing that harms or chases. Say "yes" to go with that.

### Q21_2. Anomaly Catalogue: is a hold-to-zoom lens enough for accessibility, or should every room offer a list-view of objects too?

Default: add the list view as the screen-reader path. Say "yes" to go with that.

### Q22_1. Loadout Lab: should finding every pass of a challenge count towards 100%, or stay a bonus?

Default: bonus only, so 100% stays easy. Say "yes" to go with that.

### Q22_2. Loadout Lab: should the Broken Build ever be nerfed or banned from a "fair" challenge variant?

Default: no, Broken is always allowed and celebrated. Say "yes" to go with that.

### Q23_1. Glitch Hunter: should the tester's log notes be dry and dark in voice, or plainer?

Default: dry and short, behind the Story toggle. Say "yes" to go with that.

### Q23_2. Glitch Hunter: should "decoy" rooms (no glitch to find) exist at all, or does every room hide one?

Default: 3 decoys across the game. Say "yes" to go with that.

### Q24_1. Space Museum: should the museum percentage count only the museum's own finds and rooms (so 100% never needs other games), with site objects a separate bonus shelf?

Default: yes. Say "yes" to go with that.

### Q24_2. Space Museum: should an object name be taken straight from the achievement title, or should I hand-write a nicer object for every achievement (about 300 short lines)?

Default: titles with about 60 hand-written overrides. Say "yes" to go with that.

### Q24_3. Space Museum: should visitors see someone else's museum (an invite-link snapshot, like Shared Station)?

Default: no, that stays in Shared Station. Say "yes" to go with that.

### Q26_1. The Quiet Program: wick is steady and kind rather than sad; its decline is gradual forgetting. Is that the right tragic level, or should it be sadder or lighter?

Default: as written. Say "yes" to go with that.

### Q26_2. The Quiet Program: should Wick's apologies and thanks be spoken in short lines for every Evening, or only on the first and last of each chapter?

Default: short every Evening, behind the Story toggle. Say "yes" to go with that.

### Q27_1. Night Cameras: should the game mark contradictions between your notes and the footage for you (a setting), on or off by default?

Default: on. Say "yes" to go with that.

### Q27_2. Night Cameras: is a mundane or gently sad explanation for every case right, or should a few cases stay unexplained (an anomaly note, like Lighthouse's optional layer)?

Default: every case explained. Say "yes" to go with that.

### Q28_1. Three Sides of the Story: are a fruit farmer, a water engineer and a clinic nurse the right three viewpoints for a water shortage, or would you swap one (for example a shopkeeper or a council member)?

Default: as written. Say "yes" to go with that.

### Q28_2. Three Sides of the Story: should the Council meeting be a fourth playable thread, or just an ending screen that summarises what the three sides chose?

Default: a short playable thread. Say "yes" to go with that.

### Q28_3. Three Sides of the Story: should fact cards be on by default or switched on in Settings?

Default: on, with a setting to hide. Say "yes" to go with that.

### Q30_1. Terminal Logs: buttons only, or also a real typing line for commands (with autocomplete) on desktop?

Default: both, typing optional. Say "yes" to go with that.

### Q30_2. Terminal Logs: should the ship's daemon speak (short lines in its own log voice) or should there be no voice at all, only files?

Default: short daemon lines, behind the Story toggle. Say "yes" to go with that.

### Q31_1. Keep Talking: is "no server, each device checks its own answer" fine, knowing a determined cheat could peek?

Default: yes (no leaderboards, so nothing to cheat). Say "yes" to go with that.

### Q31_2. Keep Talking: should a friend job be started from a short code you can read aloud as well as an invite link?

Default: both (code is the seed). Say "yes" to go with that.

### Q32_1. Shared Station: shared Station and Space Museum both celebrate what you have done on the site (rooms lit versus objects placed). Keep both as separate games, or merge them?

Default: keep both; the station shows status, the museum shows arranging. Say "yes" to go with that.

### Q32_2. Shared Station: should visitors be able to leave one of 12 fixed "waves", or no gifts at all in v1?

Default: waves in, free text never. Say "yes" to go with that.

### Q32_3. Shared Station: should the Station Card include a display name, or only the lit rooms?

Default: a name from a short closed word list. Say "yes" to go with that.

### Q33_1. Saboteur Puzzle: should each saboteur have a small sympathetic reason shown after the case (a debt, a fear), or should the reason stay unknown?

Default: a small reason shown. Say "yes" to go with that.

### Q33_2. Saboteur Puzzle: should the contradiction check be on by default, with a setting to turn it off for a harder game?

Default: on. Say "yes" to go with that.

### Q34_1. Repair the Ship's Code: should phones get the tap-a-token editor only, or a normal keyboard editor too?

Default: both, token mode first on small screens. Say "yes" to go with that.

### Q35_1. Query the Archive: should a "free query" practice desk (no slip, just explore the Archive) be added after the last slip?

Default: yes, a read-only sandbox that still counts clauses used toward the Drawer. Say "yes" to go with that.

### Q35_2. Query the Archive: clause chips for beginners can be switched off for a typed-only game. Default: chips on until chapter 3, then optional.

Recommended: the default written in the plan. Say "yes" to go with that.

### Q36_1. Pattern Match: the game uses its own matcher for safety, which supports a clearly listed subset of regular expressions. Is that fine, or should it use the full Python engine with a hard cap on pattern length?

Default: own matcher. Say "yes" to go with that.

### Q36_2. Pattern Match: par marks reward the shortest pattern. Keep them as an optional small mark, or drop them to keep it pure puzzle?

Default: keep, optional. Say "yes" to go with that.

### Q37_1. Binary Bakery: should helper displays (running sum, binary string) be on by default, with a setting to hide them for a harder game?

Default: on. Say "yes" to go with that.

### Q37_2. Binary Bakery: should negative numbers (two's complement) be a late optional chapter?

Default: no, kept out. Say "yes" to go with that.

### Q38_1. Orbit Maths: should the physics stay at ratios, speeds and fuel with given numbers (no formulas to memorise), or include the real rocket equation with logarithms in the last stage?

Default: simple steps with given numbers; no logarithms. Say "yes" to go with that.

### Q38_2. Orbit Maths: should a built-in calculator be allowed on every sheet, or only on the last two stages?

Default: every sheet. Say "yes" to go with that.

### Q39_1. Circuit Playground: should the board stay at 24 parts (works well on phones), or allow bigger boards on desktop?

Default: 24 on every device. Say "yes" to go with that.

### Q39_2. Circuit Playground: should AC (a swinging source) ever be added, or keep everything DC?

Default: DC only. Say "yes" to go with that.

### Q40_1. AI Mistakes: should cases stay in toy domains (animals, foods, weather) with real-world incidents only in the Field Guide notes, or should some cases use a realistic setting (for example a job-application screener)?

Default: toy domains only. Say "yes" to go with that.

### Q40_2. AI Mistakes: should the Fix step (change one example and re-run Pip) be on from the start or appear only after the first chapter?

Default: from the start. Say "yes" to go with that.

### Q41_1. Material Match: which named source should be the main one for the numbers?

Default: a public engineering reference (Engineering ToolBox) cross-checked against the Wikipedia reference values. Say "yes" to go with that.

### Q41_2. Material Match: should the cost word (cheap to dear) be included, given it varies by place and year?

Default: yes as a relative word with a date, never a price. Say "yes" to go with that.

### Lo1. Loop FY-5: you said yes to an opt-in "supply chain disruption" random event, but Loop now has opt-in market shocks on a fixed schedule (announced one cycle early, no randomness); should the fixed shocks count as that item?

Recommended: yes, the fixed shocks are the supply-chain disruption, since you dislike random luck. Say "yes" to go with that, "no" if you still want a random version.

