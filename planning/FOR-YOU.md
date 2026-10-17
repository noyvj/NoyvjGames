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
