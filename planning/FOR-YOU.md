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

## Questions

### Q1. Grid C21 & Tide D3 — the scoping conversation you asked for

Both ideas got "I'll let you make the call" and are currently parked in `LATER.md` pending exactly this conversation:

- **Grid C21** — a "grid twin" split-view comparison mode: run two strategies side by side in one session. Open questions before I'd build this: should the twin be a fully separate, independently-clickable second grid (double the UI, double the state), or a lighter "shadow" grid that just mirrors your build choices onto a different starting scenario for comparison (less to build, less to click, but less genuinely "yours")? And does this replace or sit alongside the existing global-comparison line (C15) and the operator-career meta-progression (C1) that already give a sense of "how am I doing"?
- **Tide D3** — a multi-settlement mode: manage two coastal settlements at once. Same shape of question: fully independent second settlement (its own coastline grid, its own adaptation tiers, genuinely double the game), or a lighter "sister settlement" that shares your funds/adaptation tier but has its own separate coastline and sea-level exposure (less duplication, but a different kind of tension than "manage two economies")?

Both would be a real scope jump for their game (meaningfully more UI, more state, more to test) rather than a small feature — worth deciding deliberately rather than me guessing at the shape. What's the actual player experience you want out of either one, and does "full duplicate" or "lighter shadow/sister" match that better?

**Your answer:**

---

### Q2. Warframe tracker: how possible is linking to real account data, and tracking frame/weapon/companion crafting?

You asked (round 2, X17) for a feasibility talk on two goals. Short version first: the account-data half is **already partly done**, the crafting half is **not figured out yet**.

**(a) Connecting to account data, the way AlecaFrame does.**
- *Already built (X-b):* the tracker's "Import lastData.dat / inventory.json" button fills every resource's **built** count from a real inventory export. You produce the file with `warframe-api-helper` or AlecaFrame while the game is running, then upload it. Decryption and matching happen in your browser; nothing is sent anywhere. Details are in `warframe_build_tracker/README.md`.
- *Honest gap:* it was tested only against a synthetic file, because no real export was available. The matching is a best-effort guess on item paths, and the import summary lists anything it couldn't match.
- *Truly live linking* (no manual export step) is **not realistic** for a static site: the game has no official public API for a player's inventory, and the community tools get it by reading the game or its login session on your own PC, which a web page can't do and shouldn't. The practical ceiling is "export a file, upload it," which exists now.

**(b) Tracking frame / weapon / companion crafting, not only Amp/Zaw/Kitgun parts.**
- *Feasibility: moderate, and it depends on one thing I can't check from here.* Real inventory exports are known to contain more than resources (owned blueprints, items currently in the foundry, and owned frames, weapons and companions), so an import could tell the tracker which crafts you already own or have running. I'm going from general knowledge of the file format, not from a real file in this repo, so treat the field names as unconfirmed.
- *The bigger cost is reference data, not import:* every extra item needs its own component and resource list. There are hundreds of frames and weapons, so I'd propose starting with a small hand-picked list you actually farm, the same way the current 33 parts started, and growing it.
- *Foundry timers* ("ready at" times) look easy to add once a real export shows how timers are stored.

**What I need from you:** run `warframe-api-helper` (or AlecaFrame) once and give me a real `lastData.dat` or `inventory.json`, ideally with your personal identifiers removed or just checked by you before sharing. With a real file I can verify the resource import and see exactly what the crafting data looks like, and then say concretely what's feasible instead of guessing. If you'd rather not share one, I can keep building on the synthetic file, but crafting tracking would stay guesswork.

**Your answer:** (share a sample / no sample, keep it resource-only / start with a small hand-picked crafting list)
