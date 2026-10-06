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

**Your answer (2026-10-07): later.** When every game has its Desktop layout (Le Champ de Mots and SOL are still waiting on your usage reset), I send screenshots of all of them and you give your input. Nothing needed from you until then. Controller support: not yet; audio stays parked.

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

### 4. Answers to your Round 3 questions, plus five items I now explain (each needs one word from you)

**You asked: how visible is all the information right now (usernames, passwords, saves)?** I checked the backend code. Plainly:
- **Passwords** are never stored or sent back. Each is hashed with PBKDF2-SHA256 (600,000 rounds, a random salt per account) and no endpoint returns the hash.
- **Usernames** are private except in two places: signing up tells you whether a name is already taken (so names can be probed one at a time), and a username shows next to a score only on a leaderboard you have opted into.
- **Saves** are the main exposure. A save is stored as plain JSON in the database and **the save code is the only key**: anyone who has a code can read (and overwrite) that save with no login. A code is 8 characters from a 31-letter alphabet (about 850 billion possibilities), fine for game progress, not fine for anything personal. Saves you claim to an account are attached to it, but the code still works.
- **Feedback comments** are public. The public list used to include an internal account id; I removed it tonight.
- **Emails** (optional) are visible only to you in the admin page, never in any public output. **Ratings**, **aggregate stats** and **leaderboard entries** are public by design; stats hide any group smaller than 3.
- **Sessions** (the login token) never expire on their own.
- **Fixed tonight (goes live on the next backend deploy):** guessing passwords is now throttled per username and per address, guessing save codes is throttled per address, and the public feedback list no longer carries an account id.
- **Still open, your call:** for Undersleep's personal data I recommend it stays on the device only (with manual export and import) and never goes in a save code or the cloud; a cloud version would need per-account encryption, which is a real project. Tell me if you want that project anyway.

**Undersleep Q3, restated:** should the optional daily check-in part (the "add personal touches" layer) be hidden until the player turns it on ("Just play" is the default), or shown from the first launch? I recommend hidden by default.

**Items you could not judge because I did not explain them (my labels; the ideas are from Round 1):**
1. **Grid C6:** let a player save two scenarios and overlay their trend graphs for a side-by-side comparison. (Grid now has the shadow-grid twin, which covers part of this.) now, later or drop?
2. **Tide D10:** show the acidity from three seasons ago right next to the current acidity, so the delayed link between cause and effect is visible as numbers. now, later or drop?
3. **Aftermath E5:** add another event category beyond weather and non-weather (for example a heat-mortality event) for variety in the fixed seven-event schedule. now, later or drop?
4. **Herd F4:** a second end-of-game feedback question about Herd's own lesson ("did decoupling feel like a real strategy, or a tax on growth?"), like Thaw's two-question pattern. now, later or drop?
5. **Loop H16:** an optional "supply chain disruption" random event, opt-in as an advanced mode, kept apart from the deterministic core lesson. now, later or drop?
6. **Contraption (round 2 M8):** a physics puzzle sandbox (drag parts, watch them collide). It needs a JavaScript physics engine such as Matter.js, which means shipping a library and writing the game in JavaScript rather than Python, a much bigger stack decision than a normal new game. It stays parked as you said; tell me if you ever want it costed properly.

### 5. Multiplayer: one decision left (the rest are answered)

Answered 2026-10-07 and recorded in `planning/MULTIPLAYER-SCOPING.md`: (1) the level of multiplayer is my call; (2) any ghost or run summary is opt-in; (3) two-player games let the player choose friend-only or open, with friend-only recommended; (5) moderation is you for now, and me too if that is possible.

**Still open: (4) client-trusted scores or replay verification.** You said unsure. Plain version: today a score is whatever the player's browser sends, so a determined person can post a fake one. Replay verification means the server re-runs the game from its seed and the recorded moves to check the score, which only works for deterministic games (Signal, Last Line, a seeded Canopy forest) and costs real work. My recommendation: accept client-trusted scores for now (friendly boards), and add verification only for a game where cheating would matter. Say "go with that" or tell me otherwise.

### 7. Seasonal events: react to the redone list

`planning/SEASONAL-EVENTS.md` redoes Round 3 section N around real big dates (Christmas, Halloween, New Year, Easter, Hanukkah, Thanksgiving, 4th of July, Valentine's, Lunar New Year, Diwali), each a 15-minute task on a host game with a temporary stand-in where no game fits. The date engine is built and tested. Three questions: (1) is the host-game mapping acceptable? (2) which American-centric dates (4th of July, Thanksgiving) do you keep, replace with inclusive ones, or drop? (3) should badges show only in the game, or also on the hub next to account achievements (I recommend both)?

---

## Answered — building now (no further input needed, listed so you can see what your answers turned into)

From the completion-verification audit's questions (all answered 2026-09-21):

- **Continuum K7** (was Q2): investigated per your request rather than ratified blind — turned out to be a false positive (two unrelated ideas sharing the "K7" label across rounds; both are genuinely done). See `planning/TODO.md`'s V-E-9 for the full trace. No action needed.
- **Continuum K15 / site-wide settings sync** (was Q3): you want this as a real site-wide feature (signed-in players' preferences follow them everywhere; guests keep the current per-browser/per-device reset behavior), not just a Continuum fix. Scoping this as its own proper cross-game feature — see `planning/TODO.md`'s new entry.
- **Thaw G5** (was Q4): building a real "years per round" calibration number, my call on the exact figure.
- **Thaw G10** (was Q5): leave as-is, no change. Recorded in `planning/TODO.md` V-E-3.
- **Loop H13** (was Q6): the achievement-toast substitution stays, but sequencing so a milestone-worthy achievement toast and any other toast don't visually overlap — never fire two at once.
- **Loop H20** (was Q7): building real distinct flavor content per goods-set (not merging into H2).
- **Drift I8** (was Q8): close enough, no change. Recorded in `planning/TODO.md` V-E-7.
- **Aftermath E6 "Civil Unrest"** (was Q9): kept. `LATER.md`'s stale Aftermath E5 entry removed.
- **SOL A18 "Reset This World"** (was Q10): kept. `LATER.md`'s stale SOL A18 entry removed.
- **SOL A3 welcome-back toast** (was Q11): building a real delta against your previous visit's stats, not just a static snapshot.
- **Canopy B3 Highland Grove** (was Q12): building a distinct degradation/compounding rate multiplier for the second biome.
- **Aftermath E4 legacy system** (was Q13): you left this to my call — decided while building, see the commit/CLAUDE.md note once it lands.
- **Grid/Continuum mobile dock** (was Q14): keeping the lighter version deliberately, no change. Recorded in `planning/TODO.md` V-AB-3.
- **UI decluttering, Canopy/Le Champ de Mots** (was Q15): you agree, no change. Recorded in `planning/TODO.md` V-AB-6.
- **Continuum K9 / Warframe X23** (was part of Q16): both kept as their own separate items, no folding/moving.

---

## Answered 2026-09-26 — folded into `planning/TODO.md` section U (nothing further needed from you)

Your Q1-Q10 answers are now the decided specs on U1-U14 in `planning/TODO.md` (each item says "decided 2026-09-26, ready to build"). In short:

- **Continuum ticks (U1):** ~10s per season early (slower/scaled by era), Pause + 1x/2x/4x, starts paused, ticks only while the page is open and visible, Advance Season button removed.
- **Hearth-and-Hamlet look (U2):** Continuum only, controls as clickable buildings in the scene (one building per "thing", town centre for research); not a colour-only style switcher.
- **Saving (U3):** claim-to-account by default when signed in, Overwrite/New slot/Cancel prompt (or pick from the U4 saves screen), 3 slots for signed-in accounts only, existing saves become slot 1.
- **Opening screen (U4):** built per game from a common starting layout, "Continue" first when a save exists, tutorial offered only from New Game, visual-set picker only for games that have one (Le Champ de Mots), light/dark in general Settings.
- **Test data (U7):** `is_test` flag + AI testing account + hide-test-data checkbox, excluded from public stats too. Neither of us can see which accounts are real, so the locked admin page gets an Accounts panel where you tick the fake ones.
- **Admin password (U8):** `X-Admin-Token` header, separate revocable AI token, protects every admin endpoint. Both tokens are set and the backend is deployed — confirmed live 2026-09-26 (`GET /admin/stats` returns 401 with no token, 200 with the real one).
- **Account email (U9):** optional, manual reset verification only, visible to admin (which is why admin is locked), editable by the player from the hub account panel.
- **SOL research tree (U10):** ~20 varied-cost nodes per level, rejoining at Near Bodies then again at Far Bodies, most nodes give a small bonus, existing progress converts.
- **Collapsible cards (U13):** compact by default, remembered on this device, Play stays visible.
- **Screens for speed (U14):** measure first, then split the heaviest 2-3 games; you haven't profiled lag yourself.
