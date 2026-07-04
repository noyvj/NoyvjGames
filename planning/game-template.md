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
