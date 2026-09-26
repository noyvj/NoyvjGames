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

### 2. Choose an admin password (for U8) — needed before I can lock the admin page

**Why:** `admin.html` currently sits behind nothing but an unlisted URL. To put it behind a password, the backend needs a secret only you control; I can't create or store one for you (it must live as an environment variable on the FastAPI Cloud deployment, and be kept out of git).

**Steps (after you answer Q6 below):** pick a long password/passphrase, set it as an environment variable on the FastAPI Cloud app (I'll tell you the exact variable name once Q6 fixes the design), and redeploy. Never paste the password into a repo file or chat.

**What to tell me:** just that it's set. I'll build against the variable name, and for how the AIs get access see Q6.

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

*(Q1-Q10 below all come from your 2026-09-26 audit list, tracked as `planning/TODO.md` section U. Answer under each **Your answer:**; if a question is just "sensible default OK?", "yes" is enough. Signal's and Undersleep's own questions live in `planning/IMPROVEMENT-IDEAS-ROUND-3.md` sections P and Q, not here.)*

### Q1. Continuum tick-based (U1)

Today a season only passes when you press Advance Season. Ticks change that game's whole feel, so a few things need settling:
1. How fast: one season per ~5 seconds, ~10, or ~20? (Early eras have little to do each season; later eras have more to weigh, so I'd suggest a slower default that scales up by era.) **Your answer:**
2. Should there be Pause plus 1x/2x/4x speed controls, and should the game start paused on a brand-new settlement so nothing happens before you've read anything? (My suggestion: yes to both.) **Your answer:**
3. Should it keep ticking while the tab is in the background or you've walked away? Ticking only while the page is open and visible is the safest (nothing piles up while you're away, matching the no-idle-timer stance elsewhere on the hub). **Your answer:**
4. Keep an "Advance Season" button as a fast-forward for impatient players, or remove it entirely? **Your answer:**

### Q2. "Hearth and Hamlet"-style visual style (U2)

I don't have a reference for that game's UI, so I want to build the right thing:
1. Can you describe it (or drop a screenshot into the repo, e.g. `planning/reference/`)? What I need is how the controls sit inside the picture — for example clickable buildings in a scene rather than a button list. **Your answer:**
2. Which game should be the pilot? Le Champ de Mots already has a 4-style switcher (so it's a natural fifth style), but a farm scene with clickable plots is a very natural fit for this look too; Continuum's settlement scene is the other obvious candidate. **Your answer:**
3. Do you want this as one shared style that eventually every game can opt into (needs a lot of per-game layout work), or built game by game starting with the pilot? **Your answer:**

### Q3. Saving: claim by default, 3 slots (U3)

1. "Claim to account by default" — when you're signed in, Save always attaches to your account; anonymous players keep today's plain save codes. Correct? **Your answer:**
2. The pop-up when the account already has a save: should it offer "Overwrite that save", "Save as a new slot" (if slots are on), and "Cancel"? **Your answer:**
3. 3 slots: signed-in accounts only (each game gets slots 1-3 with a name and last-saved time), with anonymous players staying on a single code? **Your answer:**
4. Existing accounts' current saves become slot 1, no data lost — OK? **Your answer:**

### Q4. Per-game opening screen (U4)

1. Roll out to all 12 games at once (via one shared component, like the tutorial), or pilot on 2 games first and copy what works? (I'd pilot on 2, since every game's layout differs.) **Your answer:**
2. "Pick what visual set they want" — only Le Champ de Mots has visual styles today. Do you mean (a) only games that have a switcher show that step for now, (b) every game gets 2-3 visual sets built over time (which overlaps the dark/light theme item Y11), or (c) something else? **Your answer:**
3. Should "Continue" (load your latest save) be the first button when a save exists, so returning players get back in with one click? **Your answer:**
4. Tutorial: on first visit, keep auto-starting when the game opens, or only offer it from the opening screen? **Your answer:**

### Q5. Ignoring test data on the admin page (U7)

1. Which of the 5 accounts are real? Tell me the usernames to keep (I can't tell which are yours from the outside), or tell me the test ones. **Your answer:**
2. My plan: add an `is_test` flag on accounts (and reports/reviews/saves inherit it from their account), a dedicated AI-testing account so the AIs never touch real data, and a "hide test data" checkbox on admin (on by default). Reports/reviews with no account can be flagged by hand from admin. Fine? **Your answer:**
3. Should flagged test data be excluded from the public stats too (ratings, achievement percentages, community highlights)? I'd say yes. **Your answer:**

### Q6. Admin password design (U8)

1. Design: admin endpoints require an `X-Admin-Token` header; `admin.html` shows a password box and keeps the token only in that tab's `sessionStorage`. The token is a server environment variable (see Action item 2). OK? **Your answer:**
2. How should the AIs get access? Options: (a) you give us the password per session on request, (b) a second separate "AI token" you can revoke independently that is only ever set in a local, gitignored file, (c) AIs never read prod admin data and use the local test database instead. I'd pick (b). **Your answer:**
3. Should this also protect the other admin-only endpoints (the raw `answer-reports` list, `/admin/stats`)? I'd say yes, all of them. **Your answer:**

### Q7. Optional account email (U9)

1. Should the email be used only so you can verify a reset request by hand (you compare it to what the person tells you), or do you want automatic reset emails? Automatic needs an email-sending service (extra signup and cost), so I'd start with the manual version. **Your answer:**
2. Should the email be private to the admin (never shown to other players, never in any public stat)? I'd say yes, and I'll add it to the Terms & Privacy page. **Your answer:**
3. Can a signed-in player add/change/remove it later from the hub account panel? **Your answer:**

### Q8. SOL research tree (U10)

Right now the research is two bars (Near Bodies, then Far Bodies). Your description: ~20 nodes, splitting and rejoining, ending at "Near Bodies", all costing 50 Iron.
1. "Near bodies at the end" — so the Near Bodies unlock (Moon, Mars) becomes the final node, and Far Bodies becomes a second, deeper tree afterwards? Or is Far Bodies part of the same 20? **Your answer:**
2. Should every node cost exactly 50 Iron (simple, as you said), or should later nodes cost more/another resource? I'd start with a flat 50 and add variety later if it feels samey. **Your answer:**
3. Should the nodes do something (e.g. "Space-Grade Mining Equipment" = +10% Iron per click, "Efficient Smelting" = cheaper miners) or be purely a path to the end? I'd give most of them a small real bonus so the tree feels useful — which is your stated goal. **Your answer:**
4. Existing saves have research progress as a number. I'd convert it to nodes already researched, so nobody loses progress — fine? **Your answer:**

### Q9. Collapsible hub title cards (U13)

1. Default state: compact (picture, name, rating stars only; click to expand for the text, review widget and feedback) or expanded with a "Compact view" toggle? I'd default to compact, remembering the choice on this device. **Your answer:**
2. Should "Play" stay visible in the compact view? (I'd say yes — clicking the picture/name still opens the game.) **Your answer:**

### Q10. Splitting games into screens for speed (U14)

1. Which games feel laggy to you, and when — at startup, or while playing? That tells me whether to attack load time (Pyodide + big `game.py`) or per-frame work. **Your answer:**
2. My plan is measure first: boot time and DOM size per game, then split the heaviest 2-3 (likely Continuum, Le Champ de Mots, SOL) into on-demand screens, and reuse whatever works for U4's opening screens. OK to start there? **Your answer:**
