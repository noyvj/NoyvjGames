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

### U1. Undersleep: should the optional daily check-in layer be hidden until the player turns it on?

Recommend: yes, hidden by default ("Just play" is the default).

### U2. Undersleep: keep the player's personal data on the device only, with manual export and import, and never in a save code or the cloud?

Recommend: yes. A cloud version needs per-account encryption, which is a real project; say "later" if you want that project eventually.

### Ch1. Chronicle: after you spot-check the sample set, may I author the full American presidents set (three sources per claim)?

Recommend: yes, then the history of food and Ancient Greece as sets 2 and 3.

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

### Ch7. Chronicle: when it is ready, should Chronicle go on the hub (card, thumbnail, favicon) now, or wait until the presidents set is fully authored?

Recommend: wait until the full presidents set is done.

### Lx1. Lexis: build planets 4 and 5 (the two fainter worlds) to grow it to the Large size?

Recommend: later, after you have played planets 1 to 3.

### Fr1. Le Champ de Mots: should a singular noun typed without its le or la (for example `mode` for `la mode`) count as correct?

Today it is marked wrong because the article carries the gender. Recommend: keep le/la required (the bare plural for des/les nouns and the bare noun for l' nouns are already accepted).

### Fr2. Le Champ de Mots: which word sounded wrong in "J'adore nager, j'aime aussi faire du surf." (a player's pronunciation concern)?

I suspect "surf" (an English loanword). Please listen and tell me which word.

### Fr3. Le Champ de Mots: which word sounded wrong in "du poulet" (a player's pronunciation concern)?

It is not on the pronunciation watchlist. Please listen and tell me.

### Be1. Backend: how many proxies does FastAPI Cloud put in front of the app?

The per-address rate limits use the first X-Forwarded-For entry, which a client can spoof. Recommend: leave as is unless you see abuse.

### Be2. Backend: reject the username noyvj at signup unless an owner environment variable is set?

Otherwise, if the production database were ever rebuilt, whoever signed up as noyvj first would get admin. Recommend: yes.

### Be3. Backend: should sign-in tokens expire, with a logout route?

They never expire today (a noted design choice). Recommend: later.

### Be4. Hub: remove the Google ads script (placeholder client id) from the hub until your AdSense account is approved?

It can only fail until then. Recommend: yes, and I put it back when you give me the id.

### Be5. Hub: ask for the session lengths on the hub cards separately later (you said later on this)?

My estimates: Signal 5 min, the eight climate games 20 min, everything else long-form. Say "later" to keep this parked.

### Ti1. Tide: build a Tide Workshop (sliders for starting funds, lag length, sea-level rate, surge size) with runs labelled "custom rules" and never ranked?

Recommend: yes.

### Ti2. Tide: may I choose the named coastline scenarios myself (three invented coasts: low delta, cliff bay, barrier island, with plain traits)?

Recommend: yes, my call.

### Ti3. Tide: add a living harbor scene (a harbor picture drawn in code that reflects acidity and fish, with an off switch)?

Recommend: yes.

### Ti4. Tide: give technical words (acidity, lag) plainer labels with the science in a tooltip?

Recommend: yes.

### Ti5. Tide: show achievements as medal cards (shape plus text) instead of a plain list?

Recommend: yes.

### Gr1. Grid: should retiring a plant ask for confirmation only when it is the last plant? (Retiring any other plant already skips confirmation.)

Recommend: yes, last plant only.

### Gr2. Grid: may the scenario builder share scenarios through the shared run-code format?

Recommend: yes.

### Gr3. Grid: build the R&D lab as part of an upgrade tree (you suggested a tree over a roguelike earlier)?

Recommend: yes.

### Gr4. Grid: build neighbour trading with computer-controlled neighbours only (no real players)?

Recommend: yes.

### Gr5. Grid: build storm prep as a short preparation step before a storm with small costs?

Recommend: yes.

### He1. Herd: may I choose the balance values for the new mechanics myself and tell you afterwards?

Recommend: yes.

### He2. Herd: may I write the branching story as a short original story with three branches, with real-world facts only in the info panel?

Recommend: yes.

### He3. Herd: how much should the minigame affect results?

Recommend: a small bonus capped at about 5% of a round's funds.

### He4. Herd (and Aftermath, Thaw): mark runs that use custom rules as "unranked" and keep them off leaderboards?

Recommend: yes.

### Th1. Thaw: show real-world gigatonne carbon figures only if I read them live and name the source on screen?

Recommend: yes.

### Af1. Aftermath: add a fog mode (events hidden until they arrive) as an optional hard mode, since it conflicts with the forecast features?

Recommend: yes, optional.

### Af2. Aftermath: put the scenario and modifier options into one "modifiers" menu?

Recommend: yes.

### Lo1. Loop: build trading cards with short real-world facts about each material, read live and named on screen?

Recommend: yes.

### Lo2. Loop: add market shocks as a deterministic scheduled mode (no randomness)?

Recommend: yes.

### Lo3. Loop: add a simple computer rival chain you compare against?

Recommend: yes.

### Lo4. Loop: add rewind (like Drift's) now and autopilot later?

Recommend: rewind yes, autopilot later.

### Dr1. Drift: merge the two overlapping ideas (a personality system and a civic-milestone system) into one?

Recommend: yes.

### Dr2. Drift: may I draw the skins, building pop-ups and route glyphs myself as simple code-drawn graphics?

Recommend: yes.

### Te1. Trade Empire: may I add a Blackout mode badge to the shared opening screen?

It touches shared code used by every game. Recommend: yes, small.

### Te2. Trade Empire: build the Cartel Board as a late-game panel?

Recommend: later.

### Co1. Continuum: write the advisor council, notable citizens and citizen of the season as original fictional characters, with real-world facts only sourced and named on screen?

Recommend: yes.

### Co2. Continuum: build neighbouring settlements as computer-controlled neighbours first, before any multiplayer?

Recommend: yes.

### Ca1. Le Champ de Mots: add coins earned from watering that unlock cosmetic skins?

Recommend: yes, cosmetic only.

### Ca2. Le Champ de Mots: add a false-friends set, built from a reputable list read live and named on screen?

Recommend: yes.

### Ca3. Le Champ de Mots: add an optional answer timer to practice for a quickest-answer record?

The game deliberately has no clock. Recommend: no.

### So1. SOL: may I write the balance for prestige mutators myself?

Recommend: yes.

### So2. SOL: build the anomaly system on a fixed schedule rather than random?

Recommend: yes.

### Cn1. Canopy: build the community plot (one forest everyone adds to) on the new leaderboard backend?

Recommend: later.

### Cn2. Canopy: build the rival-company 1 v 1 mode?

Recommend: later.

### Mp1. Multiplayer: replay verification of scores for Signal and Last Line only, client-trusted everywhere else?

You said go with client-trusted for now; this asks only about adding verification later for Signal. Recommend: later.

---

## Answered 2026-10-08 — folded into the TODO and docs (read from the ideas sheet)

- **Round 1 items to judge (old item 4):** you said **now** for Grid C6 (overlay two saved scenarios' trend graphs), Tide D10 (show acidity from three seasons ago next to the current value), Aftermath E5 (another event category), Herd F4 (a second end-of-game feedback question about Herd's own lesson) and Loop H16 (optional supply chain disruption event, opt-in advanced mode), and **do not do it** for the Contraption physics sandbox. The five are now TODO items (section FY); Contraption is dropped.
- **Multiplayer (4):** go with client-trusted scores for now (recorded in `planning/MULTIPLAYER-SCOPING.md`).
- **Seasonal events:** you said yes to the redone list (host mapping, the dates and badges in both the game and the hub); recorded in `planning/SEASONAL-EVENTS.md`.
- **Overnight design calls:** yes to my recommendations: keep the Aftermath Flawless Defense bar at 15%, build the Aftermath unspent-resources confirm off by default, drop Trade Empire J-13 (charter archetypes), drop Continuum K-29 (Blitz timer), build the shared run-code format once, drop the luck items (Loop GH-17, GH-21, GH-30). You will tell me about the Continuum par numbers while you play, and asked me to ask about session lengths separately (that is item Be5).
- **Clean up test rows (0), AdSense (1) and screenshots (0c):** you said later; they stay at the top.
- **Redeploy (0b):** you pushed and the backend answered, so it is done. Everything pushed so far is live: the answer report "fixed" tickboxes, leaderboards, health, the account export and delete, and the rest.
- **How to ask you things (0e):** you asked me to put questions on the ideas sheet directly, one per item, because answering in a file is hard from your phone. That is what this file now does: each question below is one item.

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
