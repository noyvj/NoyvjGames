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

### Pf1. From your survey: what feels relaxed in a game? You asked for examples, so pick any: (a) a game you can pause any time, (b) steady progress that can never be lost, (c) a collection quietly filling in, (d) a routine you know by heart, (e) something else?

Recommend: tell me which letters, and I lean the calm modes on those.

### Pf4. From your survey: build one new game as a Lifeline-style choose-your-own-adventure with many branching paths (sci-fi, dark tone, optional reading, a main character who makes mistakes)?

Recommend: yes, as a small text game about a stranded ship crew, built after Chronicle.

### Pf5. From your dream game (a dark foggy forest city builder where each building's keeper has friendship sidequests and gifting, each building has its own puzzle with permanent upgrades, plus a mining mode with a huge skill tree and bunker sections that specialise buildings): write a plan for it, starting with only the city-and-resources loop and the fog look?

Recommend: later, as a plan first (a planning file), with the first-person helping nodes, the mining skill tree and the per-building puzzles parked.

### Pf6. From your survey: add new games on coding, maths or chemistry (for example a logic-gate puzzle game, a chemistry reactions puzzle)?

Recommend: yes, one coding or logic-circuit puzzle game first (computers and puzzles are two of your favourites).

### Pf7. From your tycoon note: show three "get X to level N to unlock Z" goals at all times in the idle and tycoon games (SOL, Trade Empire, Continuum, Loop), as one shared panel?

Recommend: yes, built once in shared/ and fed by each game's own goals.

### Pf8. From your survey: you were unsure the site can hold real-time input. It can (SOL already ticks every 100 ms and the Champ minigames run every second). Want a fast timed reaction game as one of the next new games?

Recommend: yes, one small optional one, with a slower-mode setting like the Champ minigames.

### Pf9. From your survey: add optional friend ties (shared run codes, a friend list, ghost runs, no messaging, never required, no worst-score shaming)?

Recommend: yes, optional, after the shared run-code format exists (FY-7).

### Pf10. From your survey: keep a standing rule that no game has an all-good hero character who never makes a mistake?

Recommend: yes, already noted in the player profile.

