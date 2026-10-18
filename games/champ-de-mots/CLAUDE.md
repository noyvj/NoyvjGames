# Le Champ de Mots — French Syllabus Farming Game
### Design Doc v0.1 (Personal project — not tied to a BCM assessment)

---

## 1. Concept

A farming/idle-management game where **plots = vocabulary and grammar points** from FREN151 and FREN152, planted and grown in the same order your syllabus teaches them. The healthier a plot, the less manual attention it needs — mirroring how spaced repetition works in real memory: shaky new knowledge needs constant watering, well-committed knowledge runs on autopilot.

**Core hook:** you're not managing an abstract farm, you're literally watching your own French knowledge become self-sustaining.

Working title: *Le Champ de Mots* ("The Field of Words") — open to renaming.

---

## Standing constraints (a short summary of design-doc sections 3 to 8; the full text is in NOTES.md)

- Wellbeing: a plant never dies and its growth stage only ever moves up. A wrong answer only reschedules the plot (interval back to 1 day). No "failed", "start over", streak or fire-emoji framing anywhere on the page.
- Content: the catalog (`fren_combined_catalog.json`) holds only facts (vocab pairs, grammar rules). Practice questions are generated at runtime from it, never copied from the workbook's own exercises.
- Nothing on the farm runs on a timer or an animation; the arcade minigames (`champ_minigames_*`) are the only timed things. All 23 rows are open from the start (no pacing gate).
- Every practice or minigame action must feed `record_practice(mode, correct)` so it visibly counts (see "Practice rule" below); the ledger never changes SRS state.
- Saves: `get_state()`/`load_state()` is the shared save widget's contract; old saves must load unchanged.

## 11. Milestone Sequence & Status

| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | Syllabus content → JSON catalog | FREN151 + FREN152, one continuous sequence (`fren_combined_catalog.json`, 23 weeks / 138 topics / 1047 items) | Done |
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
| 14 | Combo bonus + confidence rating | Correct-answer combo speeds SRS growth; self-rated confidence sharpens the wrong-answer penalty | Done |
| 15 | Deliberate interleaving in Review | Stratified round-robin by plot stage in place of a plain shuffle | Done |
| 16 | Adaptive distractor difficulty | Budding+ plots draw harder, similarity-ranked multiple-choice distractors | Done |
| 17 | Cultural notes toggle | Surfaces the cultural-notes half of `fren_supplementary_notes.json`, gated to unlocked rows | Done |
| 18 | Progress dashboard | Row mastery, weakest topics, days-since-last-touch — read-only, no SRS mutation | Done |
| 19 | "Weeds" plot state | Distinct overlay for known French mix-ups (à/a, où/ou, etc.), takes precedence over wilting | Done |
| 20 | Personal error-pattern digest | Classifies why a typed miss happened (mix-up / accent slip / typo / genuine miss); surfaces on the dashboard | Done |
| 21 | Gender-tagging drill | `V_GENDER_TAG` variant tests le/la recall apart from meaning, for unambiguous-article vocab items | Done |
| 22 | Liaison/elision practice | Hand-authored 10-question quiz grounded in the TTS pronunciation watchlist | Done |
| 23 | Achievements (game-local slice) | Plots-automated + full-weeks-automated tiers; needed no new save state | Done — retrofitted into the hub-wide cross-game pattern by Milestone 31 |
| 24 | Mispronunciation-risk report button | Flags known mispronunciation-trap items from the TTS watchlist for human triage | Done |
| 25 | Bugfix: typed-answer inputs weren't clearing between questions | Reset the input's value at every "move on" path (Review/Proficiency/Bonus), not just the main panel | Done |
| 26 | Report buttons extended to Review, Proficiency, and Bonus | Shared payload builders reused across all four practice surfaces | Done |
| 27 | "Greetings & Basics Blitz" arcade minigame | 60-second beat-the-clock vocab match, sequence 1-11 | Done |
| 28 | "Verb Racer" arcade minigame | Grammar-only lane race vs. a fixed-pace rival, sequence 12-15 | Done |
| 29 | "Boutique Dash" arcade minigame | Colour+garment order-rush with a patience clock, sequence 16-18 | Done |
| 30 | "Café Rush" arcade minigame | Food/drink order-rush with a passé-composé confirmation twist every 3rd customer, sequence 19-23 | Done — completes the 4-part arcade family |
| 31 | Achievements retrofit into the hub-wide cross-game pattern | Static `achievements.json` manifest, `achievements_earned` save field, unlock toast, hub-dashboard link | Done |
| 32 | Visual-style switcher | Low-poly / text-based / cartoon / high-def chrome-and-palette themes, desktop-only, `localStorage`-persisted | Done |
| 33 | "What's New" in-game changelog panel | 12-entry curated highlights list (site-wide K16 goal) | Done |
| 34 | L4a: remove the row-unlock pacing gate | Every row unlocked unconditionally from the start; repaired the test suite a session-limit interruption left broken | Done |
| 35 | R2-L1b: practice-progress ledger | Every practice mode (4 minigames, gender drill, liaison, proficiency tests, bonus sentences) feeds one capped, saved ledger shown as a header "Practice score" tile + dashboard section; never touches SRS | Done |
| 36 | V-AB-1: first-run visual-style picker | Four-option dialog shown once when no style is stored (desktop only), skippable to High-def, honest that three styles are CSS chrome | Done |
| 38 | Study tools batch 1 (Round 3 L-9, L-28, L-24, L-20): exam-date planner + header exam countdown, farm filter/sort, on-screen accent bar | Done (2026-10-07) — see "Study tools batch 1" at the end of this file; L-18, L-19, L-13, L-8, L-29, L-21, L-26, L-27, L-17, L-25 NOT built yet |
| 37 | Desktop boot (PC version plan): `pc.html` generated from `index.html`, the farm as a self-scrolling stage, readout chips, a side column of watering, study and practice-game buttons, every question flow and minigame as a window | Done (2026-10-07) — see "Desktop boot" at the end of this file |
| 39 | Watering rule (2026-10-08): the first correct answer for a plot each in-game day, from any plot-linked activity, waters it; later ones nudge | Done — see "Watering versus nudging" at the end of this file |
| 40 | Water options chooser: next plot, a week, a topic, wilting first, quick multiple choice, typing, listening, by minigame (each with a live count) | Done — see "Water options" |
| 41 | Minigame audit: every game names the plot each answer waters, waters at least two plots a play, feeds the ledger | Done — see "Minigame audit and coverage" |
| 42 | Four new minigames (Word Match, Grammar Gaps, Listening Pick, Word Order Race) so every plot has an arcade game | Done — see "New minigames" |
| 43 | Slower / Normal / Faster for all nine minigames | Done — see "Minigame difficulty" |
| 44 | Progressive question format: multiple choice for a new plot, typed answers more and more as it grows; "Always multiple choice" setting | Done — see "Progressive question format" |
| 45 | Round 2 batch (2026-10-09): answer-report sweep (FY-8, FY-14), the full 16-combination contrast scan (LC-1), Farm shop with coins and plot skins (L-1 part), Faux Amis false-friends game and farm badge (L-15, L-16) | Done — see "Round 2 batch (2026-10-09)" at the end of this file |

## File map (read this before editing; the game is split into small files, 2026-10-18)

The old single `game.py` (420 KB), `minigames.py` (144 KB), `index.html` and `style.css` were cut into files a small model can read whole. Nothing the AI may edit passes about 14,000 estimated tokens (bytes divided by 4) except `index.html` (about 75 KB of markup, capped by `tests/test_file_sizes.py`); that test fails if a file grows past its limit (the generated `pc.html` and `study-table.html`, `.json` data and this notes file are exempt). Behaviour did not change: every name the old `game.py` and `minigames.py` had is still `game.<name>` / `minigames.<name>`, saves are byte-identical, the page looks identical. To find a function, `grep -n "def name" champ_*.py`.

**Python, the farm.** `game.py` is only the entry point: it imports the modules, re-exports every name (`game.get_state`, `game.render`, `game.FarmState` ... tests and the page use them) and calls `setup()`. The modules below are listed in dependency order (a module only imports from the ones before it). **The module list lives in two places that must match**: `_PART_NAMES` in `game.py` (and in `minigames.py` for the minigames' modules) and `CHAMP_PY_MODULES` at the top of `boot.js` (the page fetches each file and writes it into Pyodide's file system before it runs `game.py`); a new module also goes into `sw.js` and `offline-manifest.json`. `tests/test_module_list.py` checks the files on disk, the lists and the import order.

| File | Size | What it holds, and when to ask for it |
|------|------|---------------------------------------|
| `champ_rules.py` | 8 KB | Le Champ de Mots' fixed numbers and small tables: the spaced-repetition constants, the growth stages, the file names, the practice-ledger modes and caps and the exam-planner defaults. Pure data. Ask for this file to change a number. |
| `champ_runstate.py` | 13 KB | The live state: every module variable that gets REPLACED while playing (`current_question`, `review_queue`, `combo_count`, the panel-open flags ...), plus `LIVE_NAMES`. Ask for it to add a new rebound variable. |
| `champ_catalog.py` | 5 KB | Loading the course data: the combined FREN151/FREN152 catalog, the supplementary notes (cultural notes, liaison questions, pronunciation risks) and the chapter titles. Read once when the game starts. |
| `champ_model.py` | 13 KB | The farm itself: Plot, Row and FarmState (the plots, the spaced-repetition scheduler, the unlock chain), the one live `state`, and the plot-record helpers the save code uses. Ask for this file to change how a plot grows or is scheduled. |
| `champ_qbuild.py` | 21 KB | Building questions: normalising answers, blanking a word, finding look-alike distractors, the pools they come from and variants_for() (which kinds of question a plot offers). |
| `champ_questions.py` | 10 KB | generate_question(): turns a plot and a question kind into the prompt, choices and answer a player sees, plus the progressive choice-versus-typed schedule (wants_typed). |
| `champ_grading.py` | 21 KB | Grading: the accepted spellings of an answer, strict and lenient tiers, the weeds look-alike table, the error-pattern digest and check_answer(). |
| `champ_labels.py` | 7 KB | Fixed wording for the farm (stage icons and labels, legend and status messages, report button labels) and the failure feedback blurb. |
| `champ_util.py` | 2 KB | Tiny helpers every panel uses: _element() (look up a page element), pref_get()/pref_set() (per-browser preferences) and the speech hooks speech_available()/speak_french(). |
| `champ_stats.py` | 5 KB | Read-only counts over the farm: row mastery, weakest topics, days since last touch, stage distribution, automated plot counts and the topic/plot lookups the review and proficiency modes share. |
| `champ_calendar.py` | 8 KB | The real calendar day (study_today), the study-days record and the study calendar panel. |
| `champ_points.py` | 12 KB | The practice-progress ledger (record_practice and the header score), the study buddy, the golden plot of the day and the daily goals. Every practice mode feeds record_practice(). |
| `champ_reportlog.py` | 5 KB | The 'My Reports' panel: a small dated feed of every report the player has sent (built on shared/narrative_log.py). |
| `champ_watering.py` | 10 KB | The one watering rule (water_plot: the first correct answer for a plot each day waters it, a later one nudges it), today's tally, and the coins and plot skins that watering earns. |
| `champ_growth.py` | 9 KB | Plot-growth credit: which practice surfaces grow plots, the 'Plot growth credited' lines and the markers on each panel. |
| `champ_practice_base.py` | 4 KB | State shared by the practice panel and its helpers (the plot cells, the confidence tally, the per-row clean-run badge) and close_practice(). |
| `champ_reports.py` | 6 KB | The 'I think this should count' and pronunciation-concern reports for the practice panel, and the helpers every other mode's report buttons reuse (payload shapes and the dispatch to the page). |
| `champ_leech.py` | 9 KB | Stubborn plots (leeches): detecting and resting them, the re-teach lines, the session highlights and the weak-items CSV and Anki exports. |
| `champ_semesters.py` | 10 KB | Semester bands on the farm: grouping the weeks under FREN151 and FREN152 headings, their progress and collapsing. |
| `champ_arrange.py` | 9 KB | Farm filter and sort: which plots and weeks are shown, in what order, and the CSS classes and tooltip each plot cell gets. |
| `champ_legend.py` | 15 KB | 'What the colours and icons mean': the list of every indicator on the farm and how a sample of each is drawn. |
| `champ_water_pool.py` | 6 KB | Which plots each 'Water options' choice can water right now (next, week, topic, wilting, multiple choice, typed, listening) and the constants those sessions use. |
| `champ_review_base.py` | 10 KB | The Review tab's settings and candidate lists: random word, grammar, marathon, cram and weak-spot candidates. |
| `champ_review.py` | 20 KB | The Review tab: running a review session (start, answer, next, close), its report buttons, the shareable result and the Review panel's drawing. |
| `champ_proficiency.py` | 14 KB | Weekly proficiency tests: building a test for a week, answering it, its report buttons and the panel's drawing. |
| `champ_bonus.py` | 25 KB | Bonus sentence sections: order the tiles, translate each tile, translate the whole sentence; their report buttons and the panel's drawing. |
| `champ_builder.py` | 7 KB | The freeform sentence builder: put the tiles of any unlocked week's bonus sentence in order. |
| `champ_listening.py` | 7 KB | Listening practice: the browser's own voice reads a French sentence, the player picks what it means. |
| `champ_conversation.py` | 13 KB | The conversation simulator: short scripted exchanges that chain phrases from several topics. |
| `champ_placement.py` | 21 KB | The placement test: a mixed test over the whole syllabus that suggests where to start, plus applying its plan. |
| `champ_examformats.py` | 7 KB | The exam practice formats panel (clock reading, true or false, rewriting, pronoun answers, reciprocal pronouns, pair questions). The questions themselves come from formats.py. |
| `champ_phrasebook.py` | 5 KB | The personal phrasebook: bookmark plots, practise just that list. |
| `champ_dashboard.py` | 15 KB | The progress dashboard, the spaced-repetition explainer, the grammar deep-dive and the cultural notes panel. |
| `champ_liaison.py` | 8 KB | Liaison and elision practice: a short fixed quiz over hand-written questions. |
| `champ_achievements.py` | 15 KB | Achievements (checks, progress, panel, unlock toast) and the in-game 'What's New' changelog panel. |
| `champ_planner.py` | 12 KB | The exam planner: the exam date, minutes a day, the projection of how many plots will be automated, and the header countdown. |
| `champ_accent.py` | 4 KB | The on-screen accent bar under each typed-answer box. |
| `champ_prefs.py` | 2 KB | The two settings toggles: accent sensitivity and 'Always multiple choice' (plus the plain-words format schedule). |
| `champ_shop.py` | 4 KB | The Farm shop panel (skins bought with coins). The coin rules live in champ_watering. |
| `champ_practice.py` | 19 KB | The main practice panel: opening a plot, answering it, the Next plot and Next day buttons, slip forgiveness and the panel's drawing. |
| `champ_wateropts.py` | 6 KB | The 'Water options' chooser: starting a session of the chosen kind, the listening buttons and the panel's drawing. |
| `champ_farm.py` | 13 KB | The farm grid: building it once, drawing every plot cell and the header status tiles. |
| `champ_renderer.py` | 3 KB | render(): the one function that redraws the whole page. It also hands render() to every earlier module that calls it. |
| `champ_setup.py` | 18 KB | setup(): wires every button on the page to its handler, hands the farm to the minigames and draws the first screen. |
| `champ_savegame.py` | 9 KB | Saving: get_state() and load_state() (the shared save widget's contract) and resume_note(). |
| `game.py` | 6 KB | Entry point and wiring: the minigames/formats imports, the tick aliases the page calls by name, `_PART_NAMES`, the re-export loop, `_GameModule`, and the `setup()` call. Ask for it to add a module. |

**Python, the arcade minigames** (`champ_minigames_*.py`, written by `minigames.py` the same way):

| File | Size | What it holds, and when to ask for it |
|------|------|---------------------------------------|
| `champ_minigames_rules.py` | 1 KB | Tuning numbers for the five timed arcade games (durations, lives, base points, patience, combo steps). Pure data. |
| `champ_minigames_runstate.py` | 8 KB | The minigames' live state: every minigame variable that gets REPLACED while playing (`blitz_active`, `racer_question`, `cafe_stage`, the wiring `_farm` ...), plus `LIVE_NAMES`. |
| `champ_minigames_core.py` | 14 KB | Shared pieces of every minigame: the wiring game.py hands in (configure), growth credit and ledger helpers, the row-unlock checks, the difficulty setting, labels and the answer-area builder. |
| `champ_minigames_blitz.py` | 14 KB | Greetings & Basics Blitz (weeks 1-11): a 60-second rapid-fire translation game with lives and a combo. |
| `champ_minigames_racer.py` | 13 KB | Verb Racer (weeks 12-15): pick the right verb form to outrun a rival. |
| `champ_minigames_boutique.py` | 17 KB | Boutique Dash (weeks 16-18): serve clothing orders before the customer's patience runs out. |
| `champ_minigames_cafe.py` | 20 KB | Café Rush (weeks 19-23): serve food orders, with a passé composé twist every few customers. |
| `champ_minigames_sprint.py` | 13 KB | Passé Composé Sprint (weeks 21-23): a timed fill-the-gap game with lives and a combo. |
| `champ_minigames_arcade.py` | 9 KB | The base class the four newer games share (panel, start and close, timer, difficulty, summary) plus the speech hooks. |
| `champ_minigames_games.py` | 24 KB | Word Match, Grammar Gaps, Listening Pick and Word Order Race, each a small subclass of the shared base class. |
| `champ_minigames_amis.py` | 16 KB | Faux Amis: reading the false-friends list from the live page, caching it, and the game built on it. |
| `champ_minigames_registry.py` | 8 KB | render() and setup() for all minigames, the list of newer games, the tick functions the page calls every second, and the 'water by minigame' helpers. |
| `minigames.py` | 6 KB | Entry point of the arcade games: `_PART_NAMES`, the re-export loop and `_MinigamesModule`. `game.py` imports it and calls `configure()`, `configure_speech()` and `setup()` on it. |
| `formats.py` | 20 KB | The exam practice formats' questions (pure, no page). Not split. |

**State-handling rule.** A module variable that some function REPLACES (`current_question = ...`, `combo_count += 1`) lives only in `champ_runstate.py` (`champ_minigames_runstate.py` for the minigames) and every other module reads and writes it as `runstate.<name>` (each starts with `import champ_runstate as runstate`). Never `from champ_runstate import current_question`: that copies the name once and goes stale (a test checks this). Lists, dicts and sets that are only changed in place stay in the module that owns them. A new rebound variable goes into the state module AND its `LIVE_NAMES` tuple; `game.<name>` reads and writes of those names are forwarded to it. `render()` is defined in `champ_renderer.py` (after every panel's own `render_<panel>()`), so each earlier module that calls it holds a `render = None` placeholder that `champ_renderer.py` fills in when it loads; `minigames` has the same pattern with `champ_minigames_registry.py`. Tests that patch a name (`game_env.module.some_function = fake`) work: the module's `__setattr__` copies the new value into every module that holds that name.

**Page.** `index.html` is the markup (about 75 KB: one page with some forty panels and no code left in it to move; the generated `pc.html` is the same page plus the Desktop shell, so never edit it). Its scripts are separate files loaded in the same order as before: `tutorial-steps.js` (the walkthrough text), `boot.js` (Pyodide boot, the module list and the one-second minigame tick), `page-hooks.js` (speech, preferences, real date, downloads, report sender), `toast-hook.js`, `result-copy.js`, `shortcuts.js`, plus the older `visual-style.js` and `pc.js`. The stylesheet is cut into ordered parts that must stay in this order (the order is the cascade): `style-1-base.css` (layout, status tiles, practice panel, the farm and its legend, info toggles), `style-2-panels.css` (the practice-panel upgrade: hero badges, question card, dashboard, achievements and toast, choice tiles, buttons), and last `style.css` (the console look, then the later additions: study calendar, phrasebook, planner, filters, accent bar, shop skins, semester bands, legend guide, exam formats; it holds the site-wide `[hidden] { display: none !important; }` rule that `shared/tests/test_hidden_attribute_rule.py` looks for, and `scripts/generate-pc-pages.py` anchors on its link). `minigames.css`, `visual-styles.css` and `pc.css` are unchanged. Put new rules in the part for their area. After changing `index.html`, `pc-config.json`, `pc.js` or `pc.css`, regenerate `pc.html` with `python3 scripts/generate-pc-pages.py`.

**Tests read the pieces through `tests/pagefiles.py`:** `style_css()` (the three stylesheet parts), `page_text(page)` (the page plus every local script it loads), `game_source()` (`game.py` plus every `champ_*.py` of the farm) and `minigames_source()`, so a rule or function can move between files without breaking a test. `tests/conftest.py` forgets the `champ_*` modules between tests (each binds `document` and `create_proxy` from that test's fake `js`).

---

## For the local AI (exact names, all grepped against the code on 2026-10-18)

Le Champ de Mots has no `handle()` action list and no view dict: Python builds the farm (`champ_model.state`, a `FarmState` of `Plot`s) and writes the DOM; the page reads that. Never invent a name; grep it first.
- **Entry points.** Every button is wired once in `setup()` in `champ_setup.py` (`_element(id).addEventListener("click", create_proxy(handler))`; the minigames wire theirs in `champ_minigames_registry.py`). Main ids: `water-next-button`, `next-day-button`, `practice-panel` (`practice-prompt`, `practice-answer-input`, `practice-submit-button`, `practice-next-button`, `practice-close-button`), `review-toggle-button`, `water-options-toggle-button`, `dashboard-toggle-button`, `farm-filter-select`, `farm-sort-select`; a panel is opened by its `*-toggle-button`.
- **Engine verbs.** `generate_question(plot, rng, variant, exclude, farm, format)` (`champ_questions.py`) returns a dict with `plot_id variant topic_type context instruction prompt note mode choices answer`; `check_answer(question, given, tier, accent_sensitive)` (`champ_grading.py`); `water_plot(plot, combo, confidence)` (`champ_watering.py`, the ONE watering rule: first correct answer per plot per day waters, later ones nudge); `state.review(plot_id, correct, day, combo, confidence)`, `state.due_plots()`, `state.next_due_plot()`, `state.advance_day()`; `record_practice(mode, correct, points)` (`champ_points.py`).
- **Python the page may call** (`window.pyodide.globals.get(name)`): `get_state`, `load_state`, `share_result`, `resume_note`, `minigame_run_active`, and the once-a-second ticks `blitz_tick sprint_tick racer_tick boutique_tick cafe_tick pairs_tick gaps_tick listenpick_tick wordorder_tick amis_tick` (re-exported in `game.py`). To give JS a new value add a function; never read a Python variable by name from JS (replaced variables live in `champ_runstate.py`).
- **get_state()** (`champ_savegame.py`) always writes `version current_day plots error_patterns practice_ledger achievements_earned`; only when not default: `report_log study_buddy study_days phrasebook placement_through exam_plan golden quests leech_rests coins`. `plots` holds only plots that were reviewed. `load_state` validates every field with the `_validated_*` helpers; per-device settings use `pref_get()/pref_set()` (localStorage), not the save.
- **Redraw.** `render()` (`champ_renderer.py`) redraws the page, calling `render_farm`, `render_status`, `render_dashboard`, `render_review`, `render_<panel>` ...; every handler ends with `render()`. JS that decorates the page must reapply after a redraw (`page-hooks.js`, `toast-hook.js` show the hook pattern), never once.
- **Practice rule.** Every practice or minigame action must feed `record_practice(mode, correct)`: a new mode is one line in `PRACTICE_MODES` (`champ_rules.py`) and the header score and dashboard pick it up. A mode whose results vanish when it closes is not allowed.
- **A new panel/button.** (1) markup in `index.html` (hidden by default with the `hidden` attribute, a visible `*-toggle-button` that opens it, a way to close it; `pc.html` is generated from it); (2) add every id a `champ_*.py` module looks up to `ELEMENT_IDS` in `tests/conftest.py` (the fake DOM raises `KeyError` for an unknown id); (3) the listener in `setup()` and a `render_<name>()` called from `render()`; (4) `pc-config.json`: a window is `[panel-id, button-id, "Title"]` in `windows` and the button goes in `toolbar.menu`, otherwise in `zones` or a `composites` entry; (5) the human then runs `scripts/generate-pc-pages.py` (never edit `pc.html`); `shared/tests/test_pc_games.py` checks the config. A new Python module goes into `_PART_NAMES` (`game.py`) and the module list in `boot.js` in the same position, after everything it imports (`tests/test_module_list.py`); not `sw.js`.
- **Tests that pin things.** `test_module_list.py`, `test_file_sizes.py` (14,000-token cap, `index.html` 78 KB), `test_polish.py` (nothing in the farm runs on a timer or an animation, no streak language), `test_farm_ui.py` (no failure or streak framing), `test_save_widget.py` (save contract), `test_watering_rule.py`, `test_practice_progress.py` (every mode feeds the ledger and never touches SRS), `test_srs.py`, `test_question_generator.py`, `test_grading_v2.py`, `test_changelog.py`, `test_achievements.py`, `test_visual_style_switcher.py`. The fake DOM is `tests/conftest.py` (`game_env` fixture: `.module`, `.elements`).
- **Browser tests.** Copy `tests/test_example_browser.py` (`from browser_helpers import open_game`; `base` is a fixture from `conftest.py`): it boots the page, clicks `#water-next-button`, asserts `#practice-panel` is visible and `page.errors == []`. `open_game` pre-answers the first-visit style picker, which otherwise covers the page.
- **Do not.** Invent a view key, id or action. Use `from champ_runstate import x` (use `runstate.x`; a rebound variable also goes in `LIVE_NAMES`). Put `setInterval`, `setTimeout`, `requestAnimationFrame`, `datetime` or `time.time` in the farm's Python (`game.py` and the `champ_*.py` modules except `champ_minigames_*`), `@keyframes`, `animation:` or `transition:` in the farm stylesheets, or the word "streak" in the page (the minigames own all timers), copy the workbook's own exercises (questions are generated from the catalog), or punish a wrong answer (a stage never goes down). Add a `get_state()` key unless its value is not the default. Edit `pc.html`, `sw.js` or `offline-manifest.json`.

## Long history

The long history (per-item build notes, audit logs, site-wide-goal write-ups) was moved out of this file on 2026-10-18 into `NOTES.md` in this folder. Do not read it whole: grep its `## ` headings and read only the section you are told to.
