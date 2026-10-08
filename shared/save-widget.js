/*
 * Shared save widget (planning/SAVE-BUTTON-INTEGRATION.md). One script, included unchanged by
 * every game:
 *   <script src="../../shared/save-widget.js" data-game-id="<slug>"></script>
 * (after shared/hub-auth.js, which supplies HUB_AUTH_TOKEN_KEY and hubAuthHeaders()).
 *
 * Per-game contract: the game's Python exposes get_state() -> plain JSON-safe dict and
 * load_state(data) (its inverse) in Pyodide's globals, and the page's boot script sets
 * window.pyodide right after loadPyodide(). Nothing else changes per game.
 *
 * Anonymous play always works, with one save code per game kept in localStorage. When a bearer
 * token is present (the hub's sign-in), a "Claim this save to your account" option appears
 * (also on page load and after Load, wherever a stored code is shown), saves go to three
 * account slots, and on page load the account's most recent save for this game is loaded
 * automatically, unless the opening screen's "New Game" was chosen. There is no auto-save by
 * default, no conflict resolution: one explicit button, last write wins (the opt-in autosave
 * checkbox is the one exception, see SAVE-BUTTON-INTEGRATION.md section 7).
 *
 * Every localStorage access goes through lsGet/lsSet/lsRemove: blocked storage means "nothing
 * remembered", never a half-built widget.
 *
 * Dev-server note: this repo's dev server sends no cache-control header, so Chrome can serve a
 * stale copy of this file even after a hard reload. If an edit seems to have no effect, fetch the
 * file with {cache: "no-store"} and compare before assuming the code is wrong.
 */
(function () {
  const SCRIPT = document.currentScript;
  const GAME_ID = SCRIPT && SCRIPT.dataset.gameId;
  if (!GAME_ID) {
    console.error("save-widget.js: missing required data-game-id attribute on its <script> tag");
    return;
  }
  // A second copy (a page that includes it twice) would mount a second panel and double every handler.
  if (window.NoyvjSaveWidget) return;

  const API_BASE = "https://noyvjgames.fastapicloud.dev";
  const STORAGE_KEY = `savecode:${GAME_ID}`;

  // Storage can throw (blocked site data, some private modes). Every read and write goes through
  // these so a blocked store means "nothing remembered", never a widget that stops half-built.
  function lsGet(key) { try { return localStorage.getItem(key); } catch (err) { return null; } }
  function lsSet(key, value) { try { localStorage.setItem(key, value); } catch (err) { /* not remembered this load */ } }
  function lsRemove(key) { try { localStorage.removeItem(key); } catch (err) { /* nothing to forget */ } }
  // The hub's bearer token (HUB_AUTH_TOKEN_KEY comes from shared/hub-auth.js).
  function hubToken() { return lsGet(HUB_AUTH_TOKEN_KEY); }
  // HUB_AUTH_TOKEN_KEY/hubAuthHeaders() come from shared/hub-auth.js,
  // loaded before this file — the same bearer-token helpers script.js uses
  // for the hub's own sign-in UI, so the two can't drift out of sync on
  // the localStorage key or header shape.

  const RETRY_DELAYS_MS = [700, 1500];

  function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  // The backend sends timestamps as ISO strings. Postgres (timestamptz) includes a
  // UTC offset, but a database that stores naive timestamps (the sqlite used locally
  // and in tests) sends "2026-10-06T18:05:17" with none, which Date() reads as LOCAL
  // time -- the wrong hour for everyone outside UTC, so "just now" read "11 h ago"
  // and "latest save" sorting could pick the wrong slot. A string with no zone is UTC.
  function parseTime(iso) {
    if (!iso) return 0;
    const text = String(iso);
    const hasZone = /(Z|[+-]\d{2}:?\d{2})$/i.test(text);
    const ms = new Date(hasZone ? text : `${text}Z`).getTime();
    return Number.isNaN(ms) ? 0 : ms;
  }

  // Neon (serverless Postgres) sleeps when idle, and the first request after that used to fail
  // with a bare 500 instead of just being slow, which a player "fixes" by clicking Save four
  // times. Retry transient failures (network error, 5xx) for them; never a 4xx (wrong code, bad
  // body), because retrying cannot change that answer.
  async function fetchWithRetry(url, options, onRetrying) {
    let lastErr;
    for (let attempt = 0; attempt <= RETRY_DELAYS_MS.length; attempt++) {
      try {
        const res = await fetch(url, options);
        if (res.ok || (res.status >= 400 && res.status < 500)) return res;
        lastErr = new Error(`status ${res.status}`);
      } catch (err) {
        lastErr = err;
      }
      if (attempt < RETRY_DELAYS_MS.length) {
        if (onRetrying) onRetrying(attempt + 1);
        await sleep(RETRY_DELAYS_MS[attempt]);
      }
    }
    throw lastErr;
  }

  if (!document.getElementById("save-widget-styles")) {
    const style = document.createElement("style");
    style.id = "save-widget-styles";
    style.textContent = `
      /* UX-2/UX-6: these rules used to be class-only (.save-widget-slot button), so the
         widget's own "#save-widget button { width: 100%; margin-top }" rule (an id
         selector, higher specificity) won: every slot button became full-width, the label
         was squeezed to nothing and "Save here" was pushed off the right edge of the panel.
         Prefixing with #save-widget gives these the specificity they need. Each slot is a
         small grid: the label on its own line, then the Load / Save here buttons. */
      #save-widget .save-widget-slots { display: grid; gap: 0.4rem; margin: 0.4rem 0; }
      #save-widget .save-widget-slot { display: grid; grid-template-columns: 1fr 1fr; gap: 0.25rem; align-items: stretch;
        font-size: 0.72rem; padding: 0.3rem; border: 1px solid #2a3a4c; border-radius: 8px; }
      #save-widget .save-widget-slot-label { grid-column: 1 / -1; min-width: 0; overflow-wrap: anywhere; line-height: 1.25; }
      #save-widget .save-widget-slot button { width: auto; min-width: 0; margin: 0; font-size: 0.72rem; padding: 0.3rem 0.35rem; cursor: pointer; }
      #save-widget .save-widget-slot button:only-of-type { grid-column: 1 / -1; }
      html[data-theme="light"] #save-widget .save-widget-slot { border-color: rgba(70, 95, 170, 0.3); }
      html[data-theme="light"] #save-widget .save-widget-slot button,
      html[data-theme="light"] #save-widget .noyvj-menu-button {
        background: linear-gradient(135deg, #dbe4fb, #c6d3f5); color: #1b2033; border: 1px solid rgba(70, 95, 170, 0.3); }
      /* Header row: the Save / Load toggle, plus (UX-8) the opening screen's "Main menu"
         button, which shared/opening-screen.js drops into this row after the opening
         screen is dismissed so the way back to the game's main page is always in the
         same corner, next to the save controls, in every game. */
      #save-widget .save-widget-header { display: flex; align-items: center; gap: 0.4rem; }
      #save-widget .save-widget-header .save-widget-toggle { flex: 1 1 auto; width: auto; white-space: nowrap; }
      #save-widget .save-widget-header .noyvj-menu-button { flex: 0 0 auto; width: auto; margin: 0; padding: 0.25rem 0.5rem;
        font-size: 0.72rem; white-space: nowrap; }
      .save-widget-chooser { position: fixed; inset: 0; z-index: 10001; display: flex; align-items: center; justify-content: center;
        background: rgba(6, 7, 12, 0.72); padding: 1rem; box-sizing: border-box; overflow-y: auto; }
      .save-widget-chooser-card { width: min(22rem, 100%); max-height: 100%; overflow-y: auto; box-sizing: border-box; margin: auto;
        background: #171a29; color: #eaeaf0; border: 1px solid rgba(140,160,255,0.3);
        border-radius: 14px; padding: 1rem; display: grid; gap: 0.5rem; }
      .save-widget-chooser-card p { margin: 0; }
      .save-widget-chooser-card button { padding: 0.55rem; font: inherit; cursor: pointer; overflow-wrap: anywhere;
        background: #2a3a4c; color: #fff; border: 1px solid rgba(140,160,255,0.3); border-radius: 8px; }
      html[data-theme="light"] .save-widget-chooser-card button { background: #dbe4fb; color: #1b2033; border-color: rgba(70, 95, 170, 0.35); }
      html[data-theme="light"] .save-widget-chooser-card { background: #ffffff; color: #1b2033; }
      #save-widget {
        position: fixed;
        bottom: 12px;
        right: 12px;
        z-index: 9999;
        background: rgba(18, 20, 31, 0.94);
        border: 1px solid #2a3a4c;
        border-radius: 10px;
        padding: 10px 12px;
        font-family: system-ui, -apple-system, sans-serif;
        font-size: 0.78rem;
        color: #eaeaf0;
        width: 200px;
        box-sizing: border-box;
        /* UX-6: with three slot rows the open panel is taller than a short or phone-sized
           viewport. Cap it to the viewport and scroll inside the panel instead of letting
           the top (toggle, Save Progress) or bottom (Load) run off-screen. */
        max-width: calc(100vw - 24px);
        max-height: calc(100vh - 24px);
        max-height: calc(100dvh - 24px);
        overflow-y: auto;
        overscroll-behavior: contain;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
      }
      #save-widget .save-widget-toggle {
        background: none;
        border: none;
        color: #eaeaf0;
        font-weight: 600;
        font-size: 0.8rem;
        cursor: pointer;
        padding: 4px 0;
        min-height: 28px;
        width: 100%;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.4rem;
        text-align: left;
      }
      /* The arrow is the actual "this collapses/expands" affordance --
         the label alone ("Save / Load") reads the same whether the panel
         is open or shut, which is exactly what made the old toggle unclear. */
      #save-widget .save-widget-toggle-arrow {
        display: inline-block;
        transition: none;
        font-size: 0.7rem;
        opacity: 0.85;
      }
      #save-widget.collapsed .save-widget-toggle-arrow { transform: rotate(-90deg); }
      #save-widget.collapsed .save-widget-body { display: none; }
      #save-widget.collapsed { width: auto; padding: 4px 10px; }
      #save-widget button {
        width: 100%;
        font-size: 0.78rem;
        padding: 0.5rem;
        margin-top: 0.4rem;
        border: none;
        border-radius: 6px;
        background: #2a3a4c;
        color: white;
        cursor: pointer;
        font-family: inherit;
      }
      #save-widget button:disabled { opacity: 0.5; cursor: not-allowed; }
      #save-widget input {
        width: 100%;
        box-sizing: border-box;
        padding: 0.4rem;
        margin-top: 0.4rem;
        border: 1px solid #2a3a4c;
        border-radius: 6px;
        background: #0b0d17;
        color: #eaeaf0;
        font-size: 0.75rem;
        text-align: center;
        text-transform: uppercase;
        font-family: inherit;
      }
      #save-widget input::placeholder { color: #5a6070; text-transform: none; }
      #save-widget .save-widget-code {
        font-weight: 600;
        color: #6fa0d8;
        word-break: break-all;
        margin: 0.4rem 0 0;
      }
      #save-widget .save-widget-status {
        opacity: 0.75;
        margin: 0.4rem 0 0;
        min-height: 1em;
      }
      #save-widget .save-widget-autosave-label {
        display: flex;
        align-items: center;
        gap: 0.4rem;
        margin-top: 0.5rem;
        font-size: 0.72rem;
        opacity: 0.85;
        cursor: pointer;
      }
      #save-widget .save-widget-autosave-label input {
        width: auto;
        margin: 0;
        flex: none;
      }
      #save-widget .save-widget-link {
        background: none;
        border: none;
        color: #6fa0d8;
        text-decoration: underline;
        cursor: pointer;
        padding: 0;
        font-size: 0.72rem;
        margin-top: 0.4rem;
        display: block;
        width: 100%;
        text-align: left;
      }
      /* The [hidden] attribute must win over the display:block rules
         above it — author CSS otherwise beats the UA stylesheet's
         default [hidden] { display: none }, which silently defeats
         every .hidden = true toggle in this widget's own JS. */
      #save-widget [hidden] {
        display: none !important;
      }
    `;
    document.head.appendChild(style);
  }

  const root = document.createElement("div");
  root.id = "save-widget";
  // data-testid values follow the convention in planning/game-template.md (Z-30):
  // <component>-<part>, lowercase kebab-case, with a number appended for repeated parts.
  root.setAttribute("data-testid", "save-widget");
  root.innerHTML = `
    <div class="save-widget-header">
      <button type="button" class="save-widget-toggle" data-testid="save-widget-toggle"><span class="save-widget-toggle-label">&#128190; Save / Load</span><span class="save-widget-toggle-arrow" aria-hidden="true">&#9662;</span></button>
    </div>
    <div class="save-widget-body" data-testid="save-widget-body">
      <button type="button" class="save-widget-save-button" data-testid="save-widget-save">Save Progress</button>
      <label class="save-widget-autosave-label"><input type="checkbox" class="save-widget-autosave-checkbox" data-testid="save-widget-autosave"> Autosave every 5 minutes</label>
      <p class="save-widget-code" data-testid="save-widget-code" hidden></p>
      <button type="button" class="save-widget-copy-button save-widget-link" data-testid="save-widget-copy" hidden>Copy code</button>
      <button type="button" class="save-widget-claim-button save-widget-link" data-testid="save-widget-claim" hidden>Claim this save to your account</button>
      <button type="button" class="save-widget-new-button save-widget-link" data-testid="save-widget-new" hidden>Start a new save (forget this code)</button>
      <div class="save-widget-slots" data-testid="save-widget-slots" hidden></div>
      <input type="text" class="save-widget-load-input" data-testid="save-widget-load-input" placeholder="XXXX-XXXX" maxlength="9" autocomplete="off">
      <button type="button" class="save-widget-load-button" data-testid="save-widget-load">Load</button>
      <p class="save-widget-status" data-testid="save-widget-status"></p>
    </div>
  `;

  function mount() {
    document.body.appendChild(root);
  }
  if (document.body) mount();
  else document.addEventListener("DOMContentLoaded", mount);

  const saveButton = root.querySelector(".save-widget-save-button");
  const autosaveCheckbox = root.querySelector(".save-widget-autosave-checkbox");
  const codeDisplay = root.querySelector(".save-widget-code");
  const copyButton = root.querySelector(".save-widget-copy-button");
  const claimButton = root.querySelector(".save-widget-claim-button");
  const newButton = root.querySelector(".save-widget-new-button");
  const loadInput = root.querySelector(".save-widget-load-input");
  const loadButton = root.querySelector(".save-widget-load-button");
  const statusEl = root.querySelector(".save-widget-status");
  const toggleButton = root.querySelector(".save-widget-toggle");

  // Starts expanded (unchanged default), but now with an explicit
  // aria-expanded + title so the toggle's own accessible name says what
  // clicking it will do, not just a static "Save / Load" label that read
  // the same whether the panel was already open or shut.
  function syncToggleState() {
    const collapsed = root.classList.contains("collapsed");
    toggleButton.setAttribute("aria-expanded", String(!collapsed));
    toggleButton.title = collapsed ? "Show save/load options" : "Hide save/load options";
  }
  toggleButton.addEventListener("click", () => {
    root.classList.toggle("collapsed");
    syncToggleState();
  });
  // Playtest audit 2026-10-06 (S1): expanded by default, the widget covers
  // the bottom-right ~200x230px of a phone screen, hiding primary game
  // buttons. Below 600px wide it now starts collapsed unless the player has
  // already chosen otherwise; the choice is remembered per browser.
  const COLLAPSE_PREF_KEY = "save-widget-collapsed";
  try {
    const pref = lsGet(COLLAPSE_PREF_KEY);
    const narrow = window.matchMedia && window.matchMedia("(max-width: 600px)").matches;
    // The Desktop boot (window.NOYVJ_LAYOUT === "pc") keeps it tucked away too: the game
    // fills the window and the widget would sit on top of the side column.
    const desktopBoot = window.NOYVJ_LAYOUT === "pc";
    if (pref === "true" || (pref === null && (narrow || desktopBoot))) root.classList.add("collapsed");
  } catch (e) { /* convenience only */ }
  toggleButton.addEventListener("click", () => {
    try { lsSet(COLLAPSE_PREF_KEY, String(root.classList.contains("collapsed"))); }
    catch (e) { /* convenience only */ }
  });
  syncToggleState();

  // `owned` = the code came from this account's own slots, so there is nothing to claim.
  function showActiveCode(code, owned) {
    codeDisplay.textContent = `Code: ${code}`;
    codeDisplay.hidden = false;
    copyButton.hidden = false;
    newButton.hidden = false;
    claimButton.hidden = Boolean(owned) || !hubToken();
    // Pre-fill the load field with the remembered code too, not just the
    // separate "Code: X" display -- lets a player re-load (e.g. after
    // accidentally clicking around) without having to retype or re-copy
    // their own code. Only when the field is empty so this never clobbers
    // a code the player is actively typing in (e.g. someone else's code,
    // on a different device).
    if (!loadInput.value) loadInput.value = code;
  }

  // Pyodide loads asynchronously and each game's own boot script sets
  // window.pyodide only once loadPyodide() resolves — this widget mounts
  // immediately, well before that's guaranteed to have happened, so an
  // autoload attempt has to be able to wait for load_state() to actually
  // exist rather than assuming it's there yet.
  function waitForLoadState(timeoutMs = 15000, intervalMs = 150) {
    return new Promise((resolve, reject) => {
      const start = Date.now();
      (function check() {
        const loadState = window.pyodide && window.pyodide.globals.get("load_state");
        if (loadState) return resolve(loadState);
        if (Date.now() - start > timeoutMs) return reject(new Error("timed out waiting for Pyodide"));
        setTimeout(check, intervalMs);
      })();
    });
  }

  // Resolves once the opening screen (if any) has been answered. opening-screen.js loads AFTER this
  // file, so window.NoyvjOpeningScreen does not exist yet when this runs; waiting for the document
  // to finish parsing guarantees every script ran. (Checking synchronously let the account's latest
  // save load over a "New Game".)
  async function waitForOpeningChoice() {
    if (document.readyState === "loading") {
      await new Promise((resolve) => document.addEventListener("DOMContentLoaded", resolve, { once: true }));
    }
    if (window.NoyvjOpeningScreen && window.NoyvjOpeningScreen.choice) {
      return window.NoyvjOpeningScreen.choice;
    }
    return "continue";
  }

  // The last /users/me/saves answer, kept for a few seconds for the page-load sequence only
  // (autoload, then slot rows): both need the same list, so one request serves both.
  let recentSaves = null;

  // Fetches this account's saves for this game, newest first. Returns null on any
  // failure (not signed in, network, bad response) and [] when there are none.
  async function fetchAccountSaves() {
    if (!hubToken()) return null;
    try {
      const res = await fetchWithRetry(`${API_BASE}/users/me/saves`, { headers: hubAuthHeaders(), cache: "no-store" });
      if (!res.ok) return null;
      const saves = await res.json();
      recentSaves = { at: Date.now(), raw: saves };   // lets the startup refreshSlots() skip a second identical request
      return saves
        .filter((s) => s.game_id === GAME_ID)
        .sort((a, b) => parseTime(b.updated_at || b.created_at) - parseTime(a.updated_at || a.created_at));
    } catch (err) {
      // Logged (not just returned null) so a user-reported "my save isn't
      // loading" is debuggable from the browser console -- otherwise there's
      // no way to tell a network failure from a bad response from a JSON
      // parse error apart.
      console.error(`${GAME_ID} save-widget: fetching /users/me/saves failed`, err);
      return null;
    }
  }

  // Loads the account's most recently updated save for this game into the game.
  // Returns true if one was found and loaded.
  async function loadLatestFromAccount(message) {
    const forThisGame = await fetchAccountSaves();
    if (!forThisGame || !forThisGame.length) return false;
    const mostRecent = forThisGame[0];
    let loadState;
    try {
      loadState = await waitForLoadState();
    } catch (err) {
      console.error(`${GAME_ID} save-widget: autoload gave up waiting for load_state()`, err);
      return false;
    }
    try {
      loadState(window.pyodide.toPy(mostRecent.save_data));
    } catch (err) {
      console.error(`${GAME_ID} save-widget: autoload's load_state() call threw`, err);
      return false;
    }
    lsSet(STORAGE_KEY, mostRecent.save_code);
    showActiveCode(mostRecent.save_code, true);
    // U3: the loaded save's slot becomes the active, already-confirmed one.
    if (mostRecent.slot) setActiveSlot(mostRecent.slot, true);
    // This came from GET /users/me/saves -- the account's own saves list --
    // so it's already claimed to this account. Offering to claim it again
    // would be redundant (and confusing) even though it's a harmless no-op.
    claimButton.hidden = true;
    statusEl.textContent = message || "Continued your most recent save.";
    return true;
  }

  // Returns true if an account save for this game was found and loaded.
  async function tryAutoLoadFromAccount() {
    if (!hubToken()) return false;
    // U4: with an opening screen present, wait for the player's choice. A
    // "New Game" must never be overwritten by the account's latest save.
    const chosen = await waitForOpeningChoice();
    if (chosen === "new") {
      // The remembered slot belongs to the game that was just abandoned; forget it
      // so the first save of the new game asks where to go instead of silently
      // overwriting that slot, and no slot row is marked as the current one.
      clearActiveSlot();
      return false;
    }
    return loadLatestFromAccount();
  }

  (async () => {
    const loaded = await tryAutoLoadFromAccount();
    if (slotMode()) refreshSlots(true);
    if (loaded) return;
    const existingCode = lsGet(STORAGE_KEY);
    if (existingCode) showActiveCode(existingCode);
  })();

  // "Start a new save" forgets the remembered code, so it asks first through the shared
  // ConfirmDialog (one fix for every game); a page without confirm-dialog.js acts at once.
  function forgetSavedCode() {
    lsRemove(STORAGE_KEY);
    codeDisplay.hidden = true;
    copyButton.hidden = true;
    newButton.hidden = true;
    claimButton.hidden = true;
    loadInput.value = "";
    statusEl.textContent = "Next save starts a fresh code.";
  }

  newButton.addEventListener("click", () => {
    if (window.ConfirmDialog) {
      window.ConfirmDialog.ask({
        id: `${GAME_ID}-save-widget-forget-code`,
        message:
          "Start a new save? This forgets your current save code in this browser -- " +
          "your progress under that code isn't deleted from the server and can still " +
          "be loaded later by pasting the code back in, but you'll need to have saved " +
          "it somewhere first. This browser won't remember it anymore.",
        confirmLabel: "Start a new save",
        onConfirm: forgetSavedCode,
      });
    } else {
      forgetSavedCode();
    }
  });

  function legacyCopy(text) {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand("copy");
    document.body.removeChild(ta);
    if (!ok) throw new Error("execCommand('copy') returned false");
  }

  copyButton.addEventListener("click", async () => {
    const code = lsGet(STORAGE_KEY);
    if (!code) return;
    // Try the modern Clipboard API first, but don't just take "it exists"
    // as proof it'll work -- some browsers expose navigator.clipboard yet
    // still throw (no permission, not a secure context, document not
    // focused), so fall back to the old execCommand trick on ANY failure,
    // not only when the API is missing outright.
    try {
      await navigator.clipboard.writeText(code);
    } catch (err) {
      try {
        legacyCopy(code);
      } catch (fallbackErr) {
        console.error(`${GAME_ID} save-widget: clipboard copy failed`, err, fallbackErr);
        statusEl.textContent = "Couldn't copy — code is shown above.";
        return;
      }
    }
    statusEl.textContent = "Code copied!";
  });

  // Pyodide's PyProxy.toJs() converts a Python `None` to JS `undefined`,
  // not `null` — and JSON.stringify silently DROPS any object key whose
  // value is `undefined` (a well-known JS/JSON quirk). Left unhandled,
  // that means every nullable field a game tracks (e.g. "no event has
  // fired yet") would silently vanish from every save. This replacer
  // maps undefined -> null so JSON.stringify keeps the key instead of
  // deleting it.
  function undefinedToNull(_key, value) {
    return value === undefined ? null : value;
  }

  // Returns the game's current state as a plain JS object, `undefined` if
  // the game hasn't implemented the get_state() half of the contract (or
  // get_state() itself raised — a buggy implementation is just as unusable
  // as a missing one, and should fail the same friendly way rather than as
  // an uncaught exception with no message at all), or `null` if Pyodide
  // itself isn't ready yet.
  function readGameState() {
    if (!window.pyodide) return null;
    const getState = window.pyodide.globals.get("get_state");
    if (!getState) return undefined;
    let proxy;
    try {
      proxy = getState();
      return proxy && proxy.toJs ? proxy.toJs({ dict_converter: Object.fromEntries }) : proxy;
    } catch (err) {
      // A game's own get_state() raising is a bug in that game, not in this
      // shared widget — worth a console line pointing at GAME_ID rather than
      // just silently treating it the same as "not implemented yet".
      console.error(`${GAME_ID} save-widget: get_state() raised`, err);
      return undefined;
    } finally {
      if (proxy && typeof proxy.destroy === "function") proxy.destroy();
    }
  }

  // U3: numbered save slots for signed-in accounts (3 per game). Anonymous
  // players are untouched and keep the single save code. Signed in, "Save
  // Progress" writes to the active slot; the first save of a visit into a slot
  // that already holds something asks which slot to use (overwrite, use an
  // empty one, or cancel), so a fresh start can never silently replace an
  // older save. Autosave only writes to a slot the player has already
  // confirmed this visit.
  const SLOT_COUNT = 3;
  const ACTIVE_SLOT_KEY = `activeslot:${GAME_ID}`;
  const slotsEl = root.querySelector(".save-widget-slots");
  let slotRows = {};
  let activeSlot = parseInt(lsGet(ACTIVE_SLOT_KEY), 10) || null;
  let slotConfirmed = false;
  // True once the slot rows have been read from the server at least once. Until then
  // the widget does not know what is in the slots, so it must never guess "empty".
  let slotsKnown = false;
  // The reason the last save attempt failed, so the Save Progress button can show it
  // instead of overwriting it with a generic "Save failed". Reset at the start of each attempt.
  let saveFailureNote = "";
  function setFailure(message) {
    saveFailureNote = message;
    statusEl.textContent = message;
  }

  function slotMode() {
    return Boolean(hubToken());
  }
  function setActiveSlot(n, confirmed) {
    activeSlot = n;
    slotConfirmed = Boolean(confirmed);
    try { lsSet(ACTIVE_SLOT_KEY, String(n)); } catch (e) { /* convenience only */ }
  }
  function clearActiveSlot() {
    activeSlot = null;
    slotConfirmed = false;
    try { lsRemove(ACTIVE_SLOT_KEY); } catch (e) { /* convenience only */ }
    if (slotMode() && Object.keys(slotRows).length) renderSlots();
  }
  function timeAgo(iso) {
    if (!iso) return "";
    const seconds = Math.max(0, (Date.now() - parseTime(iso)) / 1000);
    if (seconds < 90) return "just now";
    if (seconds < 5400) return `${Math.round(seconds / 60)} min ago`;
    if (seconds < 129600) return `${Math.round(seconds / 3600)} h ago`;
    return `${Math.round(seconds / 86400)} d ago`;
  }

  // Re-reads this account's slot rows. Returns true when the rows are fresh. On a
  // failure it says why in the status line (a stale/expired sign-in looks exactly like
  // "saving is broken" otherwise) instead of silently leaving the slot list hidden.
  async function refreshSlots(allowRecent) {
    if (!slotMode()) {
      slotsEl.hidden = true;
      return false;
    }
    try {
      let raw = allowRecent && recentSaves && Date.now() - recentSaves.at < 10000 ? recentSaves.raw : null;
      recentSaves = null;
      if (!raw) {
        const res = await fetchWithRetry(`${API_BASE}/users/me/saves`, { headers: hubAuthHeaders(), cache: "no-store" });
        if (res.status === 401) {
          setFailure("Your sign-in has expired — sign in again from the hub.");
          return false;
        }
        if (!res.ok) throw new Error(`status ${res.status}`);
        raw = await res.json();
      }
      const saves = raw.filter((r) => r.game_id === GAME_ID && r.slot);
      slotRows = {};
      saves.forEach((r) => { slotRows[r.slot] = r; });
      slotsKnown = true;
    } catch (err) {
      console.error(`${GAME_ID} save-widget: refreshing save slots failed`, err);
      if (!slotsKnown) setFailure("Couldn't reach your saves just now — try again.");
      return false;
    }
    renderSlots();
    return true;
  }

  function renderSlots() {
    slotsEl.innerHTML = "";
    for (let n = 1; n <= SLOT_COUNT; n++) {
      const row = slotRows[n];
      const line = document.createElement("div");
      line.className = "save-widget-slot";
      line.setAttribute("data-testid", `save-widget-slot-${n}`);
      const label = document.createElement("span");
      label.className = "save-widget-slot-label";
      label.textContent = row
        ? `${n}${activeSlot === n ? " ●" : ""} ${row.slot_name || "Save " + n} · ${timeAgo(row.updated_at || row.created_at)}`
        : `${n}${activeSlot === n ? " ●" : ""} Empty`;
      line.appendChild(label);
      if (row) {
        const load = document.createElement("button");
        load.type = "button";
        load.setAttribute("data-testid", `save-widget-slot-${n}-load`);
        load.textContent = "Load";
        load.addEventListener("click", () => slotLoad(n));
        line.appendChild(load);
      }
      const save = document.createElement("button");
      save.type = "button";
      save.setAttribute("data-testid", `save-widget-slot-${n}-save`);
      save.textContent = "Save here";
      save.addEventListener("click", async () => {
        // An explicit tap on a slot that holds something else (not the one this game
        // was loaded from or last saved to) asks first, so a mis-tap can't replace it.
        if (slotRows[n] && !(activeSlot === n && slotConfirmed)) {
          const go = await confirmOverwrite(n);
          if (!go) return;
        }
        statusEl.textContent = "Saving...";
        saveFailureNote = "";
        const ok = await slotSave(n);
        statusEl.textContent = ok ? `Saved to slot ${n}!` : (saveFailureNote || "Save failed — try again.");
      });
      line.appendChild(save);
      slotsEl.appendChild(line);
    }
    slotsEl.hidden = false;
    // A remembered code that is one of this account's own slots is already claimed.
    const remembered = lsGet(STORAGE_KEY);
    if (remembered && Object.values(slotRows).some((r) => r.save_code === remembered)) claimButton.hidden = true;
  }

  // Resolves true when it is fine to overwrite slot n. With no shared ConfirmDialog on
  // the page it simply allows it; a cancelled dialog never resolves (nothing to do).
  function confirmOverwrite(n) {
    return new Promise((resolve) => {
      if (!window.ConfirmDialog) return resolve(true);
      const row = slotRows[n];
      window.ConfirmDialog.ask({
        id: `${GAME_ID}-save-widget-overwrite-slot`,
        message: `Overwrite slot ${n} (${(row && row.slot_name) || "Save " + n}, ${timeAgo(row && (row.updated_at || row.created_at))}) with your current progress? The old save in that slot is replaced.`,
        confirmLabel: `Overwrite slot ${n}`,
        allowSkip: false,
        onConfirm: () => resolve(true),
      });
    });
  }

  async function slotSave(n) {
    const state = readGameState();
    if (state === null) { setFailure("Still loading — try again in a moment."); return false; }
    if (state === undefined) { setFailure("This game hasn't wired up saving yet."); return false; }
    try {
      const res = await fetchWithRetry(
        `${API_BASE}/users/me/saves/${encodeURIComponent(GAME_ID)}/slots/${n}`,
        {
          method: "PUT",
          headers: Object.assign({ "Content-Type": "application/json" }, hubAuthHeaders()),
          body: JSON.stringify({ save_data: state }, undefinedToNull),
        }
      );
      if (res.status === 401) {
        setFailure("Your sign-in has expired — sign in again from the hub.");
        return false;
      }
      if (!res.ok) throw new Error(`status ${res.status}`);
      const body = await res.json();
      slotRows[n] = body;
      slotsKnown = true;
      setActiveSlot(n, true);
      try { lsSet(STORAGE_KEY, body.save_code); } catch (e) { /* convenience only */ }
      showActiveCode(body.save_code, true);
      renderSlots();
      return true;
    } catch (err) {
      console.error(`${GAME_ID} save-widget: slot save failed`, err);
      return false;
    }
  }

  async function slotLoad(n) {
    if (!slotRows[n]) return;
    // Re-read the rows first: another tab or device may have saved here since this
    // panel last looked. If the refresh fails, fall back to what is on screen.
    await refreshSlots();
    const row = slotRows[n];
    if (!row) { statusEl.textContent = `Slot ${n} is empty now.`; return; }
    if (!window.pyodide) { statusEl.textContent = "Still loading — try again in a moment."; return; }
    const loadState = window.pyodide.globals.get("load_state");
    if (!loadState) { statusEl.textContent = "This game hasn't wired up loading yet."; return; }
    try {
      loadState(window.pyodide.toPy(row.save_data));
      setActiveSlot(n, true);
      try { lsSet(STORAGE_KEY, row.save_code); } catch (e) { /* convenience only */ }
      showActiveCode(row.save_code, true);
      renderSlots();
      statusEl.textContent = `Loaded slot ${n}!`;
    } catch (err) {
      console.error(`${GAME_ID} save-widget: slot load failed`, err);
      statusEl.textContent = "Load failed — try again.";
    }
  }

  // Resolves to a slot number, or null if the player cancelled.
  function chooseSlot() {
    return new Promise((resolve) => {
      const overlay = document.createElement("div");
      overlay.className = "save-widget-chooser";
      overlay.setAttribute("data-testid", "save-widget-chooser");
      const card = document.createElement("div");
      card.className = "save-widget-chooser-card";
      card.setAttribute("role", "dialog");
      card.setAttribute("aria-modal", "true");
      const heading = document.createElement("p");
      heading.textContent = "Your account already has saves for this game. Where should this one go?";
      card.appendChild(heading);
      const done = (value) => { document.removeEventListener("keydown", onKey, true); overlay.remove(); resolve(value); };
      const onKey = (e) => { if (e.key === "Escape") { e.stopPropagation(); done(null); } };
      document.addEventListener("keydown", onKey, true);
      for (let n = 1; n <= SLOT_COUNT; n++) {
        const row = slotRows[n];
        const button = document.createElement("button");
        button.type = "button";
        button.setAttribute("data-testid", `save-widget-chooser-slot-${n}`);
        button.textContent = row ? `Overwrite slot ${n}: ${row.slot_name || "Save " + n} (${timeAgo(row.updated_at || row.created_at)})` : `Save to empty slot ${n}`;
        button.addEventListener("click", () => done(n));
        card.appendChild(button);
      }
      const cancel = document.createElement("button");
      cancel.type = "button";
      cancel.setAttribute("data-testid", "save-widget-chooser-cancel");
      cancel.textContent = "Cancel";
      cancel.addEventListener("click", () => done(null));
      card.appendChild(cancel);
      overlay.appendChild(card);
      document.body.appendChild(overlay);
      card.querySelector("button").focus();
    });
  }

  // The save-button / autosave path when signed in. Returns true/false, or
  // null when the player cancelled the chooser.
  async function doSlotSave(silent) {
    saveFailureNote = "";
    const fresh = await refreshSlots();
    // If the slot rows have never been read, "no rows" means "unknown", not "empty":
    // going ahead would save into slot 1 and could silently replace a real save there.
    if (!fresh && !slotsKnown) return false;
    let target = activeSlot;
    if (silent) {
      // Autosave never asks and never touches a slot the player hasn't confirmed this visit.
      if (!target || !slotConfirmed) return false;
      return slotSave(target);
    }
    const occupied = Object.keys(slotRows).length > 0;
    if (!target || (slotRows[target] && !slotConfirmed)) {
      if (!occupied) {
        target = 1;
      } else {
        target = await chooseSlot();
        if (target === null) return null;
      }
    }
    return slotSave(target);
  }

  // The ONE code path that talks to the save endpoint, shared by the Save button and the opt-in
  // autosave timer so they cannot drift apart. Returns true/false and leaves all user-facing
  // feedback to the caller (a disabled "Saving..." button vs. a silent timer tick).
  async function doSave(onRetrying, silent) {
    saveFailureNote = "";
    if (slotMode()) return doSlotSave(Boolean(silent));
    const state = readGameState();
    if (state === null) {
      setFailure("Still loading — try again in a moment.");
      return false;
    }
    if (state === undefined) {
      setFailure("This game hasn't wired up saving yet.");
      return false;
    }
    try {
      const code = lsGet(STORAGE_KEY);
      const res = await fetchWithRetry(
        code ? `${API_BASE}/saves/${code}` : `${API_BASE}/saves`,
        {
          method: code ? "PUT" : "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(
            code ? { save_data: state } : { game_id: GAME_ID, save_data: state },
            undefinedToNull
          ),
        },
        onRetrying
      );
      if (!res.ok) throw new Error(`status ${res.status}`);
      const body = await res.json();
      lsSet(STORAGE_KEY, body.save_code);
      showActiveCode(body.save_code);
      return true;
    } catch (err) {
      console.error(`${GAME_ID} save-widget: save failed`, err);
      return false;
    }
  }

  saveButton.addEventListener("click", async () => {
    saveButton.disabled = true;
    saveButton.textContent = "Saving...";
    const ok = await doSave(() => (statusEl.textContent = "Saving... (retrying)"));
    statusEl.textContent = ok === null ? "" : ok ? `Saved at ${new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}` : (saveFailureNote || "Save failed — try again.");
    saveButton.disabled = false;
    saveButton.textContent = "Save Progress";
  });

  // Opt-in autosave every 5 minutes, default OFF (the one exception to "no auto-save", see
  // SAVE-BUTTON-INTEGRATION.md section 7). It calls the same doSave() as the button; last write
  // wins, so the two cannot meaningfully race.
  const AUTOSAVE_KEY = `autosave-enabled:${GAME_ID}`;
  const AUTOSAVE_INTERVAL_MS = 5 * 60 * 1000;
  let autosaveTimer = null;

  function isAutosaveEnabled() {
    try {
      return lsGet(AUTOSAVE_KEY) === "true";
    } catch (err) {
      return false;
    }
  }

  function setAutosaveEnabled(enabled) {
    try {
      lsSet(AUTOSAVE_KEY, enabled ? "true" : "false");
    } catch (err) {
      console.error(`${GAME_ID} save-widget: failed to persist autosave preference`, err);
    }
  }

  function stopAutosaveTimer() {
    if (autosaveTimer !== null) {
      clearInterval(autosaveTimer);
      autosaveTimer = null;
    }
  }

  function startAutosaveTimer() {
    stopAutosaveTimer(); // guards against ever running two overlapping intervals
    autosaveTimer = setInterval(performAutosave, AUTOSAVE_INTERVAL_MS);
  }

  async function performAutosave() {
    // Runs unattended -- a failed/not-ready autosave (still loading, game
    // hasn't wired up get_state() yet, network error) stays silent besides
    // doSave()'s own console.error; the manual Save button is unaffected
    // and remains the reliable fallback. Only a SUCCESSFUL autosave gets
    // any player-visible feedback, briefly, then reverts.
    const previousStatus = statusEl.textContent;
    const ok = await doSave(undefined, true);
    if (!ok) return;
    statusEl.textContent = "Autosaved";
    setTimeout(() => {
      if (statusEl.textContent === "Autosaved") statusEl.textContent = previousStatus;
    }, 4000);
  }

  autosaveCheckbox.addEventListener("change", () => {
    setAutosaveEnabled(autosaveCheckbox.checked);
    if (autosaveCheckbox.checked) startAutosaveTimer();
    else stopAutosaveTimer();
  });

  // Restore on load: a missing key reads as OFF; a player who turned it on gets the timer back
  // from page load without re-ticking the box.
  autosaveCheckbox.checked = isAutosaveEnabled();
  if (autosaveCheckbox.checked) startAutosaveTimer();

  loadButton.addEventListener("click", async () => {
    if (!window.pyodide) {
      statusEl.textContent = "Still loading — try again in a moment.";
      return;
    }
    const loadState = window.pyodide.globals.get("load_state");
    if (!loadState) {
      statusEl.textContent = "This game hasn't wired up loading yet.";
      return;
    }
    const code = loadInput.value.trim().toUpperCase();
    if (!code) {
      statusEl.textContent = "Enter a save code first.";
      return;
    }
    loadButton.disabled = true;
    loadButton.textContent = "Loading...";
    try {
      const res = await fetchWithRetry(`${API_BASE}/saves/${code}`, undefined, () => (
        statusEl.textContent = "Loading... (retrying)"
      ));
      if (!res.ok) throw new Error(`status ${res.status}`);
      const body = await res.json();
      loadState(window.pyodide.toPy(body.save_data));
      lsSet(STORAGE_KEY, body.save_code);
      showActiveCode(body.save_code);
      loadInput.value = "";
      statusEl.textContent = "Loaded!";
    } catch (err) {
      console.error(`${GAME_ID} save-widget: load failed for code ${code}`, err);
      statusEl.textContent = navigator.onLine === false
        ? "Load failed — you appear to be offline."
        : "Load failed — check the code (format XXXX-XXXX) and try again.";
    } finally {
      loadButton.disabled = false;
      loadButton.textContent = "Load";
    }
  });

  claimButton.addEventListener("click", async () => {
    const code = lsGet(STORAGE_KEY);
    if (!code) return;
    claimButton.disabled = true;
    claimButton.textContent = "Claiming...";
    try {
      const res = await fetchWithRetry(
        `${API_BASE}/saves/${code}/claim`,
        { method: "POST", headers: hubAuthHeaders() },
        () => (statusEl.textContent = "Claiming... (retrying)")
      );
      if (res.status === 409) {
        // Either every slot for this game is taken, or the code is another account's.
        let detail = "";
        try { detail = (await res.json()).detail || ""; } catch (e) { /* no body */ }
        statusEl.textContent = /slots/i.test(detail)
          ? "All 3 save slots are full — use \"Save here\" on a slot to replace one instead."
          : "That save already belongs to another account.";
        claimButton.disabled = false;
        claimButton.textContent = "Claim this save to your account";
        return;
      }
      if (!res.ok) throw new Error(`status ${res.status}`);
      let claimed = null;
      try { claimed = await res.json(); } catch (e) { /* the claim itself worked */ }
      claimButton.hidden = true;
      claimButton.disabled = false;
      claimButton.textContent = "Claim this save to your account";
      if (claimed && claimed.slot) {
        // The claimed save took a slot; that is now the one being played.
        setActiveSlot(claimed.slot, true);
        await refreshSlots();
        statusEl.textContent = `Save claimed to your account (slot ${claimed.slot})!`;
      } else {
        statusEl.textContent = "Save claimed to your account!";
      }
    } catch (err) {
      console.error(`${GAME_ID} save-widget: claim failed for code ${code}`, err);
      statusEl.textContent = "Claim failed — try again.";
      claimButton.disabled = false;
      claimButton.textContent = "Claim this save to your account";
    }
  });

  // Small public API for the opening screen's "Main menu" re-entry (UX-8).
  window.NoyvjSaveWidget = {
    // Loads the account's latest save (signed in) or the remembered save code
    // (anonymous). Resolves true if something was loaded.
    async loadLatest() {
      if (slotMode()) {
        const ok = await loadLatestFromAccount("Loaded your latest save.");
        if (ok) await refreshSlots();
        return ok;
      }
      const code = lsGet(STORAGE_KEY);
      if (!code || !window.pyodide) return false;
      loadInput.value = code;
      loadButton.click();
      return true;
    },
  };
})();
