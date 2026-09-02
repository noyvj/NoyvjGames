# Save Button Integration — Shared Across All Games

Companion to `SAVE-SYSTEM-DESIGN.md` (backend/schema) and `ACCOUNTS-AND-FEEDBACK-DESIGN.md` (accounts). This doc covers the piece that goes *inside* each game: one shared save button and one shared script, dropped into every game unchanged, so saving doesn't need custom work per game.

Status: **draft — not yet built.**

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
- **On Save:** calls `window.pyodide.globals.get('get_state')()`, converts the Pyodide proxy to a plain JS object (`.toJs({dict_converter: Object.fromEntries})`), and `POST`s it to `/saves` (or `PUT`s to `/saves/{code}` if a code already exists this session). Shows the returned save code to the player and copies it to the clipboard.
- **Remembers the code locally:** stores the last save code for *this game* in `localStorage` (keyed per game, e.g. `savecode:sol`), so returning to the same browser can offer "Continue" without retyping a code.
- **On Load:** takes a code (typed in, or auto-filled from `localStorage`), `GET`s `/saves/{code}`, and calls `window.pyodide.globals.get('load_state')(data)`.
- **If a user is logged in** (bearer token present — see `ACCOUNTS-AND-FEEDBACK-DESIGN.md`): after a successful save, also offers a one-click "Claim this save to my account" button, which calls `POST /saves/{code}/claim`. Anonymous play always still works; this is additive, not required.

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
