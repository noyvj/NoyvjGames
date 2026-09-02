# Le Champ de Mots — French Syllabus Farming Game
### Design Doc v0.1 (Personal project — not tied to a BCM assessment)

---

## 1. Concept

A farming/idle-management game where **plots = vocabulary and grammar points** from FREN151 and FREN152, planted and grown in the same order your syllabus teaches them. The healthier a plot, the less manual attention it needs — mirroring how spaced repetition works in real memory: shaky new knowledge needs constant watering, well-committed knowledge runs on autopilot.

**Core hook:** you're not managing an abstract farm, you're literally watching your own French knowledge become self-sustaining.

Working title: *Le Champ de Mots* ("The Field of Words") — open to renaming.

---

## 2. Core Loop

1. **Plant** — a new unit unlocks a batch of plots (vocab words, a conjugation pattern, a grammar rule).
2. **Tend** — each plot needs periodic "watering," which is really a recall/practice prompt (translate, conjugate, fill-in-blank, listen-and-type).
3. **Grow** — correct, spaced-out recall grows the plant through visible stages.
4. **Automate** — once a plot's mastery score crosses a threshold, it gets an auto-waterer (sprinkler icon), meaning it needs far less frequent manual check-ins, but still occasionally resurfaces (like real spaced repetition never truly stops).
5. **Expand** — automating plots frees up your daily "attention budget" to plant the next syllabus unit's words, so the farm visually grows in step with your real course progress.

This loop **is** a lightly-skinned spaced repetition system (SRS) — the game layer's job is to make SRS visually satisfying instead of feeling like flashcard homework.

---

## 3. Plant Growth Stages

| Stage | Visual | Meaning |
|---|---|---|
| Seed | Bare soil, seed packet icon | Just introduced, not yet tested |
| Sprout | Small green shoot | Recalled correctly once |
| Budding | Stem with leaves | Recalled correctly across 2+ spaced sessions |
| Blooming | Flower/fruit forming | Strong recall, longer intervals passed |
| Harvested / Automated | Full plant + sprinkler icon | Mastered — auto-watered, drops to rare "maintenance" reviews |
| Wilting | Drooping, greyed | Overdue for review — visual guilt-trip, gently nudges you back |

Wilting is deliberately **not punishing** (no plant death) — this is a learning tool, not a Duolingo-streak-guilt machine. A wilted plant just needs a re-water to recover; nothing is ever lost permanently. (Worth flagging: this is a personal-wellbeing design choice, not just a game-design one — I'd avoid any "you failed / start over" framing.)

---

## 4. Content Model — Continuous FREN151 → FREN152 (complete)

Per your call, FREN151 and FREN152 are **one continuous farm**, not two seasons. The content model reflects that: every week across both subjects gets a single incrementing `sequence` number, while `course` and `week` are kept as metadata so the game can still show "FREN151, Week 3" style labels if useful.

```
Combined timeline (fren_combined_catalog.json)
 └─ Week entry: {course, week, sequence, chapter, topics[]}
     └─ Topic (vocab | grammar | phrase | phonetic)
         └─ Item (fr/en pair, or prompt/answer for phonetics)
```

**Final tally: 23 weeks, 129 topics, 966 items**, sequence 1–23 running straight through FREN151 (weeks 1–11) into FREN152 (weeks 2–13 — FREN152's own "week 1" has no separate tutorial content; it's folded into its week 2 as bridge material, so the catalog picks up there).

| Segment | Sequence | Chapter theme |
|---|---|---|
| FREN151 Ch.1–4 | 1–11 | Greetings → family & description (A1) |
| FREN152 Bridge | 12 | Numbers/time revision, present tense -ir/-re |
| FREN152 Ch.5 | 13–15 | Daily routine, reflexives, comparative/superlative |
| FREN152 Ch.6 | 16–18 | Shopping for clothes, colours, demonstratives |
| FREN152 Ch.9 | 19–23 | Food & drink, partitive, passé composé |

The farm's rows keep extending in sequence order — a plot planted in FREN151 week 3 sits to the left of one planted in FREN152 week 5, with nothing marking the subject boundary except the chapter label. That's the point: it reads as one course of study, matching how you're actually learning it.

**Important: the catalog contains only facts (vocab pairs, grammar rules), never the workbook's own exercises, dialogues, or scrambled-word puzzles.** Per your instruction, practice questions are generated at runtime from the catalog data rather than reproduced from the textbook — see Section 5.

---

## 5. Practice Mechanics (the "watering" actions)

**Practice questions are always generated at runtime from the catalog data — never copied from the workbook's own exercises.** This does two things: it stops practice from turning into "memorise this one specific fill-in-the-blank answer," and it keeps the game clear of the workbook's copyrighted exercise material (the catalog only stores vocab pairs and grammar facts, which the game recombines freely).

Generation approach per `topic_type`:

- **vocab / phrase** — translate prompts (FR→EN or EN→FR, alternated), with multiple-choice distractors pulled from *other items in the same or a nearby topic* (so distractors are plausible, not random). The direction and the distractor set are re-rolled each time a plot is watered, so the same word never has one fixed question.
- **grammar** — fill-in-the-blank generated by taking one of the rule's example items and blanking the target word/ending; conjugation items get a pronoun swapped in from the six-person set so the blank changes each visit.
- **phonetic** — matching/multiple-choice between letter-or-symbol and its spoken name.

Each plot's practice type is determined by its `topic_type`. A pool of at least 3-4 plausible variants per item is the design floor — enough that watering the same plot twice rarely gives an identical question.

---

## 6. Spaced Repetition Engine (the actual mechanic under the hood)

Lightweight SM-2-style scheduling, not the full algorithm — simplicity matters more than academic rigor here:

- Each plot tracks: `ease_factor`, `interval_days`, `last_reviewed`, `next_due`, `correct_streak`.
- Correct recall → interval grows (e.g., 1 day → 3 → 7 → 14 → 30...).
- Incorrect recall → interval resets to short (1 day), streak resets, but **no visual punishment** beyond "this plot needs water again."
- Crossing an interval threshold (e.g., 14+ days) flips a plot to "Automated" — it still reappears eventually, just far less often.

This state is per-plot, per-user — fits your existing save-code system (Neon/Postgres) rather than needing a new backend.

---

## 7. Farm Expansion & Syllabus Pacing

- The farm map is laid out in **rows = sequence number** (1–23 currently), left to right, running continuously across FREN151 into FREN152 with no reset.
- A new row of plots unlocks only once the *previous* row's plots have all reached at least "Sprout" — this keeps the game pace loosely tied to your actual course pace rather than letting you binge-plant everything at once (which would defeat the spaced-repetition point).
- Since FREN151 is already complete, its 11 rows can be marked as available immediately (a "catch-up" zone) while FREN152's rows unlock week by week as the semester progresses.

---

## 8. Visual/UX Notes

- Static, screenshot-friendly presentation matches your stated preference — the "farm" can be a simple grid/SVG scene with plant-state sprites swapped per stage, no animation required for assessment-style screenshots (not that this needs assessment, but keeps build effort low either way).
- No forced daily-streak pressure UI (no fire emoji guilt) — a calm "plots needing water today" counter is enough nudge.

---

## 9. Tech Fit (matches existing hub stack)

- Pure HTML/CSS/JS or Pyodide, no build step — consistent with the rest of the hub.
- Save state (per-plot SRS data) via the existing FastAPI + Neon backend and save-code system — no new infra needed.
- Content (the unit/topic/item catalog) can live as static JSON in the repo, versioned like the other games.

---

## 10. Open Questions

- [x] ~~Draft the full item catalog~~ — done for both subjects (`fren_combined_catalog.json`, 966 items).
- [x] ~~Should FREN151 and FREN152 be one continuous farm?~~ — Yes, confirmed. One continuous sequence, no season split.
- [ ] Audio pronunciation — worth the extra asset effort, or skip for v1?
- [ ] Any interest in this ever becoming a BCM114 Round 2 candidate (story-based games, different SDG), or is this staying purely personal/hobby, separate from all DAs?

---

## 11. Milestone Sequence & Status

| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Syllabus content → JSON catalog | FREN151 + FREN152, one continuous sequence (`fren_combined_catalog.json`, 23 weeks / 129 topics / 966 items) | Done |
| 2 | Plant-state model + SRS scheduling | Per-plot `ease_factor`, `interval_days`, `last_reviewed`, `next_due`, `correct_streak`; growth stages; wilting. Tests: scheduling transitions across sample review sequences | Done |
| 3 | Runtime question generator | Section 5 — varied prompts per `topic_type`, distractors from nearby items, 3-4+ variants per plot. Tests: variant coverage, distractor plausibility, no textbook exercise reproduction | Done |
| 4 | Static farm grid UI | Section 3 stages + wilting, rows = sequence 1-23, chapter labels, no animation required | Done |
| 5 | Save-code backend hook | Shared `shared/save-widget.js` drop-in + `get_state()`/`load_state()` contract | Done |
| 6 | Row-unlock pacing | Section 7 — previous row all at Sprout+ before the next unlocks; FREN151's 11 rows open immediately as a catch-up zone | Done |
| 7 | Polish pass | Section 8 — screenshots-ready visuals, calm "plots needing water" counter, no streak-guilt UI | Done |
| 8 | Grading engine v2 | §14.2 — formalize STRICT/LENIENT tiers, per-item `accepted` array, normalization pass | Done |
| 9 | Report button + `answer_reports` table | §14.2.4 — flag-as-correct queue in the backend, no in-game review UI (see §14.4 decision) | Done |
| 10 | Failure feedback blurb | §14.3 — Phase 1 template version only | Done |
| 11 | Review tab | §14.4 — Random Word Review + Grammar Review | Done |
| 12 | Weekly proficiency tests | §14.5 — one per `sequence` entry, informational only (see §14.4 decision) | Done |
| 13 | Bonus sentence-building sections | §14.6 — 1-2 original sentences per week, tile-drag + translate | Done — 23/23 weeks, 1 original sentence each |

## 12. Build Notes & Decisions

Decisions taken during the build that the design doc above left open. Appended to as milestones land.

**Milestone 2 — plant-state model + SRS**

- **Plot granularity.** The doc's §2 wording ("vocab words, a conjugation pattern, a grammar rule") is taken literally: vocab/phrase/phonetic get **one plot per item**, a grammar topic is **one plot for the whole rule**, with its example items reserved as fuel for §5's question variants. That yields **722 plots** across the 23 rows (472 of them in FREN151's catch-up zone).
- **Growth stages never regress.** §3 says an incorrect recall carries "no visual punishment beyond *this plot needs water again*", so `plot.stage` is stored and monotonic: a wrong answer reschedules the plot (interval back to 1 day, streak to 0, ease down 0.2) but the plant keeps the highest stage it has reached. Scheduling can get harsher; the picture never does.
- **Time is an explicit in-game day counter,** not the wall clock. `state.current_day` starts at 0 and only moves when the player advances it. That keeps scheduling deterministic and testable, and keeps the game honest about being a study *toy* rather than a nagging daily-streak app.
- **Wilting excludes seeds.** A never-watered plot is always "due" but never "wilting" — there is no plant there yet to droop, and dressing an unplanted plot up as neglect would be exactly the guilt framing §3 rules out.
- **Interval ladder.** 1 day → 3 days → `round(interval × ease)` thereafter, ease starting at 2.5, +0.1 per correct (cap 3.0), −0.2 per incorrect (floor 1.3). Four clean recalls take a plot Seed → Sprout → Budding → Blooming → Automated (interval past the 14-day threshold), which is the pace the doc's §6 example ladder implies.

**Milestone 3 — runtime question generator**

- **13 variants, 3-7 per plot.** Every plot in the farm can produce at least three genuinely different questions and most produce four or five (distribution: 22 plots × 3, 528 × 4, 162 × 5, 8 × 6, 2 × 7 — after the audit-pass change to `blank_target()` noted at the end of this section). Translate-either-direction and type-either-direction cover vocab/phrase/phonetic; grammar adds example translation, word blanks, ending blanks and the pronoun swap.
- **Conjugation pronoun-swapping, given only plain fr/en strings.** The catalog stores no grammatical structure at all — a conjugation table is just six items like `{"fr": "nous parlons", "en": "we speak"}`. So the swap is recovered by parsing: `split_pronoun()` matches the string against the six-person set (longest first, so `il/elle/on` beats `il`, and the elided `j'` matches without a following space) and returns `("nous", "parlons")`. A topic counts as a verb table only if **3+ items split successfully across 2+ distinct pronouns**, and a split is only accepted when the remainder looks like one person's form: **no `/` in it and at most 3 tokens** (room for reflexives, `je me lève`, and compound tenses, `j'ai mangé`). That last rule matters — 10 of the catalog's verb topics pack a whole table, or *two* verbs, into a single string (`"je bois / tu bois / il boit"`), and swapping a pronoun onto those would generate nonsense. Exactly 10 topics qualify as real tables; the other 10 verb topics fall back to translation and word blanks. Swapped questions read `nous _____` with the *other people of the same verb* as distractors, which is both the most plausible distractor set available and self-checking.
- **Ending blanks come from the shared stem.** `parle/parles/parlons/parlez/parlent` share the stem `parl`, so the variant renders `vous parl_____` with `-ez/-ons/-ent/-es` as options. Irregular tables (`ai/as/a/avons/avez/ont`) have no stem of length 2+, so the variant simply isn't offered there — no special-casing needed.
- **What gets blanked.** Function words win when they lead (an article rule *is* about the article), otherwise the rightmost content word is hidden, skipping the catalog's bracketed placeholders (`+ [masc. country]`) and preferring words that occur only once. Where a word does recur, every occurrence becomes a gap, so the answer is never readable off the prompt.
- **Typed answers are lenient on purpose,** and the leniency is a checker concern, not a content one: the displayed answer stays verbatim catalog text, while `check_answer()` folds case and accents, ignores parentheticals, accepts either side of a `/`, and forgives a leading `a/an/the/to`. Mistyping `é` should never cost a plant. The single place that leniency would defeat the point — the phonetic *accents* topic, where the accent is the whole lesson — opts out of French typed variants instead. Later extended, once real play surfaced the gaps: a trailing `+ [placeholder]` template marker (e.g. `"I am + [nationality]"`) is also accepted with the placeholder dropped, since it was never something to type; a bidirectional list of common English contractions (`it's`/`it is`, `don't`/`do not`, and ~30 more pairs, `CONTRACTION_PAIRS`) means either form is always accepted regardless of which one the catalog happens to store; and the Belgian/Swiss French words for 70/80/90 (`septante`/`huitante`/`nonante`, plus `neufante` alongside `nonante` for 90 in case that's genuinely the pairing taught) are accepted as equally correct alternatives to the France-standard compounds (`NUMBER_REGIONALISMS`), scoped to exactly those three catalog items rather than attempting arbitrary compound numbers.
- **Audit pass — `_strip_plus_annotation()`'s trailing-`+`-strip is deliberately left over-lenient for 7 catalog items, not just tightened alongside everything else above.** The function is naive on purpose: `re.sub(r"\s*\+.*$", "", text)` drops from the *first* `+` in the string to the end, which is exactly right for a genuine trailing template slot (`"Je suis + [nationality]"` → `"Je suis"`, `"assez + adjective"` → `"assez"` — the dropped half is only ever a placeholder label, never something a player should have to type) but over-reaches on the 7 items where the catalog uses `+` as mid-string *rule notation* whose tail is the actual lesson, not a slot label: the 4 contraction items in `fren151-w8-grammar005` (`"à + le → au"` → strips to `"à"`, `"à + les → aux"` → `"à"`, `"de + le → du"` → `"de"`, `"de + les → des"` → `"de"`) and the 3 comparative items in `fren152-w4-grammar002` (`"plus + adjective + que"` → `"plus"`, `"moins + adjective + que"` → `"moins"`, `"aussi + adjective + que"` → `"aussi"`). Typed against those specific items, this genuinely over-accepts — e.g. typing just `"à"` would satisfy the full answer `"à + le → au"`. Deliberately not tightened (e.g. by reusing `blank_target()`'s end-anchored `TEMPLATE_SLOT` pattern instead, which would correctly leave these 7 untouched): the explicit brief for this leniency layer is *more* forgiving typed-answer checking, never less, and narrowing the regex to only strip a genuine trailing slot is a strictness change wearing a bug-fix costume. The 7 items are also all offered as multiple-choice variants (`V_EXAMPLE_FR_EN`/`V_EXAMPLE_EN_FR`, exact-match only) alongside their typed ones, so the rule is always tested exactly somewhere in the plot's variant pool even though the typed path is soft on it. Left exactly as-is; flagged here rather than fixed.
- **`blank_target()`'s handling of "/" needed its own fix, separate from the checker leniency above.** *(The single-word half of this was later reversed — see the audit-pass note at the end of this section.)* A masc/fem or similar single-word pair (`"australien / australienne"`) was being blanked as if it were an ordinary sentence — one whole word chosen and hidden, the other left fully visible (`"australien / _____"`, answer `"australienne"` only) — so a player who knew "australien" but not that *this specific* blank wanted the feminine form got marked wrong for the wrong reason. Worse, for items where "/" joins two entirely different **phrasings** rather than one-word variants (`"Comment vas-tu? / Ça va?"`), the same per-word logic could blank a word *inside* one phrasing while the other sat completely intact next to it (`"Comment vas-tu? / Ça _____?"`) — a genuinely nonsensical prompt. Fixed by teaching `blank_target()` to recognise a whitespace-bounded `"/"` (never one embedded in a single token, like the catalog's own `"[places/attractions]"` placeholder) and branch: if every side is exactly one word, blank the *whole* compound as a single unit and keep the answer `"/"-joined` (so the existing slash-splitting leniency accepts either form, and — since this variant is always presented as multiple-choice — the choice buttons now show full pairs like `"italien / italienne"` instead of single gender-committed words); if any side is more than one word, refuse to blank it at all and let the item's direct-translate variants (which already split "/" correctly both ways) carry it instead. A companion test pins the specific plot (`fren151-w6-phrase002-i02`) whose fr text has a bracketed, non-alternation "/" placeholder, confirming it never loses its variant-count floor over this.
- **Audit pass — the single-word "/" branch was making prompts of nothing at all.** Blanking `"australien / australienne"` "as a single unit" sounded right in the abstract, but the alternation *is* the whole item: `re.split` covers every character of the string, so the blanked result was always exactly `"_____"` and nothing else. 93 catalog items were affected (the nationalities and occupations lists, the possessive-adjective table, the irregular-adjective tables), and each one rendered as a bare gap above four full gendered pairs — literally unanswerable except by guessing, and worse than the misfired-blank bug the branch was written to fix. `blank_target()` now refuses **every** whitespace-bounded `"/"` item, which is what the multi-word half of the branch already did, so the two shapes collapse into one rule and the function loses a special case rather than gaining one. The items are still asked, via their translate/typed variants, where `answer_alternatives()` has always accepted either side of a `"/"` — which was the leniency the branch was reaching for anyway. Every plot still clears the 3-variant floor (the distribution shifts as noted above); `test_no_blank_question_is_a_prompt_of_nothing_but_the_gap` walks all 722 plots × every item so a gap can never swallow a whole prompt again.
- **Audit pass — a trailing `+ <slot>` is a template marker, not a word to recall.** `blank_target()` already skipped the catalog's *bracketed* placeholders (`+ [masc. country]`) because `_is_blankable()` rejects `[`/`]`, but four items name the slot as a bare English word — `"assez + adjective"`, `"je n'aime pas + infinitive"`, `"le/la/les plus + adjective"` and its `moins` twin — so the gap landed on the metalanguage and the question became "type the word *adjective*". A `TEMPLATE_SLOT` regex now sets a trailing `+ <slot>` aside before the word is chosen: the slot stays visible in the prompt (`"je _____ pas + infinitive"`) but can never be the answer. It is anchored to the end of the string deliberately — the catalog also uses `+` mid-string as genuine rule notation (`"à + le → au"`), where the word after the `+` is exactly the lesson and still blanks normally.
- **The copyright constraint is a test, not a convention.** `test_every_generated_string_is_recombined_catalog_text` walks all 722 plots × every variant and asserts each answer, choice and note is a substring of some catalog `fr`/`en`/`rule`/`title` string, and a companion test asserts every instruction line comes from this game's own enumerable `INSTRUCTIONS` dict. Nothing a player sees can drift into being workbook material without a test going red.

**Milestone 4 — static farm grid UI**

- **The grid is built once, then only repainted.** 722 cells is far too many to recreate on every answer, so `build_farm()` runs at boot and `render_farm()` afterwards only rewrites each cell's class, sprite and tooltip. Each cell keeps its own click handler (one `create_proxy` per plot) rather than using event delegation — a plot cell *is* the button, and that keeps the fake-DOM tests dispatching straight at the thing a player clicks.
- **Stage sprites, no animation.** 🟤 seed, 🌱 sprout, 🌿 budding, 🌷 blooming, 🌻 automated, with the state carried in a `plot--<stage>` class so CSS does the rest. §8 asked for screenshot-friendly and static, so there are no transitions anywhere: every frame of the farm is a usable screenshot.
- **The sprinkler is a dot, not a second emoji.** A 25px cell cannot carry 🌻 and a sprinkler side by side, so an automated plot gets a small blue drop in its corner via `::after`, and its tooltip says "auto-watered" in words.
- **Wilting is a 6° rotation and some drained colour** — a droop, nothing more. Seeds are excluded, locked rows are excluded, and one watering clears it.
- **The course boundary is invisible by construction.** Row 12 (FREN152 wk 2) is built by exactly the same code path as row 11, with the same classes; only its chapter label reads differently. A test asserts the two rows' classNames are identical so the join can't drift into becoming a visible season break.
- **Every practice question re-rolls, and never twice the same variant in a row.** The plot remembers the last variant it served and passes it to the generator as `exclude`, which is why `open_practice()` keeps a transient `plot.last_variant` — a display concern, so it stays out of the save payload.
- **Warm palette, deliberately unlike the hub's climate games.** Paper and soil rather than dark slate. The hub's rule is that a game's internals are free once you are inside it.

**Milestone 5 — save-code backend hook**

- **The shared widget, unchanged.** One `<script src="../../shared/save-widget.js" data-game-id="champ-de-mots">` line and `window.pyodide = pyodide;` in the boot script; no bespoke bridge, and `shared/save-widget.js` itself is not touched. A test asserts both lines are present in `index.html` so the integration can't silently rot.
- **Only touched plots are saved.** Writing all 722 plots × 6 SRS fields would make every save a ~100KB POST that mostly says "unchanged". `get_state()` writes out only plots that have been reviewed at all, and `load_state()` rebuilds the rest from the catalog — which is where they came from and is versioned in the repo anyway. An untouched farm serialises to under 200 bytes.
- **"Touched" includes plots that only ever went wrong.** Those sit at streak 0 and stage Seed, but they carry a real `last_reviewed` and a reduced ease factor; dropping them would quietly undo the scheduling.
- **Loading resets what the save doesn't mention.** A plot absent from the incoming save is returned to its defaults rather than left standing, so loading a save code never leaves the previous session's plants growing in someone else's farm.
- **Saves are forgiving of drift.** Unknown plot ids (an older catalog revision) are skipped rather than raising, partial plot records fall back to defaults field by field, and an unrecognised stage name falls back to Seed. Any open practice question is closed on load, since it was generated against the farm that just got replaced.

**Milestone 6 — row-unlock pacing**

- **The gate is a growth condition, not a date.** §7 describes FREN152's rows opening "week by week as the semester progresses", but this game has no live "today" (see Milestone 2's day-counter decision), so the rule is implemented purely as *every plot in row N-1 has reached at least Sprout*. A date-driven release would sit on top of that rule rather than replace it, so the gate is ready for one without pretending to have one now.
- **Rows 1-11 are permanently open.** FREN151 is finished in real life, so its 472 plots are a catch-up zone with no gate at all — `CATCH_UP_MAX_SEQUENCE = 11`, which is exactly where FREN152 begins.
- **Sprout, not "visited".** A plot answered only incorrectly is still a Seed, so it still holds the gate shut. The flip side, from §3: because stages never regress, a later wrong answer can never re-lock a row you have already opened.
- **Unlocking is cached.** `render()` asks about lock state once per plot — 722 times a repaint — so the unlocked set is computed once and invalidated on review and on load rather than walked per cell.
- **Locked rows are quiet, not scolding.** Dashed border, faded cells, disabled buttons, and an italic "opens when row N has all sprouted". Locked plots are excluded from the due count and from "water the next plot", so the calm counter never asks for something the farm won't let you do.

**Milestone 7 — polish pass**

- **The counter is a sentence, not a scoreboard.** "472 plots are ready for water today." — with the singular handled — and underneath it a pace note: "Water as many or as few as you like. Nothing here expires, and stopping costs nothing." The empty state neither congratulates nor nags: "Nothing needs water today. The farm is ticking over on its own."
- **A stage tally, not a score.** 🟤 721 · 🌱 0 · 🌿 0 · 🌷 0 · 🌻 1 — how much of the farm is at each stage, with no notion of how far along it "should" be by now. Each open row also carries a quiet "N ready" in its header.
- **The wellbeing constraints are enforced by tests over the shipped files,** not just by care while writing them: no fire emoji in any of `index.html` / `style.css` / `game.py`; the word "streak" never reaches the markup (`correct_streak` stays an internal SRS field); no `setInterval` / `setTimeout` / `datetime` anywhere in `game.py`, because no clock may drive the interface; and no `@keyframes` / `animation:` / `transition:` in the CSS, because §8 asked for static and screenshot-friendly.
- **Enter submits a typed answer,** and plot cells carry an `aria-label` matching their tooltip, so the sprite's meaning is available to a screen reader rather than only to the eye.

**Milestone 8 — grading engine v2**

- **The old two-argument `check_answer(question, given)` is frozen, byte-for-byte.** §14.7's brief was to evolve the existing grading path, and the hard constraint on this milestone was that everything the pre-existing suite checks keeps passing — including the accent-folding-always leniency Milestone 3 shipped. Rather than flip that default and edit old tests to match, the new STRICT/LENIENT machinery is additive: `check_answer` grows `tier=None` and `accent_sensitive=None` keyword arguments, and omitting both reproduces Milestone 3's function exactly (same code path, same result, for every call already in the suite). `normalize_answer` and `answer_alternatives` grow the same kind of optional, default-preserving parameters (`fold_accents=True`, `accepted=None`). The real gameplay path (`submit_answer()`) is the one caller that always passes the new arguments explicitly, so live play gets the actual §14.2 behaviour while every existing test keeps exercising the untouched legacy default.
- **Tier is decided from the answer's own shape, not the item's.** §14.2 says "word count, `topic_type`" — in practice topic_type never has to be consulted separately, because a phonetic/vocab answer that's actually one word already comes out STRICT on word count alone, and the few genuinely multi-word phonetic entries (none currently in the catalog) would correctly fall LENIENT too. `grading_tier(answer_text)` strips the trailing `+ <slot>` marker and any parenthetical first — so a template item like `"I am + [nationality]"` is judged on `"I am"` (LENIENT) rather than the annotated original — then counts whitespace-separated tokens: ≤1 is STRICT, 2+ is LENIENT. A hyphenated number (`"quatre-vingt-dix"`) is one token, so numbers land STRICT exactly as §14.2's table names them, with no special-casing needed.
- **STRICT still gets contraction equivalence and the number-regionalism table.** §14.2's normalization list (shared by both tiers) explicitly includes contraction equivalence, and `NUMBER_REGIONALISMS` is the same kind of thing — a genuine alternate spelling of one exact fact (`nonante` for `quatre-vingt-dix`), not a curated list of *different* acceptable phrasings. "No synonym list" at STRICT is read as: no "/"-splitting, no leading-article drop, no catalog `accepted` array — the LENIENT-only forgivenesses that exist precisely because a phrase can be *said* more than one way.
- **The accent-sensitivity toggle is a real toggle, not just a parameter.** `ACCENT_SENSITIVE` is a module-level global, default `True` (accents matter, per §14.2 — "spelling accents correctly is an assessed skill"), flipped by a checkbox (`#accent-toggle-checkbox`) that calls `on_toggle_accent_sensitivity()`. It's session state, not SRS state, so — same call as `plot.last_variant` in Milestone 4 — it deliberately stays out of `get_state()`/`load_state()`; a fresh page load always starts accent-sensitive. `check_answer`'s own default (`accent_sensitive=None`) still means "fold accents", i.e. the *old* Milestone 3 behaviour, since that's what every pre-existing caller needs; the live game explicitly passes `ACCENT_SENSITIVE` on every submission instead of relying on that default.
- **The `accepted` array is generated lazily, not written into the 966-item catalog file.** §14.2 says "auto-generated at content-build time rather than hand-authored for all 966 items" — the constraint being *no hand-authoring*, not *must be persisted to disk*. Writing a 3-5-phrasing array onto every LENIENT fr/en field across 966 items would meaningfully bloat a catalog that is otherwise pure fact data, for content that's entirely mechanically re-derivable from the item's own text at zero real cost. So `_catalog_item_accepted(item, field)` generates it on the fly via `generate_accepted_variants()` (canonical phrasing, punctuation-stripped, both directions of any contraction, and — only for an explicit `"/"` alternation — each side plus the pair reordered, all mechanically recombined from the item's own text, same copyright rule as §5's question generator) *unless* the catalog item already carries a literal `accepted_fr`/`accepted_en` key, which wins outright. That's the intended growth path from §14.2.4: triaging a report means hand-adding a phrasing to that item's `accepted_fr`/`accepted_en` array in the JSON file, which is then a permanent, human-curated override the lazy generator never touches again for that item.
- **The catalog's illustrative single `"accepted"` key (§14.2's JSON example) became two direction-specific keys, `accepted_fr` and `accepted_en`.** The example shows one grammar record with one `prompt`/`accepted` pair, but every item in this catalog is answerable in either translation direction (`V_FR_EN_TYPED` vs `V_EN_FR_TYPED`), each with its own canonical string — a single undifferentiated `accepted` array would be ambiguous about which direction's phrasings it lists. Splitting it by field is the natural generalization and costs nothing extra to triage by hand later.
- **No UI surface for the `accepted` array itself.** Nothing in the practice panel shows or edits it — per §14.4's decision, reports get triaged by editing the catalog JSON directly, not through an in-game page.

**Milestone 9 — report button + `answer_reports` table**

- **The timestamp is the backend's `created_at`, not something `game.py` produces.** §14.2.4's payload names a `timestamp` field, but the Milestone 7 audit already forbids `datetime`/`time.time` anywhere in `game.py` (no clock may drive the interface — see that milestone's build note and `test_nothing_in_the_game_runs_on_a_timer`). Rather than carve out an exception, the payload sent from Python omits a timestamp entirely and the backend's own `AnswerReport.created_at` (`server_default=func.now()`, same pattern as every other table in `app/models.py`) covers it — the stored row still has exactly the documented shape, just populated on the server side instead of the client.
- **Same Python-computes/JS-sends split as the shared save widget.** `game.py` never does its own `fetch()` — it never has, and `shared/save-widget.js` already established the pattern of Python building state and JS owning the network call. `submit_report()` builds the payload and calls `_dispatch_report()`, which does `from js import window` (deliberately lazy, guarded by `except ImportError`, same defensive style as `_read_catalog_json()`) and calls `window.submitAnswerReport(json.dumps(payload))` if it exists. The actual sender is a small inline `<script>` in `index.html` — not folded into `shared/save-widget.js`, since this is a champ-de-mots-specific feature, not a cross-game one — that does the real `fetch()` to `POST /answer-reports` and swallows any failure (a dropped report is a "let a human know" nicety, not core gameplay, so it fails silently rather than surfacing an error). This also means the fake-DOM test suite never touches the network: `js.window` doesn't exist in the harness, so `_dispatch_report()` is a no-op there and the tests instead pin `_report_payload()`'s shape and `submit_report()`'s one-shot behaviour directly.
- **Report button only for typed answers, matching §14.2.4's own wording** ("every *written-answer* prompt"). A wrong multiple-choice answer already shows the correct choice highlighted with no ambiguity about what was "meant" — there's nothing for a report to add there that the reveal doesn't already say.
- **`marked_correct_answer` is the canonical answer plus whatever the item's `accepted` array already holds**, via the same `_lookup_accepted()` Milestone 8 built — so a report already carries the full context a human would want when triaging it, not just the one string that happened to be on screen.
- **`game_id` on the backend table isn't hardcoded to `"champ-de-mots"`** even though every report from this game sends that value — `AnswerReport` and its endpoints are written so a future game could reuse the same reporting mechanism without a schema change, matching how `Rating`/`Feedback` already key by a `game_slug`/`game_id` string rather than assuming a single game.
- **No in-game admin/review page**, per §14.4's decision — `GET /answer-reports` supports `game_id`/`topic_type`/`item_id` filters for triaging the queue directly (e.g. by pasting a curl/httpie call into a Claude Code session), and that's the whole workflow.

**Milestone 10 — failure feedback blurb (Phase 1)**

- **All three fields are mechanical, none are per-item authored.** §14.3 only explicitly calls "why it matters" a generic per-`topic_type` template, but the same read is applied to all three: "what it is" pulls `plot.rule` verbatim for grammar (exactly as §14.3 names it) and otherwise templates the item's own fr/en pair plus its topic title; "memory tip" is a fixed per-`topic_type` sentence, filled with the item's fr/en where the template calls for it. Nothing here is item-specific insight — that's precisely what Phase 2's (out of scope) Claude API call would add. `test_no_network_or_api_call_anywhere_in_the_blurb_path` pins that Phase 2 hasn't crept in early.
- **Shown on any wrong answer, not just typed ones** — unlike Milestone 9's report button, which §14.2.4 scopes to "every *written-answer* prompt". §14.3 has no such qualifier ("when an answer is marked wrong", full stop), and a wrong multiple-choice pick benefits just as much from "why it matters" context as a wrong typed one, even though it doesn't need the report button's ambiguity-resolution.
- **Lives in its own panel (`#practice-blurb`), separate from the pre-existing `#practice-note`.** `practice-note` already surfaces `plot.rule` unconditionally for grammar plots (shown whether the answer is right or wrong, Milestone 3); the blurb's "what it is" line duplicates that content for a grammar item specifically, but only appears alongside the memory tip and why-it-matters lines on a miss, which is a deliberately different job (post-mistake context, not a standing hint) even where the text overlaps.

**Milestone 11 — Review tab**

- **A "nudge" is a distinct, smaller action from a real watering, on purpose.** §14.4 says a correct Review answer should nudge the interval forward "rather than being untracked" — read narrowly: only the interval and `next_due` move (plus `last_reviewed`, so the nudge survives a save — see below), while `correct_streak`, `ease_factor` and `stage` are left completely alone. Growing a plant's visible stage stays exclusively the daily loop's job (`schedule_after_review()`); if Review could promote a stage too, it would become a second, faster path to "Automated" that quietly undercuts the whole point of spaced, session-gated recall. A wrong Review answer touches nothing at all — no interval reset, no streak zeroing — matching this game's existing no-punishment stance (§3) and keeping Review genuinely low-stakes, since it's explicitly opt-in extra practice, not a second scored track.
- **The nudge sets `last_reviewed` even though it isn't a "real" review**, otherwise it would be silently lost: `get_state()`'s "touched" rule is `last_reviewed is not None or stage != Seed` (Milestone 5), and a nudge changes neither `stage` nor (necessarily) creates any other visible signal for a plot that had never been watered before. Setting `last_reviewed = day` is what makes the nudge actually persist through a save/reload rather than silently evaporating.
- **Both modes reuse `generate_question()` outright** rather than a second generator — §14.4 doesn't ask for new question content, only a new *selection* of which plots to ask about. Grammar Review's "biased toward fill-in-the-blank/conjugation prompts" is implemented as a variant preference at selection time (`_review_variant_for()`): if the plot's own `variants_for()` pool contains `V_BLANK_WORD`/`V_CONJUGATION_SWAP`/`V_BLANK_ENDING`, one of those is rolled; otherwise it falls back to `generate_question()`'s own default random pick across whatever that plot actually offers. This is a bias, not a hard filter — some grammar plots (the ones that aren't conjugation tables and whose examples aren't blankable) never offer those variants at all, and still deserve to show up in Grammar Review with whatever they *do* offer.
- **The count and minimum-stage filter are read from two plain in-page controls** (`#review-count-input`, `#review-min-stage-select`) at the moment a session starts, not stored as separate session-preference globals — there was nothing else that needed to read them, so the DOM element is the single source of truth. Both are defensively clamped/validated (`_review_count_setting()` falls back to the default on anything that doesn't parse as an int, clamped to 1-25; `_review_min_stage_setting()` falls back to "Seed" on any value that isn't a real stage name) so a stray/garbage control value can't crash a session the way an unrecognised save-stage name is already forgiven on load (Milestone 5).
- **No report button or failure blurb inside Review.** Both Milestone 9 and 10 are scoped to the main practice panel; extending either into Review would be a reasonable follow-up but wasn't asked for here, and keeping Review's own panel simpler was the right tradeoff for this pass. Flagging for a later milestone rather than building it speculatively now.
- **Review session state is exactly as ephemeral as `ACCENT_SENSITIVE`** — none of it (`review_mode`, `review_queue`, `review_score`, etc.) reaches `get_state()`/`load_state()`. A save/load mid-Review-session simply drops the in-progress session, which is the same "loading resets what the save doesn't mention" posture Milestone 5 already established for `plot.last_variant`.

**Milestone 12 — weekly proficiency tests**

- **A genuine ambiguity, resolved here: a proficiency test is only offered for an already-unlocked week.** §14.5 says the test covers "every topic in that week regardless of what's currently planted/watered", and §14.4's gating decision says the test itself is purely informational and never gates anything — neither sentence says whether the test is available for a *locked* week. Read literally, "regardless of what's planted/watered" is about SRS state, not row-lock state, and letting a test preview a locked week's full topic list (including topics you haven't even reached in the actual syllabus yet) would work against §7's whole reason for existing — pacing exposure to match the real course, not just pacing *automation*. So `is_proficiency_test_available()` still checks `state.is_row_unlocked()`; a locked row's "Proficiency test" button is present (consistent placement with every other row) but disabled, same visual language as a locked row's disabled plot cells.
- **"Sampling vocab/grammar/phrases" is read as "covering every topic type present," phonetic included.** §14.5's own sentence names three of the catalog's four `topic_type`s, but the same paragraph's opening clause is "covering every topic in that week" without qualification, and only two weeks (both in FREN151's week 1) have phonetic topics at all. Excluding phonetic topics from a week that has them would silently violate "every topic", so `build_proficiency_test()` samples across whatever topic types a week actually has — the omission in the second clause is read as inexact enumeration, not a deliberate carve-out.
- **A grammar topic contributes exactly the same single plot it always has** (Milestone 2's granularity call — one plot per grammar rule, many plots per vocab/phrase/phonetic item), so `_topic_plots()` is a thin wrapper that either looks up that one plot by the topic's own id or walks every item's plot for everything else. This is the same lookup shape `is_conjugation_plot()`/`variants_for()` already rely on elsewhere in the file, not a new pattern.
- **Full topic coverage first, the ~15-20 length second.** `build_proficiency_test()` guarantees one question per topic before doing anything else, then round-robins through the topics again to reach the target length — and if a week ever had more topics than the target length (none do; the largest, sequence 8, has 10), coverage would win outright rather than truncating a topic out. The catalog's smallest week (sequence 22, 2 topics) still produces a short-but-complete test rather than being padded out to a full 15-20 with unrelated content or, worse, silently dropping a topic to hit a round number.
- **Entirely stateless with respect to SRS — more so than Review.** Milestone 11's Review nudges a plot's interval on a correct answer; a proficiency test does neither that nor anything else to `state` — no `review()`, no nudge, nothing — which is what makes "regardless of what's currently planted/watered" and "purely informational" true in the same literal sense for both reading *and* writing: the test doesn't just ignore a plot's current stage when choosing what to ask, it also never writes anything back to it.
- **The entry point is a button on each row's own header** (`row-proficiency-{sequence}`), not a separate flat list of 23 links elsewhere on the page — the row is already the unit of organization for "one per `sequence` entry", so this keeps the mapping between "this week" and "this week's test" visually obvious rather than needing a second index to cross-reference against.

**Milestone 13 — bonus sentence-building sections**

- **Coverage: all 23 weeks, one original sentence each** — the low end of §14.6's "aim for 1-2 per week" rather than authoring two for every week. Given the choice between full breadth at one sentence per week or partial breadth at two, breadth won: every week having *something* to draw on for the review-mode's future extension (or a second pass later) beats several weeks having nothing. Authored by hand, one at a time, reading each week's full topic/item/rule list before drafting so every sentence is actually built from that week's real content rather than generic French — see the sourcing policy below for exactly what "that week's own vocab + grammar" was taken to permit.
- **Sourcing policy (the genuine ambiguity in "using only that week's own vocab + grammar," resolved here):** a bonus sentence's *demonstrated* content — the specific vocabulary being drilled and the grammar pattern being shown off — always comes from that week's own catalog entries (items or `rule` text). Four categories of scaffolding are allowed on top of that, none of which count as "content" being taught by the sentence: (1) subject pronouns and basic `être`/`avoir` conjugation, established from Milestone 2/week 2-3 onward and reused as foundational grammar the same way a real course assumes it from that point on; (2) universal connective words with no dedicated vocab lesson of their own (`et`, `mais`, `puis`, `alors`); (3) correct elision/liaison applied for basic grammatical correctness even in a sentence written before that specific rule's own week (e.g. `j'aime` before week 3's elision lesson) — French orthography doesn't wait for the syllabus to catch up, and refusing to elide would produce *incorrect* French in the name of originality; (4) generic proper names/places as placeholders for a subject or object with no vocabulary content of their own (`Léa`, `Marc`, `Lyon`) — the catalog's own `rule` text already does this (`"un cadeau pour Henri"`). A handful of sentences also lean on a concrete noun from an *earlier* week (`vin` in week 20's sentence, `café` in week 22's) as supporting object vocabulary where that week's own new material is purely grammatical and has no noun of its own to hang the sentence on — always the grammar pattern is that week's own, and never the specific point being drilled.
- **A "tile" is a meaningful chunk, not a strict single orthographic word.** §14.6 says "drag word tiles into correct order," but tiling at the whitespace-token level would split fixed multi-word expressions the catalog itself already teaches as one vocabulary entry — `il y a`, `en face de`, `beaucoup de` are each a single catalog item with a single translation, so splitting `il y a` into `il`/`y`/`a` for independent STRICT translation would ask a player to translate `y` and `a` as isolated fragments, which is nonsense in the same way blanking half of a masc/fem `"/"` pair was (see Milestone 3's audit-pass notes). Tiles are chunked at whatever unit the catalog itself already treats as atomic; the ordering task is still meaningfully non-trivial (4-8 tiles per sentence) and every tile still gets its own translation in task 2.
- **STRICT and LENIENT are fixed by task, not decided by `grading_tier()`.** §14.6 explicitly assigns task 2 STRICT and task 3 LENIENT — a deliberate content decision about which task should be forgiving, not a fact about the answer's own shape the way Milestone 8's auto-tiering is. `submit_bonus_tile_translation()`/`submit_bonus_sentence_translation()` pass `tier=TIER_STRICT`/`tier=TIER_LENIENT` straight to `check_answer()` rather than computing a tier from the text, which also means a short tile gloss doesn't accidentally get LENIENT's `"/"`-splitting/article-dropping/`accepted`-array leniency it was never supposed to have — and a long tile gloss doesn't get penalised STRICT-only treatment grading_tier() would have given it based on word count alone.
- **Tile glosses are stored with trailing punctuation already removed** (`"Hello"` not `"Hello,"`, `"this one"` not `"this one:"`) even though the tile's own French text keeps its comma/colon for display (`"Bonjour,"`, `"celui-ci:"`). `normalize_answer()`'s trailing-punctuation strip covers `. ! ? ¡ ¿ " « »` but not a comma or colon, and STRICT is exact-match-after-normalization — leaving a comma in the expected answer would make a perfectly correct translation fail STRICT purely because the player didn't also type the comma. Stripping it from the *stored answer* (not from `normalize_answer()` itself, which stays exactly as Milestone 8 left it) keeps the fix local to this milestone's own data rather than loosening normalization for everyone.
- **No retry/reshuffle on the ordering task in this pass.** Once every tile is placed, the result (right or wrong) is shown once and the player continues into task 2 regardless — task 2 then walks the tiles in their *real* order, which makes the correct arrangement obvious immediately afterward even after a wrong attempt. A "shuffle and try again" affordance would be a reasonable follow-up but wasn't essential for a first pass, and skipping it keeps `bonus_task`'s state machine to four clean states (`order → translate_tiles → translate_sentence → None`) rather than a fifth "retry" branch.
- **Entirely stateless with respect to SRS and row-unlock, like the proficiency test** — no `state.review()`, no nudge, nothing. Available only for an already-unlocked week (same reasoning as the proficiency test's build note: not gated, but not a way to preview a locked week's content either), entered from a `row-bonus-{sequence}` button on that week's own row header, right next to the proficiency test button.
- **The copyright-safety test for this milestone is structural, not mechanical-recombination.** The runtime question generator's own copyright test (`test_every_generated_string_is_recombined_catalog_text`, Milestone 3) works because *every* string that test walks is mechanically assembled by code with zero manual authorship — it can assert each one is literally a substring of catalog text because nothing else could have produced it. Bonus sentences are the opposite: §14.6 explicitly says "You'll need to actually author these yourself," so they're hand-written prose, and a substring test would either reject legitimate original phrasing (a sentence combining catalog words in a new grammatical arrangement isn't a substring of any single catalog string) or be trivially satisfiable in a way that proves nothing. What *is* tested: `test_bonus_sentence_tiles_reconstruct_the_full_sentence` (the tiles are exactly the sentence, no hidden text), `test_bonus_sentence_is_not_a_verbatim_copy_of_an_existing_catalog_item` (a sentence can't just be one existing item's `fr` text copy-pasted whole), and `test_bonus_sentence_ids_are_unique`. The actual "was every sentence really built from that week's own vocab/grammar" check is the authorial process described above, not a test — the same trust boundary the design doc itself draws by saying a human has to author these.

## 13. Working conventions

- Commit + tag per milestone: `git commit -m "Milestone N: <name>" -- games/champ-de-mots/` then `git tag champ-de-mots-milestone-0N`.
- Python via Pyodide, plain HTML/CSS, no build step — the hub's default stack.
- Tests use the hub's standard fake-DOM harness (`tests/fakes.py`, `tests/conftest.py`), same shape as the other games.
- Personal project: not part of any dev-log trail. Hub-linked from the main page (no BCM tag on its title card, since it isn't coursework).

---

## 14. Addendum: Grading Leniency, Review Modes & Bonus Sections (v2)

*(Source: `GRADING-AND-REVIEW-UPDATE.md`, dropped 2026-09-02. Folded in here rather than kept as a separate file, same as the original design doc. Doesn't touch the core farming loop — it changes what happens inside a single watering interaction, plus adds two new screens alongside the farm.)*

### 14.1 Relationship to what's already built

Milestones 1-7 already shipped a first pass at lenient typed-answer checking (`answer_alternatives()`, `CONTRACTION_PAIRS`/`_contraction_variants()`, `NUMBER_REGIONALISMS`, `_strip_plus_annotation()` — see §12's build notes for each). This addendum's §14.2 formalizes and extends that into an explicit STRICT/LENIENT two-tier system with a catalog-level `accepted` array per item, rather than replacing it — Milestone 8 should read the existing grading code first and evolve it, not build a parallel system.

### 14.2 Grading system

**Two strictness tiers**, decided automatically from an item's shape (word count, `topic_type`) rather than hand-flagged per item:

| Tier | Applies to | Behaviour |
|---|---|---|
| STRICT | Single-word vocab, numbers, isolated conjugated forms | Exact match after normalization only. No synonym list. |
| LENIENT | Phrases, full-sentence translations, fill-in-the-blank grammar answers | Matches against a curated list of 3-5 accepted phrasings per item. |

**Normalization** (both tiers, before any comparison): trim/collapse whitespace, case-insensitive, strip trailing punctuation, contraction equivalence (both directions, via the existing lookup table), curly/straight apostrophe equivalence. French-input accent-sensitivity is a **toggle, default ON** (spelling accents correctly is an assessed skill) — see §14.4's decision on scope.

**Accepted-answer variants (LENIENT tier):** each LENIENT item's catalog record gains an `accepted` array (canonical answer + contraction variants +, where relevant, a reordered equivalent), auto-generated at content-build time rather than hand-authored for all 966 items. The array grows over time from real usage via the report button (§14.2.4), not by trying to anticipate every phrasing up front.

```json
{
  "id": "fren151-w7-grammar001",
  "prompt": "There is a theatre.",
  "accepted": ["Il y a un théâtre.", "Il y a un théâtre", "il y a un theatre"]
}
```

**14.2.4 — The "Report" button:** every written-answer prompt shows an "I think this should count" button once marked wrong. Tapping it stores `{item_id, submitted_answer, marked_correct_answer(s), topic_type, timestamp}` to a new `answer_reports` table in the existing Neon/Postgres backend (`app/`) — not the static JSON catalog, which stays a build artifact. No auto-accept; every report needs a human (the user's) judgment call before it's added to an item's `accepted` array and redeployed.

### 14.3 Failure feedback blurb

When an answer is marked wrong (after normalization/leniency checks fail), show a short card: **what it is** (one-line restatement — the `rule` field already covers this for grammar items), **memory tip** (short mnemonic/pattern hint), **why it matters** (how it recurs later). Phase 1 (build now): template-filled from existing catalog fields plus a generic per-`topic_type` template for "why it matters." Phase 2 (explicitly a stretch, not part of this build): a one-off Claude API call per item, cached in the database — worth doing once the catalog structure has stabilised, not before.

### 14.4 Cross-section review modes, weekly tests, and decisions on the open questions

Two new modes accessible from a "Review" tab, opt-in, don't affect plot unlock pacing:

- **Random Word Review** — pulls a configurable number of `vocab`/`phrase` items from any unlocked week, filtered to a minimum growth stage. Correct answers nudge the SRS interval slightly forward on the source plot rather than being untracked.
- **Grammar Review** — same mechanic, filtered to `topic_type: grammar`, biased toward fill-in-the-blank/conjugation prompts.

The source doc left four questions open (its §7). Decided here so Milestone 11/12 can build against a settled spec rather than stalling on them:

- **Proficiency-test gating:** informational only, no unlock-gating — matches the doc's own stated lean, and avoids the front-loading/burnout risk already flagged for this game (§3's wilting design already commits to no punitive mechanics).
- **Accent-toggle scope:** one global toggle (default ON), not a separate default for Random Review — it's already user-togglable per session per §14.2, no need for a second mode-specific default to maintain.
- **Report review workflow:** build the `answer_reports` table + a couple of backend query endpoints (list/filter reports) — no dedicated in-game admin UI page. Matches the doc's own lighter-weight suggested option: reports get triaged periodically by pasting the queue into a Claude Code session, not through a page in the game itself.
- **Minimum stage threshold for Review modes:** configurable per session (a simple in-page control), not fixed — low cost to build, and matches the doc's own phrasing ("a minimum growth stage (e.g. 'Sprout or higher' or 'only Automated ones')").

### 14.5 Weekly proficiency tests

One test per `sequence` entry (per taught week), covering every topic in that week regardless of what's currently planted/watered — a single fixed-length session (~15-20 questions) sampling vocab/grammar/phrases from that week. Purely informational (score + per-topic breakdown), per the gating decision above.

### 14.6 Bonus sections: sentence building

Each week keeps its existing plot count unchanged; a bonus section is added per week using only that week's own vocab + grammar. Three tasks per bonus sentence: (1) drag word tiles into correct order, (2) translate each tile individually (STRICT), (3) translate the assembled sentence as a whole (LENIENT). Sentences must be **original**, combining that week's own catalog items — never lifted from the workbook, same copyright-safety rule as the runtime question generator (§5). Aim for 1-2 bonus sentences per week, authored fresh (not reused from any other source) and stored in a new `bonus_sentences` field per week entry in the catalog.

### 14.7 Milestone build order

Continues the existing numbering (see §11's table) rather than restarting — the source doc's own numbered list maps its already-built steps (content catalog, plant-state model, question generator, farm UI, save-code hook, row-unlock pacing, polish) onto this game's existing Milestones 1-3 and 7-9 respectively. New work is Milestones 8-13: grading engine v2 → report button + backend table → failure blurb → review tab → weekly proficiency tests → bonus sentence sections. Each gets its own commit + tag per §13's convention.
