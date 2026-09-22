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

### Q2. Signal (M3) — six questions before it gets built

The groundwork plan is `planning/signal-plan.md` (recommended mechanic: "Triangulate", a summed-signal deduction puzzle with a daily seed and no backend). Answer under each line.

1. Plain-JS exception OK (the game opens instantly), or do you want Pyodide anyway for consistency (a multi-second first load on a "quick daily" game)? **Your answer:**
2. Theme: retro radio-room (recommended), submarine sonar, or alien SETI? **Your answer:**
3. UTC daily reset (same puzzle for everyone, good for share talk), or each player's local midnight? **Your answer:**
4. Want an optional non-daily "endless" practice mode beyond the archive? **Your answer:**
5. Should puzzle #1 launch on a specific day, to help the 2-week "something new is visible" cadence? **Your answer:**
6. Is the recommended mechanic (Option A) what you want, or should I prototype B briefly first? **Your answer:**

---

### Q3. Undersleep (M4) — eight questions before it gets built

The groundwork plan is `planning/undersleep-plan.md` (a game layer plus an optional local-first sleep/mood journal, kept separable). Answer under each line.

1. Journal cloud sync: allow it at all (through the existing save system, as a separate opt-in), or keep the journal strictly local plus manual export/import? **Your answer:**
2. If sync is allowed, are you comfortable with that data sitting in the Neon database, given it is more personal than game saves? Would you want it encrypted client-side with a passphrase? **Your answer:**
3. Start with the tracker hidden ("Just play" default, recommended) or shown at first run? **Your answer:**
4. Tone: deadpan-absurd (recommended) or warmer/cozy? **Your answer:**
5. One persistent character, or a roster with "retire and inherit"? **Your answer:**
6. Is a one-time "not medical advice" acknowledgement at first Journal open acceptable, or too heavy? **Your answer:**
7. Any real-life tags you specifically want (caffeine, exercise, screen-late...), or leave it to my defaults? **Your answer:**
8. Story mode: a light arc (new job, new city) or sandbox only at launch? **Your answer:**

*(Overclock, Last Line and Deep Descent are deliberately not asked here: per your scoping, their theme and mechanic questions wait for the next ideas round, `planning/IMPROVEMENT-IDEAS-ROUND-3.md`.)*

---

### Q4. Continuum K26b — an eighth era, before any code starts

Per your "rather than closing it, let's keep making more eras" answer, `games/continuum/CLAUDE.md`'s new "K26b: Era 8 scoping" section proposes a working concept: **"Diaspora"** — a second, distant site founded by descendants of the original settlement (finally using the long-deferred generational-descendants narrative thread), with equity measured *between* the two sites (not just within one) as the sustainability mechanic — a genuinely new shape none of the seven existing eras repeat. Read that section for the full reasoning; answer under each line.

1. Is "Diaspora" the right name/theme, or do you want something else (fully fictional off-world, a more grounded on-world "regional expansion" framing, or a different angle entirely)? **Your answer:**
2. Is a second full site the right shape, or would the equity-as-primary-lever idea work better applied to something smaller (e.g. two districts within one settlement), so it ships faster than standing up a second full site's worth of state? **Your answer:**
3. What should Relay Stations (the new building) actually move between sites — people, a resource, or knowledge/research points? This decides a fair amount of the mechanic's exact math. **Your answer:**
4. Real-world grounding: a regional-inequality/secondary-city angle (UN-Habitat-style sources), an off-world/space-habitat-network angle, or should this era stay closer to Earth and skip the space-diaspora framing entirely? **Your answer:**
5. Once this is answered, should building it follow the same "repeat the Phase-3 per-era pattern" process every prior era used, or do you want a dedicated milestone breakout first? **Your answer:**

---

### Q5. Le Champ de Mots L22 — redefine "new cultural note" now that rows aren't gated

The original idea was a "new note available" indicator that fires when a row freshly unlocks and has cultural context worth reading. L4a (already built) removed row-unlock pacing entirely — every row is open from the start — so "freshly-unlocked row" no longer means anything, and the original trigger can't fire the way it was designed to.

Options, so you're not answering from a blank page:
- **(a)** Redefine it as an "unread notes" badge: track which rows' cultural notes you've actually opened at least once (a saved seen-list), and badge any row whose note you haven't opened yet — closer to the original intent (surface content you haven't seen), just triggered by "never opened" instead of "just unlocked."
- **(b)** Drop it — with every row open from day one, a player can just browse cultural notes at their own pace, and a badge might just add clutter.
- **(c)** Something else you have in mind.

**Your answer:**
