# BCM206 Dev Log — Infrastructure Design

This log tracks the **Infrastructure Design** Digital Artefact for BCM206: the site itself — hosting, the save system, accounts, deployment, and any platform/backend work. It is the evidence base for the Operation criterion (chains of build → test → adapt) and for Contextualisation (linking infra decisions to subject theory — Networked Society, Splinternet, AI and Future Networks, or whatever's live in Module II by the time this is written).

**This file is a running log, not a report.** Keep entries short and factual. The BCM206 contextual report gets written *from* this later — don't try to write the polished version here.

---

## Instructions for Claude Code

> Claude: at the end of any session where you touch site infrastructure — hosting/deployment config, the save system, accounts/auth, the database (Neon/FastAPI), the PWA setup, or any backend plumbing — append a new entry to the **Log** section below, in this exact format:
>
> ```
> ### YYYY-MM-DD
> **Touched:** [files/systems changed]
> **Did:** [2-4 sentences — what changed and why]
> **Result:** [what works now that didn't before, or what broke/what's still open]
> ```
>
> Append below the most recent entry — never edit or delete a past entry. If a session touches BOTH infrastructure and individual game content/mechanics, log the infra parts here and log the game-content parts in `BCM114-DEV-LOG.md` instead — split the same session across both files if needed.

---

## Log

*(entries appended below, most recent last)*

### 2026-08-15
**Touched:** `app/models.py`, `app/main.py`, `app/tests/test_save_system.py`, `games/sol/game.py`, `games/sol/tests/test_save_system.py`, `games/sol/index.html`, `games/sol/style.css`, `planning/SAVE-SYSTEM-DESIGN.md`
**Did:** Built Phase 1 of the save system from `SAVE-SYSTEM-DESIGN.md` — save codes, no accounts. Added a `Save` model (SQLAlchemy, `saves` table) and three endpoints (`POST /saves`, `GET /saves/{save_code}`, `PUT /saves/{save_code}`) to the FastAPI backend, with unambiguous-alphabet code generation (`XXXX-XXXX`, excludes `0/O/1/I/L`) and collision retry on insert. Wired SOL up as the reference integration: `serialize_state()`/`deserialize_state()`/`get_save_state_json()`/`load_save_state_json()` in `game.py`, plus a documented plain-JS bridge in `index.html` (Save/Load buttons, localStorage-remembered save code) that fetches the deployed API. Two deliberate deviations from the original spec, both for sqlite-test-suite portability: `id` is a Python `uuid.uuid4()` string instead of Postgres `gen_random_uuid()`, and `save_data` uses generic SQLAlchemy `JSON` instead of `JSONB`.
**Result:** 9 new backend tests + 8 new SOL tests, all passing (490 total across the site, 0 regressions). Caught and fixed a real bug via the test suite: `serialize_state()` was returning a live reference to `planet_state` instead of a deep copy, so post-save mutation could corrupt the "saved" snapshot — fixed with `copy.deepcopy()`. Verified live end-to-end against a temporary local backend instance (save → code → fresh page load → load by code → state restored, including mid-travel state), then reverted the API URL back to production before committing. Other games can adopt the same bridge pattern later; Phase 2 (accounts) is still just a design, not started.

### 2026-08-18
**Touched:** `script.js`, `sw.js`, `app/main.py`, `CLAUDE.md`, `README.md`, plus `index.html` and every `games/*/index.html`/`games/*/style.css` (favicon + back-link only — game-content changes logged separately in BCM114)
**Did:** Ran a full site audit (hub shell, backend, PWA config, all 10 games) looking for bugs and forgotten pieces. Found and fixed: the hub's star-rating widget was silently wrong on every card, since `/ratings/{slug}` returns both star-widget rows and per-game text-feedback-prompt rows (`stars: null`) from the same table, and `renderSummary()` was averaging over all of them instead of filtering to star rows first — confirmed live in production that Loop and Drift were each showing a misleading "0.0 ★ average (1 review)" from a single feedback-only row, now correctly showing "No reviews yet" (fix verified against the live backend, not just locally). Also fixed: no favicon anywhere on the site (added to all 11 pages); no way back to the hub from any game page (added a small link to all 10); the service worker's offline precache list was still SOL-only, predating the climate quartets (extended to all 8, cache version bumped); root `CLAUDE.md`'s games table hadn't been updated since Iteration Pass 2 / Info Page shipped; `README.md` was a one-line stub; a Pydantic `class Config` deprecation warning in the backend.
**Result:** All fixes verified live (including against the real production ratings API for the star-average bug) or via the full test suite (1424 game tests + 15 backend tests, zero regressions). One infrastructure quirk surfaced during verification, not fixed since it's outside the site itself: the Claude Browser preview pane's own tunnel proxy can serve a stale cached copy of a page indefinitely regardless of service-worker unregistration, cache-clearing, or cache-busting query strings — the only reliable workaround found was previewing a brand-new local port.
