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

### 2. Set the admin password (U8) — needed before I can lock the admin page

**Why:** `admin.html` currently sits behind nothing but an unlisted URL, and it (and the raw reports list) shows real data. To lock it, the backend needs a secret only you control. I can't create or store it for you: it has to live as an environment variable on the FastAPI Cloud app (like `DATABASE_URL` already does) and stay out of git. You answered the design questions (Q6), so this is now the only thing blocking U6, U7, U8 and U9.

**What you're setting:** two separate secrets, so the AIs' access can be revoked without changing your own:
- `ADMIN_TOKEN` — **your** admin password. You type it into the box on `admin.html`.
- `AI_ADMIN_TOKEN` — a second, independent token that only the AIs use (kept in a local file that git ignores). If it ever leaks, you delete just this one variable and your own password is untouched.

**Walkthrough (about 5 minutes):**

1. **Make two strong random values.** In a Terminal, run this **twice** (one for each secret) and keep the two outputs somewhere private, like your password manager (1Password is already on this Mac):
   ```
   python3 -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
   Each run prints a long string like `k3Jd...`. Label them "NoyvjGames ADMIN_TOKEN" and "NoyvjGames AI_ADMIN_TOKEN". A random string beats a memorable password here: you'll paste it into a box, not remember it. (If you'd rather have a passphrase you can type from memory for your own token, that works too — make it long, 5+ random words — but keep the AI token random.)

2. **Add both to the FastAPI Cloud app.** Pick whichever way you prefer:
   - **Dashboard (easiest to see what you're doing):** go to fastapicloud.com, sign in, open the NoyvjGames app (the one at `noyvjgames.fastapicloud.dev`), find its **Environment variables** settings, and add `ADMIN_TOKEN` and `AI_ADMIN_TOKEN` with the values from step 1. Tick "secret" if it offers that.
   - **Or the command line** (from the repo folder, which is where the app is linked; if it says the app isn't linked, run `python3 -m fastapi cloud link` first and pick the app):
     ```
     python3 -m fastapi cloud login
     python3 -m fastapi cloud env set --secret ADMIN_TOKEN "paste-value-here"
     python3 -m fastapi cloud env set --secret AI_ADMIN_TOKEN "paste-value-here"
     python3 -m fastapi cloud env list
     ```
     The last command should show both names (secret values are hidden). Don't paste the values into chat or a repo file; the commands above are the only place they go.

3. **Give the AI token to the local checkout only.** Create a file called `.ai-admin-token` in the repo's top folder containing just the `AI_ADMIN_TOKEN` value (one line, nothing else). It's already in `.gitignore`, so it never gets committed. The AIs read it locally to check admin data; it never appears in any tracked file. (If you'd rather not, say so and the AIs will just use a local test database instead, which is option (c) from Q6.)

4. **Redeploy later, not now.** Setting a variable doesn't change the running site until it next redeploys. I'll build the locked admin page and tell you when it's ready; you'll deploy that (as with every backend change) and it will start using the new variables. Until then nothing changes and nothing breaks.

5. **Tell me just "set".** Not the values. I'll build against those two names, and the first time you open `admin.html` after the deploy it will ask for your `ADMIN_TOKEN`.

**If something goes wrong:** you can always run `python3 -m fastapi cloud env delete ADMIN_TOKEN` (or remove it in the dashboard) and set a new one; nothing is lost, the admin page just stays locked until the value matches. Forgot your own token? Same fix: set a fresh one.

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

### 3. Redeploy the backend (small, whenever convenient)

**Why:** account-synced settings (Y31) added a `settings_json` column and two endpoints (`/users/me/settings`). The site works without them (signed-in players just don't get synced preferences yet), but they only go live when the FastAPI Cloud app is redeployed. The column is added automatically at startup (`patch_schema()`), so there is nothing to migrate by hand.

**What this deploy also turns on:** the admin token lock (U8), mark-report-done (U6), the test-data flag and Accounts panel (U7), the optional account email (U9), and the three save slots (U3). Until both tokens from action item 2 are set, the admin page's data stays locked (fail closed), so set them first or right after. To mark your own real accounts vs test ones, open `admin.html`, unlock it, and tick **Test** on the fake accounts in the Accounts panel.

**Steps:** from the repo folder run `python3 -m fastapi cloud deploy` (or however you usually deploy), then tell me it's done. I'll do a live check that `GET /users/me/settings` answers. The upcoming admin-password and test-data work (U6-U9) will need one more deploy later, so batching them is fine.

---

## Answered 2026-09-26 — folded into `planning/TODO.md` section U (nothing further needed from you)

Your Q1-Q10 answers are now the decided specs on U1-U14 in `planning/TODO.md` (each item says "decided 2026-09-26, ready to build"). In short:

- **Continuum ticks (U1):** ~10s per season early (slower/scaled by era), Pause + 1x/2x/4x, starts paused, ticks only while the page is open and visible, Advance Season button removed.
- **Hearth-and-Hamlet look (U2):** Continuum only, controls as clickable buildings in the scene (one building per "thing", town centre for research); not a colour-only style switcher.
- **Saving (U3):** claim-to-account by default when signed in, Overwrite/New slot/Cancel prompt (or pick from the U4 saves screen), 3 slots for signed-in accounts only, existing saves become slot 1.
- **Opening screen (U4):** built per game from a common starting layout, "Continue" first when a save exists, tutorial offered only from New Game, visual-set picker only for games that have one (Le Champ de Mots), light/dark in general Settings.
- **Test data (U7):** `is_test` flag + AI testing account + hide-test-data checkbox, excluded from public stats too. Neither of us can see which accounts are real, so the locked admin page gets an Accounts panel where you tick the fake ones.
- **Admin password (U8):** `X-Admin-Token` header, separate revocable AI token, protects every admin endpoint. **Your only step is action item 2 above.**
- **Account email (U9):** optional, manual reset verification only, visible to admin (which is why admin is locked), editable by the player from the hub account panel.
- **SOL research tree (U10):** ~20 varied-cost nodes per level, rejoining at Near Bodies then again at Far Bodies, most nodes give a small bonus, existing progress converts.
- **Collapsible cards (U13):** compact by default, remembered on this device, Play stays visible.
- **Screens for speed (U14):** measure first, then split the heaviest 2-3 games; you haven't profiled lag yourself.
