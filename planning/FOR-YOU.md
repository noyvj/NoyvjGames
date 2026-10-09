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

### Li4. Lighthouse: it shipped with 21 achievements (11 for keeping the light, 10 story ones, six of them hidden until solved) instead of the plan's 16; should I cut it to 16?

Recommended: keep 21, since you like reachable 100% and every one is earnable in a Quiet year.

### Li5. Lighthouse: a night lasts about 3 minutes at normal speed (one tick per 4 seconds); is that the right pace, or should it be faster or slower?

Recommended: keep 3 minutes, with 2x and 4x speeds and pause already available.

### Fs2. FREN152: the slides folder holds "FREN152 LECTURE 13 (2024)", a 2024 lecture 13 although week 13 has not happened this semester; should I use it as a preview of week 13 or ignore it?

Recommended: ignore it until your 2026 week 13 arrives, since the 2024 content may differ from this year's.

### Lg1. Logic Gates: it ships with a small story (a station called Meridian Relay and a flawed previous engineer called Vale who left notes); keep it, or make the game pure puzzle?

Recommended: keep it (it is switchable in settings, and the engineer is not an all-good hero). Say "yes" to keep it.

### Lg2. Logic Gates: should a level open as soon as the chips it needs are unlocked (so the order is partly free), or strictly one after another?

Recommended: chip-based (the current build), since you like objectives without a strict order. Say "yes" to keep it.

### Lg3. Logic Gates: keep "par" (fewest chips) as an optional second mark on each level?

Recommended: yes, kept generous and optional, never needed to progress.

### Rs1. Robot Script: should the free sandbox open earlier than the end of the last chapter (for example after chapter 3)?

Recommended: open it after chapter 3 so there is somewhere to experiment sooner. Say "yes" to go with that.

### Rs2. Robot Script: is the companion drone Scrap's tone right (quiet, dry, slightly sulky salvage drone, not a cheerful hero)?

Recommended: yes, keep it quiet and a little sulky. Say "yes" to go with that.

### Rs3. Robot Script: is the medal rule right (gold for the reference length, silver for up to a third more, bronze for any clear)?

Recommended: yes, as written. Say "yes" to go with that.

### Rs4. Robot Script: should chapter 1 stay straight corridors with no turning, or bring turning in from room 4?

Recommended: bring turning in from room 4 so chapter 1 teaches more. Say "yes" to go with that.

### Rs5. Robot Script: chapters currently open after 5 of 7 rooms are cleared; do you prefer every room open from the start?

Recommended: open every room from the start, since you like objectives without a strict order. Say "yes" to go with that.

### Dg1. Dream game: which six keepers (people who run buildings) should be there at launch?

My suggestion, since the first is fixed by your answer: the builder (first, wood quest), a woodcutter, a miner, a librarian, a workshop tinkerer and a healer. Say "yes" to go with that, or name your own.

### Dg2. Dream game: should I propose three options for the main story (one paragraph each) for you to pick from, or do you want to describe the idea first?

Recommended: I propose three options. Say "yes" for that, or "no" and describe it in a comment.

### Ap1. App form: if the site gets an installable app, should I look at desktop first or phone first?

Recommended: desktop first (a small desktop wrapper), since you mostly play on PC at night.

### Ap2. App form: may any game be playable only in the app (flagged "App only" on the hub), or should every game stay on the web?

Recommended: keep every game on the web for now; flag a game "best in the app" later if it needs it (the dream game, maybe).

### Ap3. App form: shall I try a small desktop-app experiment with one existing game to see how much work it is?

Recommended: yes, later, after the current game batches finish.

