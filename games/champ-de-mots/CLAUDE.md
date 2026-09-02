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

## 12. Build Notes & Decisions

Decisions taken during the build that the design doc above left open. Appended to as milestones land.

**Milestone 2 — plant-state model + SRS**

- **Plot granularity.** The doc's §2 wording ("vocab words, a conjugation pattern, a grammar rule") is taken literally: vocab/phrase/phonetic get **one plot per item**, a grammar topic is **one plot for the whole rule**, with its example items reserved as fuel for §5's question variants. That yields **722 plots** across the 23 rows (472 of them in FREN151's catch-up zone).
- **Growth stages never regress.** §3 says an incorrect recall carries "no visual punishment beyond *this plot needs water again*", so `plot.stage` is stored and monotonic: a wrong answer reschedules the plot (interval back to 1 day, streak to 0, ease down 0.2) but the plant keeps the highest stage it has reached. Scheduling can get harsher; the picture never does.
- **Time is an explicit in-game day counter,** not the wall clock. `state.current_day` starts at 0 and only moves when the player advances it. That keeps scheduling deterministic and testable, and keeps the game honest about being a study *toy* rather than a nagging daily-streak app.
- **Wilting excludes seeds.** A never-watered plot is always "due" but never "wilting" — there is no plant there yet to droop, and dressing an unplanted plot up as neglect would be exactly the guilt framing §3 rules out.
- **Interval ladder.** 1 day → 3 days → `round(interval × ease)` thereafter, ease starting at 2.5, +0.1 per correct (cap 3.0), −0.2 per incorrect (floor 1.3). Four clean recalls take a plot Seed → Sprout → Budding → Blooming → Automated (interval past the 14-day threshold), which is the pace the doc's §6 example ladder implies.

**Milestone 3 — runtime question generator**

- **13 variants, 3-7 per plot.** Every plot in the farm can produce at least three genuinely different questions and most produce four or five (distribution: 15 plots × 3, 421 × 4, 276 × 5, 8 × 6, 2 × 7). Translate-either-direction and type-either-direction cover vocab/phrase/phonetic; grammar adds example translation, word blanks, ending blanks and the pronoun swap.
- **Conjugation pronoun-swapping, given only plain fr/en strings.** The catalog stores no grammatical structure at all — a conjugation table is just six items like `{"fr": "nous parlons", "en": "we speak"}`. So the swap is recovered by parsing: `split_pronoun()` matches the string against the six-person set (longest first, so `il/elle/on` beats `il`, and the elided `j'` matches without a following space) and returns `("nous", "parlons")`. A topic counts as a verb table only if **3+ items split successfully across 2+ distinct pronouns**, and a split is only accepted when the remainder looks like one person's form: **no `/` in it and at most 3 tokens** (room for reflexives, `je me lève`, and compound tenses, `j'ai mangé`). That last rule matters — 10 of the catalog's verb topics pack a whole table, or *two* verbs, into a single string (`"je bois / tu bois / il boit"`), and swapping a pronoun onto those would generate nonsense. Exactly 10 topics qualify as real tables; the other 10 verb topics fall back to translation and word blanks. Swapped questions read `nous _____` with the *other people of the same verb* as distractors, which is both the most plausible distractor set available and self-checking.
- **Ending blanks come from the shared stem.** `parle/parles/parlons/parlez/parlent` share the stem `parl`, so the variant renders `vous parl_____` with `-ez/-ons/-ent/-es` as options. Irregular tables (`ai/as/a/avons/avez/ont`) have no stem of length 2+, so the variant simply isn't offered there — no special-casing needed.
- **What gets blanked.** Function words win when they lead (an article rule *is* about the article), otherwise the rightmost content word is hidden, skipping the catalog's bracketed placeholders (`+ [masc. country]`) and preferring words that occur only once. Where a word does recur, every occurrence becomes a gap, so the answer is never readable off the prompt.
- **Typed answers are lenient on purpose,** and the leniency is a checker concern, not a content one: the displayed answer stays verbatim catalog text, while `check_answer()` folds case and accents, ignores parentheticals, accepts either side of a `/`, and forgives a leading `a/an/the/to`. Mistyping `é` should never cost a plant. The single place that leniency would defeat the point — the phonetic *accents* topic, where the accent is the whole lesson — opts out of French typed variants instead. Later extended, once real play surfaced the gaps: a trailing `+ [placeholder]` template marker (e.g. `"I am + [nationality]"`) is also accepted with the placeholder dropped, since it was never something to type; a bidirectional list of common English contractions (`it's`/`it is`, `don't`/`do not`, and ~30 more pairs, `CONTRACTION_PAIRS`) means either form is always accepted regardless of which one the catalog happens to store; and the Belgian/Swiss French words for 70/80/90 (`septante`/`huitante`/`nonante`, plus `neufante` alongside `nonante` for 90 in case that's genuinely the pairing taught) are accepted as equally correct alternatives to the France-standard compounds (`NUMBER_REGIONALISMS`), scoped to exactly those three catalog items rather than attempting arbitrary compound numbers.
- **`blank_target()`'s handling of "/" needed its own fix, separate from the checker leniency above.** A masc/fem or similar single-word pair (`"australien / australienne"`) was being blanked as if it were an ordinary sentence — one whole word chosen and hidden, the other left fully visible (`"australien / _____"`, answer `"australienne"` only) — so a player who knew "australien" but not that *this specific* blank wanted the feminine form got marked wrong for the wrong reason. Worse, for items where "/" joins two entirely different **phrasings** rather than one-word variants (`"Comment vas-tu? / Ça va?"`), the same per-word logic could blank a word *inside* one phrasing while the other sat completely intact next to it (`"Comment vas-tu? / Ça _____?"`) — a genuinely nonsensical prompt. Fixed by teaching `blank_target()` to recognise a whitespace-bounded `"/"` (never one embedded in a single token, like the catalog's own `"[places/attractions]"` placeholder) and branch: if every side is exactly one word, blank the *whole* compound as a single unit and keep the answer `"/"-joined` (so the existing slash-splitting leniency accepts either form, and — since this variant is always presented as multiple-choice — the choice buttons now show full pairs like `"italien / italienne"` instead of single gender-committed words); if any side is more than one word, refuse to blank it at all and let the item's direct-translate variants (which already split "/" correctly both ways) carry it instead. A companion test pins the specific plot (`fren151-w6-phrase002-i02`) whose fr text has a bracketed, non-alternation "/" placeholder, confirming it never loses its variant-count floor over this.
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

## 13. Working conventions

- Commit + tag per milestone: `git commit -m "Milestone N: <name>" -- games/champ-de-mots/` then `git tag champ-de-mots-milestone-0N`.
- Python via Pyodide, plain HTML/CSS, no build step — the hub's default stack.
- Tests use the hub's standard fake-DOM harness (`tests/fakes.py`, `tests/conftest.py`), same shape as the other games.
- Personal project: not part of any dev-log trail. Hub-linked from the main page (no BCM tag on its title card, since it isn't coursework).
