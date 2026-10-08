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

### Fg1. Dream game: what working title do you want for the dark foggy forest city builder (a placeholder is fine)?

No recommendation, your call.

### Fg2. Dream game: is the city the main loop, with the mining mode, the helping nodes and the puzzles as side activities that feed it?

Recommend: yes, the city is home and everything else feeds it.

### Fg3. Dream game: which piece do you want built first as its own small game: the per-building puzzles, the bunker mining skill tree, the first-person helping nodes, or the friendship sidequests?

Recommend: the per-building puzzles, since you said they could start as their own games.

### Fg4. Dream game: top-down 2D, or low-poly 3D like Continuum's scene?

Recommend: top-down 2D first (cheaper and faster), with a low-poly look.

### Fg5. Dream game: what does the fog do in play (hides unexplored land, makes some things dangerous, slows travel, only mood)?

Recommend: hides unexplored land and clears as the city grows, never kills you.

### Fg6. Dream game: what lives in the fog (creatures, survivors, machines, nothing but atmosphere)?

Recommend: machines and strange remnants, to match your sci-fi and computers taste.

### Fg7. Dream game: who runs the buildings (humans, robots, a mix)?

Recommend: a mix, so the friendship quests can range from warm to eerie.

### Fg8. Dream game: are there threats to defend against, and if so should failing a defence cost something fixable (restore by doing something) rather than ending the run?

Recommend: yes, threats exist, failures are always repairable.

### Fg9. Dream game: is there any lose state at all?

Recommend: no, only setbacks you can recover from, with an optional hard mode.

### Fg10. Dream game: what counts as a gift to a keeper (resources, crafted items, found objects, lore pages)?

Recommend: found and crafted objects, so collecting feeds friendship.

### Fg11. Dream game: how many keepers (people running buildings) at launch: about 6, 12 or 20?

Recommend: about 6, each with a real questline, then more later.

### Fg12. Dream game: what puzzle kind should each building have (name a kind per building you imagine, or say "you choose")?

Recommend: you choose among your favourites (spatial and logic), I propose a table for you to react to.

### Fg13. Dream game: should the mining mode be a separate screen you open from the city, or a place you walk to inside the city?

Recommend: a separate screen opened from a mine building.

### Fg14. Dream game: how should it support both of your play states, under 20 minutes and over 3 hours (for example a short daily-visit loop and long optimisation sessions)?

Recommend: every building gives a 5 to 15 minute task, with deeper optimisation always available.

### Fg15. Dream game: should the city keep producing while you are away, with a cap?

Recommend: yes with a generous cap and no pressure to return.

### Fg16. Dream game: should friends be able to visit your city or leave a gift (optional, no chat)?

Recommend: later, after the shared run code and friend ties exist.

### Fg17. Dream game: how many branching quest lines (Lifeline-style) should there be at the start?

Recommend: two, then add as the keepers arrive.

### Fg18. Dream game: which existing site game is closest in feel to what you picture (Continuum, SOL, Canopy, another)?

No recommendation.

### Fg19. Dream game: art direction: dark and foggy low-poly, hand-drawn, or something else, and is there a game whose look you want?

Recommend: low-poly dark and foggy.

### Fg20. Dream game: what should the first five minutes be (arrive in the fog, meet the first keeper, place the first building)?

No recommendation, your call.

### Fg21. Dream game: is there an ending, or is it open-ended with a 100% collection goal?

Recommend: open-ended with a collection and completion tracker (easy to 100%).

### Fg22. Dream game: should some of the existing site games appear inside it as building puzzles (for example Signal as a radio tower puzzle, Lexis as a translation hut)?

Recommend: yes, as the cheapest way to get puzzles and link the whole site.

### Fg23. Dream game: what do you want to collect most (people, gifts, recipes, specimens, buildings' upgrades)?

Recommend: people and their gifts, and building upgrades.

### Fg24. Dream game: if it must be smaller, which part do you cut last?

No recommendation.

### Fg25. Dream game: when do you want a first playable, before or after your semester ends?

Honest note: Chronicle, the new puzzle games and the per-game work come first. Recommend: after your semester.

