# For You — Things Only You Can Do, and Questions I Need Answered

I check this file whenever I'm doing site work. Two kinds of entries live here:

- **Action items** — real-world steps only you can take (an external account signup, a decision that needs your own login/credentials). Each one says why it's needed, exactly how to do it, and what to tell me afterward so I can pick the work back up.
- **Questions** — decisions I can't make for you. Type your answer directly under the `**Your answer:**` line for that question.

**Once you've done an action item or answered a question, I remove that whole entry the next time I'm in here** — so this file only ever shows what's still actually open. Nothing is ever silently dropped: once handled, the substance moves into the relevant commit, doc, or `planning/TODO.md`/`LATER.md` line, same as everything else. If you want to double check what got removed, `git log -- planning/FOR-YOU.md` has the full history.

---

## Action items

### 1. Apply for Google AdSense

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

### 2. Redeploy the backend (community leaderboards)

**Why:** several features added new backend pieces: the opt-in leaderboards (SOL fastest completion, Aftermath hardest schedule, Herd decoupling gap: `/leaderboards/...` plus a new table), the extra community-index stat fields (Aftermath, Drift, Tide) the Warframe market price proxy (`/market/prices`) and the shared community pools (`/pools/...`). Until the backend is redeployed the boards just show "unavailable" in-game; nothing breaks. More items in this batch may add further backend fields (see the community-stat items in `planning/TODO.md`), so it is fine to redeploy once at the end of the night.

**Steps:** the same redeploy you did before (from the repo's `app/` folder with the FastAPI Cloud CLI). No new environment variables. The new table is created automatically on startup.

**What to tell me:** just "redeployed", and I will live-check `GET /leaderboards/sol/fastest_completion` returns 200.

### 3. Which Warframe "meta" combos should the tracker pre-load?

**Why:** the build comparison ranks named combos by how close you are to finishing them. The Warframe Wiki names only one popular combo (the "177" Amp: Raplak Prism, Propa Scaffold, Certus Brace) and none for Zaws or Kitguns, and I will not invent community metas. You can already add your own in the tracker's "My combos" box.

**Your answer:** list any combos you want built in (name plus the parts), or say "just my own box is fine".

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
