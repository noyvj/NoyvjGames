# Save Button Integration — Shared Across All Games

Companion to `SAVE-SYSTEM-DESIGN.md` (backend/schema) and `ACCOUNTS-AND-FEEDBACK-DESIGN.md` (accounts). This doc covers the piece that goes *inside* each game: one shared save button and one shared script, dropped into every game unchanged, so saving doesn't need custom work per game.

Status: **Built and rolled out — 2026-08-20.** `shared/save-widget.js` is live in SOL (the reference integration), all 8 climate games, Le Champ de Mots, and Continuum (Phase 1, Milestone 4, built on this same contract from the start). Extended same day with signed-in autoload (§3) once real use showed that without it, a returning signed-in player who forgot to paste in their code by hand would see a blank save every time and reasonably read that as "my save keeps resetting."

---

## 1. The idea

One shared file, `shared/save-widget.js`, included by every game's HTML via a plain `<script>` tag — no build step, matches the rest of the stack. It renders the save button, talks to the FastAPI save endpoints, and handles the save-code UI. Every game includes the exact same script and gets the exact same button; nothing about the widget itself changes game to game.

The only per-game work is satisfying a tiny contract: each game exposes two functions so the widget can get and restore its state. That's it — the widget doesn't know or care what's *inside* the state, so a puzzle game and a trade-sim game plug in identically.

## 2. The per-game contract

Each game's Python code must define these two functions, exposed to JS by the existing Pyodide boot glue:

```python
def get_state():
    """Return the entire current game state as a plain, JSON-serialisable dict.
    No custom objects, no functions — just numbers, strings, lists, dicts, booleans."""
    return {
        "turn": current_turn,
        "resources": resources,
        "flags": story_flags,
        # ...whatever the game actually tracks
    }

def load_state(data):
    """Take the dict from get_state() (possibly from a previous session) and
    restore the game to that point. Should be the exact inverse of get_state()."""
    global current_turn, resources, story_flags
    current_turn = data["turn"]
    resources = data["resources"]
    story_flags = data["flags"]
```

That's the whole contract. If a game can honestly implement both functions, the shared save button works for it with zero other changes.

## 3. What the shared widget does

`shared/save-widget.js` handles, identically for every game:

- Renders a small fixed-position "Save" button (and a "Load by code" input) — same corner, same look, every game.
- **On Save:** calls `window.pyodide.globals.get('get_state')()`, converts the Pyodide proxy to a plain JS object (`.toJs({dict_converter: Object.fromEntries})`), and `POST`s it to `/saves` (or `PUT`s to `/saves/{code}` if a code already exists this session). Shows the returned save code to the player.
  <!-- REVIEW(documentation): stale -- the widget never uses the clipboard API (grep shared/save-widget.js: zero matches for navigator.clipboard); it only sets codeDisplay.textContent. -->
- **Remembers the code locally:** stores the last save code for *this game* in `localStorage` (keyed per game, e.g. `savecode:sol`), so returning to the same browser can offer "Continue" without retyping a code.
- **On Load:** takes a code typed into the load input, `GET`s `/saves/{code}`, and calls `window.pyodide.globals.get('load_state')(data)`.
  <!-- REVIEW(documentation): stale -- the load input is never auto-filled from localStorage (only read on submit, cleared on success); the remembered code is instead surfaced separately via the read-only codeDisplay element (showActiveCode()). -->
- **If a user is logged in** (bearer token present — see `ACCOUNTS-AND-FEEDBACK-DESIGN.md`): after a successful save, also offers a one-click "Claim this save to my account" button, which calls `POST /saves/{code}/claim`. Anonymous play always still works; this is additive, not required.
- **On page load, if logged in: autoload the account's most recent save for this game.** Calls `GET /users/me/saves`, filters to this game's `game_id`, and — if any are found — loads the one with the latest `updated_at` (falling back to `created_at`), before falling back to whatever anonymous code is remembered in this browser's `localStorage`. The account is the source of truth once signed in; a signed-in player should never have to remember and paste in a code by hand just to pick up where they left off. Because `window.pyodide`/`load_state()` aren't guaranteed to exist yet when the widget mounts, this waits (polling, 15s timeout) for the game's boot script to finish before attempting the load. A save reached this way is already claimed (it came from the account's own list), so the "Claim this save" link is skipped for it.

## 4. Drop-in HTML

Every game's HTML page includes, near the end of `<body>`:

```html
<script src="../shared/save-widget.js" data-game-id="sol"></script>
```

`data-game-id` is the only thing that changes per game — it's what tags the save row with the right `game_id` in the backend. Everything else about the include is identical.

## 5. What this deliberately doesn't do

- No auto-save timer or auto-save-on-every-action — one explicit button, one explicit save point per click. Simpler to build, simpler to reason about, and avoids silently overwriting a save the player wanted to keep.
- No conflict resolution if the same save code is loaded and saved from two different tabs/devices at once — last write wins. Fine for a solo-player hub; not worth solving unless it actually comes up.
- No per-game save UI customisation. If a specific game genuinely needs something the shared widget can't do, that's a deliberate exception to flag and log, not a default to design around up front.

## 6. Build order

1. Write `shared/save-widget.js` against one game first (SOL is the obvious pick — it's already the proof-of-concept).
2. Confirm `get_state()`/`load_state()` round-trip correctly for that one game.
3. Add the same two functions + the one `<script>` tag to each remaining game — this step should be fast precisely because the widget itself doesn't change.
4. Log each stage in `BCM206-DEV-LOG.md`, same as the rest of the save system.
