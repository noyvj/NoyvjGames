# Game Template — copy this for every new demo idea

Use this after a 2–3 round question-based groundwork session (like the SOL one) for a new game idea. Fill in each section, then save as `games/<game-slug>/CLAUDE.md`.

---

# [GAME NAME]

## One-line pitch
[What is this game, in a sentence.]

## Concept
[A short paragraph — the actual idea, what makes it interesting, what it's inspired by if anything.]

## Stack
- Default: Python via Pyodide (matches SOL's approach — real Python logic, `js` module for DOM interaction, no build step). State explicitly if this game is better suited to plain HTML/CSS/vanilla JS instead (e.g. if Pyodide's load time is overkill for something trivially small) — flag it as a deliberate exception, not a default drift.
- Must run via local HTTP server (`python -m http.server`), same as SOL.

## Core constraints (do not violate without asking)
[Any hard rules specific to this game — e.g. "no timers," aesthetic choices, platform assumptions, anything the idea depends on.]

## Milestones
Numbered, one clearly separable/demonstrable stage at a time — same approach as SOL. Not mapped to specific calendar weeks; build and tag whenever done.

| # | Milestone | Content | Status |
|---|-----------|---------|--------|
| 1 | | | |
| 2 | | | |

## Working conventions
- Commit + tag at the end of each milestone: `git commit -m "Milestone N: <name>"` then `git tag <game-slug>-milestone-0N`.
- Update the Status column as you go so Claude Code always knows real current state, not a stale assumption.
- Once a milestone is genuinely ready to be visible, add an entry to the site's changelog/log (see root CLAUDE.md) — this is what satisfies the "something visible every 2 weeks" rule.

---

# Reference (not part of the copy above): the `data-testid` convention

Automated tests (Playwright now, anything later) find an element by `data-testid` instead of by its class or text, so a restyle or a reworded button does not break them. The shared components carry these hooks already (TODO Z-30); a game that adds its own controls should follow the same rules. The attribute changes nothing visible or audible: it is never read by game code and never styled.

**Format.** `<component>-<part>`, all lowercase, words joined by hyphens, digits allowed. Start with the name of the component or panel, then the part: `save-widget-toggle`, `confirm-dialog-confirm`, `tutorial-next`. When a part repeats, append the index or the stable id after the part name, never before it: `save-widget-slot-2`, `save-widget-slot-2-load`, `achievement-row-first_win` (ids from a data file keep their own spelling). Test ids are unique on a page; a repeated thing gets a number or id, never the same name twice.

**What to tag.** The root of a component, every button, input and link a test would press or fill, and every element whose text a test would read (a status line, a message, a counter). Do not tag purely decorative wrappers.

**For a game's own controls.** Use the game slug as the first word, then the same pattern: `grid-build-coal`, `canopy-plot-12`, `tide-advance-season`. The existing element `id`s stay as they are (the game code uses them); `data-testid` is added beside them. Static HTML: write the attribute. Built in JS: `el.setAttribute("data-testid", "...")`. Never put player text, scores or save data in the value.

**What the shared components carry today** (pinned by `shared/tests/test_testids_browser.py`):

| Component | Test ids |
|---|---|
| Save widget (`shared/save-widget.js`) | `save-widget`, `save-widget-toggle`, `save-widget-body`, `save-widget-save`, `save-widget-autosave`, `save-widget-code`, `save-widget-copy`, `save-widget-claim`, `save-widget-new`, `save-widget-slots`, `save-widget-load-input`, `save-widget-load`, `save-widget-status`; per slot (signed in) `save-widget-slot-N`, `save-widget-slot-N-load`, `save-widget-slot-N-save`; the where-to-save chooser `save-widget-chooser`, `save-widget-chooser-slot-N`, `save-widget-chooser-cancel` |
| Confirm dialog (`shared/confirm-dialog.js`) | `confirm-dialog` (the overlay), `confirm-dialog-box`, `confirm-dialog-message`, `confirm-dialog-skip` (the "don't ask again" checkbox), `confirm-dialog-cancel`, `confirm-dialog-confirm` |
| Tutorial (`shared/tutorial.js`) | `tutorial-overlay`, `tutorial-spotlight`, `tutorial-card`, `tutorial-step-counter`, `tutorial-title`, `tutorial-text`, `tutorial-card-buttons`, `tutorial-back` (not on step 1), `tutorial-next`, `tutorial-skip`; in the how-to panel `tutorial-howto-step-N` |
| Achievements (`shared/achievement-stats.js`, which decorates the game's own panel) | `achievements-panel` (the game's `#achievements-panel`), `achievement-row-<achievement id>` for each `[data-achievement-id]` row, `achievement-earn-rate`, `achievement-rarity` |

A game that renders the achievements panel itself keeps its own row markup; the hooks above are added to it by `applyAchievementStats()` after the game's render, so call that as the game already does.
