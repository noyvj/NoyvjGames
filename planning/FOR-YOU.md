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

## Questions

### Q1. What did your original B15 comment actually mean?

Canopy's `planning/TODO.md` per-game list has one leftover unresolved item: your answer to B15 talked about "overpinning" and worrying about too much being pinned, but B15 itself was "extend the mobile-dock treatment to the stats/legend panels" — which has nothing to do with pinning. I kept B15 itself as a plain yes (it's built, folded into the mobile-dock rollout goal), but I don't know what your actual comment was about. Was it meant for a different item (maybe the hub lobby's "games you have saves for" pinned section, L11)?

**Your answer:**

### Q2. Ready for me to push this repo to GitHub?

The accounts system (signup/login/save-claim/feedback) is built and tested locally but has never gone live — `planning/ACCOUNTS-AND-FEEDBACK-DESIGN.md` confirms the real FastAPI Cloud backend auto-deploys on every push to this repo's GitHub remote, so "deploying" it is just a matter of pushing. I haven't pushed anything to GitHub this session under a standing instruction not to without asking first — there's now a large amount of accumulated work (achievements, settings panels, colorblind fixes, and more across every game) sitting in local commits only. Say the word and I'll push main to the remote; otherwise I'll keep working locally and this stays queued.

**Your answer:**
