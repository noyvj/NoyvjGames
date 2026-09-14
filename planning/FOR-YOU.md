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

### 2. Deploy the accounts system to production

**Why:** Accounts (signup/login), save-claiming, and site-wide feedback are all built and fully tested — but only against a local backend. The real FastAPI Cloud + Neon instance (the one the live site's ratings already use) has never had this code pushed to it, so none of it works on the actual live site yet. I don't have your FastAPI Cloud login, so I can't run this deploy myself.

**Steps:**
1. From the `app/` directory, run whatever deploy step you used the first time this backend went live (the FastAPI Cloud CLI's deploy command, or through the FastAPI Cloud dashboard directly — whichever you originally used).
2. The Neon connection string and other environment variables should already be set on that deployment from before (ratings already work in production), so you shouldn't need to re-enter anything — but if FastAPI Cloud prompts you to confirm a secret, keep it identical to what's already there.

**What to tell me once it's done:**
- Just that it's deployed (or paste any error message if the deploy fails).

I'll do a live verification pass myself against the real production URL — signup, login, save-claim, feedback — and report back what I find.

---

## Questions

### Q1. What should the site's real public name be?

`planning/site-plan.md` still calls **"CodingIsANoyvj"** a placeholder, to be confirmed "before anything public launches" — but the site is already live (tagged `site-hosting-v1`), so this is overdue. Whatever you answer, I'll update the page `<title>`, the repo's own docs, and anywhere else the name shows up.

**Your answer:**

---

### Q2. Does BCM114 need audience-engagement content (e.g. Instagram) alongside the site?

`planning/site-plan.md` deferred this pending the semester outline, originally expected around July 27 — now well past. If the outline has dropped, do you know whether the site's public availability alone satisfies BCM114's requirement, or does something like an Instagram presence need to be built alongside it?

**Your answer:**

---

### Q3. Password-reset path for accounts — which approach?

Accounts use username + password with no email on file, so there's currently no way to recover a forgotten password — that account's claimed saves/feedback would be permanently stranded. Two real options:

- **(a) Add a real email provider** (e.g. Resend) so a "forgot password" flow can email a reset link. Needs you to sign up for that service and hand me an API key — a small but genuine cost/complexity addition (this is the exact thing that was dropped once already, when the original magic-link auth design got replaced with username+password for this reason).
- **(b) A lower-tech admin-assisted manual reset** — no new service, but means a stranded account needs you personally to intervene (via direct database access) if it ever comes up. Reasonable given the site's current scale.

**Your answer:**

---

### Q4. Favicon / PWA icon art (L6)

The site's icons are still placeholder art. Do you want to:
- **(a)** source or draw real art yourself and hand me the image file(s) to wire in, or
- **(b)** have me generate a simple placeholder graphic (e.g. a clean CSS/SVG icon) as a stand-in until you have real art?

**Your answer:**
