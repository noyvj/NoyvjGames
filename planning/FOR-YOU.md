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

The completion-verification audit (`planning/TODO.md` section N, "Completion audit" subsections) found a batch of round-1/round-2 items that were either built without your recorded approval (you'd said "later" and it got built anyway), or built in a way that deviates from what you actually asked for. Each one below is a real judgment call, not something I should just decide myself. Type your answer under each `**Your answer:**` line — I'll act on it and fold the result into the relevant commit/doc, then remove the question once answered.

### Q1. Continuum K7 — built despite a "later" answer

You answered "later" on this (and `LATER.md` still lists it as deferred), but it was built and checked off anyway. Ratify keeping it, or should it come back out? (This one's Continuum, so I'll hand any actual code change to Noyvj rather than touch it myself — but the decision is still yours to make either way.)

**Your answer:**

### Q2. Continuum K15 — accessibility settings don't survive save/load

The original ask was to confirm text-scale/colorblind settings persist through a real save/load. They don't — by design (a browser-level preference, not game state, same reasoning every other game's settings panel uses). Is browser-only persistence fine as-is, or do you want these round-tripped through the save state specifically for Continuum? (Continuum again — Noyvj would make the actual change.)

**Your answer:**

### Q3. Thaw G5 — no concrete "years per round" line

Only a vague info-toggle exists ("stylized several years"), never a concrete calibration line. Add a real number, or is the vague wording fine?

**Your answer:**

### Q4. Thaw G10 — dampening-delay callout keys off the wrong milestone

The callout fires off a new +15° milestone, not the +10° melt threshold your original idea referenced. Leave as-is, or also fire it on the melt-threshold delay?

**Your answer:**

### Q5. Loop H13 — milestone toasts are just achievement toasts

There's no dedicated per-chain milestone toast at 25/50/75/100% — it's standing in for achievement-unlock toasts, which don't repeat on later chains. Is that substitution fine, or do you want a real per-chain milestone toast added?

**Your answer:**

### Q6. Loop H20 — alternate goods-flavor sets have no distinct content

The "2-3 alternate flavor sets" are just the same label/item/icon picker as H2, with no actual distinct flavor text per set. Add real distinct content, or merge H20 into H2 since they're currently the same thing?

**Your answer:**

### Q7. Drift I8 — coda still shows three meter bars, not a before/after comparison

Built: the three bars stay, with a "today" marker plus a "Today X → generations from now Y" text line. Original ask sounded like a separate before/after comparison replacing the bars. Is the current reading close enough, or do you want an actual separate comparison view?

**Your answer:**

### Q8. Aftermath "E6" Civil Unrest — built despite a "later" answer

This social-event category is original idea #5, which you'd answered "later" on, but it got built and marked done anyway. Keep it, or revert? (If you keep it, I'll also fix `LATER.md`'s Aftermath "E5" entry, which currently points at nothing real.)

**Your answer:**

### Q9. SOL A18 "Reset This World" — built despite a "later" answer

Same shape as Q8: you said "later," it got built anyway (the button + its tests). Keep it, or revert?

**Your answer:**

### Q10. SOL A3 welcome-back toast — static snapshot, not a real delta

The idea was "what changed since last session"; what's built is a static snapshot ("N/8 worlds visited, X achievements") on save load, not an actual comparison against your previous visit. Is the snapshot enough, or do you want a real delta (comparing against stats stored from your last visit)?

**Your answer:**

### Q11. Canopy B3 Highland Grove — same degradation rates as the main forest

Your original idea specified the second biome should have different degradation/compounding rates. Highland Grove currently reuses the main forest's exact rates. Add a distinct rate multiplier, or is a same-rules bonus region enough?

**Your answer:**

### Q12. Aftermath E4 legacy system — count chips, not a visual marker

The idea was a visual settlement marker referencing prior runs; what's built is a per-event-type count chip row instead. Add an actual visual marker tied to run history, or is the chip row enough?

**Your answer:**

### Q13. Grid/Continuum mobile dock — docks less than asked

Grid's mobile dock only docks the Advance Round button, not the plant-build action row the original idea named (same substitution happened in Continuum, docking only Advance Season). Accept the lighter version, or extend the dock to the fuller set of controls?

**Your answer:**

### Q14. UI decluttering — Canopy and Le Champ de Mots self-audited as "not crowded"

Both were reviewed and judged not genuinely crowded, so nothing changed (Le Champ de Mots has a 722-cell farm plus many toggle buttons/panels, for reference). Do you agree, or want an actual collapse/decluttering pass applied to either anyway?

**Your answer:**

### Q15. Three loose "maybe"/"I'll let you make the call" answers

- **Continuum K9** got a "maybe" answer but sits in the task list as a plain build item now — keep as its own thing, or fold it into K16/K22?
- **Warframe tracker X23** also got a "maybe" — keep it on the list, or move it to `LATER.md`?
- **Grid C21** ("grid twin" split-view comparison) and **Tide D3** (multi-settlement mode) both got "I'll let you make the call" and are currently parked in `LATER.md` pending a real scoping conversation. Want to have that conversation now, or leave them parked?

**Your answer:**

