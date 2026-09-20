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

## Answered for you (no action needed)

### Herd F29: is a "methane capture marketplace" realistic? Yes.

**Finding:** real farms do sell the output of methane capture. Manure digesters produce biogas that is sold as renewable natural gas (RNG) or used for electricity, and the resulting fuel can also earn federal Renewable Fuel Standard RIN credits and California LCFS credits, on top of the gas revenue. The EPA's AgSTAR programme documents this, and industry reporting counts 191 manure-based RNG digesters operating in the US as of mid-2024. Caveat: what gets sold is the captured gas and its credits, not spare "capacity" as an abstract good, and economics depend on farm scale.

**What I did:** built it in Herd as "biogas sales": the first 2 Capture Systems cover on-farm energy use, and each further unit sells gas for a small per-round income. No abstract marketplace UI.

Sources: [US EPA AgSTAR, renewable natural gas from agricultural digesters](https://www.epa.gov/agstar/renewable-natural-gas-agricultural-based-adbiogas-systems); [ICCT, project economics of California RNG](https://theicct.org/wp-content/uploads/2023/05/case-studies-california-rng-outlook-2030-may23.pdf); [American Biogas Council, LCFS 101](https://americanbiogascouncil.org/101-for-low-carbon-fuel-standard/). Remove this entry once read.
