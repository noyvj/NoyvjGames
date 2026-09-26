/*
 * Shared save widget — SAVE-BUTTON-INTEGRATION.md.
 *
 * One script, included unchanged by every game via:
 *   <script src="../../shared/save-widget.js" data-game-id="<slug>"></script>
 * (two levels up from games/<slug>/index.html to the repo root, then into
 * shared/ — the design doc's own example used one "../", which assumed a
 * shallower games/ layout than this repo actually has; corrected here.)
 *
 * Per-game contract (see SAVE-BUTTON-INTEGRATION.md §2): the game's Python
 * code exposes two functions to Pyodide's globals —
 *   get_state() -> plain JSON-safe dict
 *   load_state(data) -> restores that dict, inverse of get_state()
 * — and the page's own boot script must expose `window.pyodide` (just
 * `window.pyodide = pyodide;` right after `await loadPyodide()`). Nothing
 * else about the widget changes per game.
 *
 * Anonymous play always works. If a bearer token is already present in
 * localStorage (the hub's sign-in — see ACCOUNTS-AND-FEEDBACK-DESIGN.md),
 * a "Claim this save to your account" option appears after a successful
 * REVIEW(documentation): "appears after a successful save" undersells it —
 * showActiveCode() (which surfaces the claim button) also runs on plain page
 * load if a signed-in user already has a stored code, and after a successful
 * Load, not just after a Save.
 * save. No auto-save by default, no conflict resolution — one explicit
 * button, one explicit save point, last write wins. See §5 of the design
 * doc for why — and its new §7 for the Z25b opt-in autosave-checkbox
 * exception to that "no auto-save" default (still OFF unless the player
 * turns it on).
 *
 * Signed-in autoload: on page load, if signed in, the widget fetches the
 * account's saves for this game and, if any exist, loads the most recently
 * updated one automatically — the account is the source of truth once
 * signed in, ahead of whatever anonymous code happens to be remembered in
 * this browser's localStorage for this game. Without this, a returning
 * signed-in player who forgot to paste in their code by hand would see a
 * blank farm/city/settlement every time and reasonably read that as "my
 * save keeps resetting" — it wasn't resetting, it just was never loading.
 *
 * Dev-environment note (found verifying the Z22 follow-up's ConfirmDialog
 * gating on "Start a new save"): this repo's local dev server sends no
 * cache-control header, and this exact file gets loaded by every game
 * across an entire long working session, so Chrome's heuristic HTTP cache
 * can end up serving a genuinely stale copy of THIS SPECIFIC file even
 * after a hard page reload -- confirmed by fetching it with
 * `{cache: "no-store"}` and comparing against what a plain <script> tag
 * actually executed. A brand-new tab with no service-worker registration
 * still hit this. If a save-widget.js change ever appears to have "no
 * effect" while manually verifying in this dev setup, check this before
 * assuming the code is wrong: fetch this file with cache disabled and
 * compare, or open the file's URL directly and hard-refresh with dev
 * tools' cache disabled. Not a concern in production (GitHub Pages serves
 * with different caching behavior, and real users don't reload the same
 * dev tab for hours).
 */
(function () {
  const SCRIPT = document.currentScript;
  const GAME_ID = SCRIPT && SCRIPT.dataset.gameId;
  if (!GAME_ID) {
    console.error("save-widget.js: missing required data-game-id attribute on its <script> tag");
    return;
  }

  const API_BASE = "https://noyvjgames.fastapicloud.dev";
  const STORAGE_KEY = `savecode:${GAME_ID}`;
  // HUB_AUTH_TOKEN_KEY/hubAuthHeaders() come from shared/hub-auth.js,
  // loaded before this file — the same bearer-token helpers script.js uses
  // for the hub's own sign-in UI, so the two can't drift out of sync on
  // the localStorage key or header shape.

  const RETRY_DELAYS_MS = [700, 1500];

  function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  // The backend's database (Neon, serverless Postgres) suspends its
  // compute after a few minutes idle. The first request after that wakes
  // it back up, but used to fail outright with a bare 500 rather than
  // just being slow (a stale pooled DB connection failing before the fix
  // in app/database.py's pool_pre_ping). A transient failure here is
  // exactly the kind of thing a user "fixes" by clicking Save four times
  // in a row — so retry it for them instead of making that the expected
  // workflow. Doesn't retry a 4xx (a wrong save code, a bad request body)
  // since retrying an error that isn't going to change the outcome just
  // delays telling the user the real problem.
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
      .save-widget-slots { display: grid; gap: 0.35rem; margin: 0.4rem 0; }
      .save-widget-slot { display: flex; gap: 0.3rem; align-items: center; font-size: 0.72rem; }
      .save-widget-slot-label { flex: 1 1 auto; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
      .save-widget-slot button { flex: 0 0 auto; font-size: 0.7rem; padding: 0.2rem 0.45rem; cursor: pointer; }
      .save-widget-chooser { position: fixed; inset: 0; z-index: 10001; display: flex; align-items: center; justify-content: center;
        background: rgba(6, 7, 12, 0.72); padding: 1rem; }
      .save-widget-chooser-card { width: min(22rem, 100%); background: #171a29; color: #eaeaf0; border: 1px solid rgba(140,160,255,0.3);
        border-radius: 14px; padding: 1rem; display: grid; gap: 0.5rem; }
      .save-widget-chooser-card button { padding: 0.55rem; font: inherit; cursor: pointer; }
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
        width: 190px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
      }
      #save-widget .save-widget-toggle {
        background: none;
        border: none;
        color: #eaeaf0;
        font-weight: 600;
        font-size: 0.8rem;
        cursor: pointer;
        padding: 0;
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
  root.innerHTML = `
    <button type="button" class="save-widget-toggle"><span class="save-widget-toggle-label">&#128190; Save / Load</span><span class="save-widget-toggle-arrow" aria-hidden="true">&#9662;</span></button>
    <div class="save-widget-body">
      <button type="button" class="save-widget-save-button">Save Progress</button>
      <label class="save-widget-autosave-label"><input type="checkbox" class="save-widget-autosave-checkbox"> Autosave every 5 minutes</label>
      <p class="save-widget-code" hidden></p>
      <button type="button" class="save-widget-copy-button save-widget-link" hidden>Copy code</button>
      <button type="button" class="save-widget-claim-button save-widget-link" hidden>Claim this save to your account</button>
      <button type="button" class="save-widget-new-button save-widget-link" hidden>Start a new save (forget this code)</button>
      <div class="save-widget-slots" hidden></div>
      <input type="text" class="save-widget-load-input" placeholder="XXXX-XXXX" maxlength="9" autocomplete="off">
      <button type="button" class="save-widget-load-button">Load</button>
      <p class="save-widget-status"></p>
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
  syncToggleState();

  function showActiveCode(code) {
    codeDisplay.textContent = `Code: ${code}`;
    codeDisplay.hidden = false;
    copyButton.hidden = false;
    newButton.hidden = false;
    claimButton.hidden = !localStorage.getItem(HUB_AUTH_TOKEN_KEY);
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

  // Returns true if an account save for this game was found and loaded.
  async function tryAutoLoadFromAccount() {
    const token = localStorage.getItem(HUB_AUTH_TOKEN_KEY);
    if (!token) return false;
    // U4: with an opening screen present, wait for the player's choice. A
    // "New Game" must never be overwritten by the account's latest save.
    if (window.NoyvjOpeningScreen && window.NoyvjOpeningScreen.choice) {
      const chosen = await window.NoyvjOpeningScreen.choice;
      if (chosen === "new") return false;
    }
    let saves;
    try {
      const res = await fetchWithRetry(`${API_BASE}/users/me/saves`, { headers: hubAuthHeaders() });
      if (!res.ok) return false;
      saves = await res.json();
    } catch (err) {
      // Logged (not just returned false) so a user-reported "my save isn't
      // loading" is debuggable from the browser console — otherwise there's
      // no way to tell a network failure from a bad response from a JSON
      // parse error apart, and this whole autoload runs silently on every
      // page load with no other visible sign it even attempted anything.
      console.error(`${GAME_ID} save-widget: autoload failed fetching /users/me/saves`, err);
      return false;
    }
    const forThisGame = saves.filter((s) => s.game_id === GAME_ID);
    if (!forThisGame.length) return false;
    forThisGame.sort((a, b) => {
      const aTime = new Date(a.updated_at || a.created_at).getTime();
      const bTime = new Date(b.updated_at || b.created_at).getTime();
      return bTime - aTime;
    });
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
    localStorage.setItem(STORAGE_KEY, mostRecent.save_code);
    showActiveCode(mostRecent.save_code);
    // U3: the autoloaded save's slot becomes the active, already-confirmed one.
    if (mostRecent.slot) setActiveSlot(mostRecent.slot, true);
    // This came from GET /users/me/saves -- the account's own saves list --
    // so it's already claimed to this account. Offering to claim it again
    // would be redundant (and confusing) even though it's a harmless no-op.
    claimButton.hidden = true;
    statusEl.textContent = "Continued your most recent save.";
    return true;
  }

  (async () => {
    const loaded = await tryAutoLoadFromAccount();
    if (slotMode()) refreshSlots();
    if (loaded) return;
    const existingCode = localStorage.getItem(STORAGE_KEY);
    if (existingCode) showActiveCode(existingCode);
  })();

  // Z22 follow-up (planning/TODO.md, found while auditing every game's own
  // reset-progress action): this button is the actual site-wide full-save
  // wipe -- identical across all 12 games since this file is shared
  // unchanged -- and used to fire with zero confirmation of any kind, not
  // even a native confirm(). Gated behind the shared ConfirmDialog here
  // (one fix, every game gets it at once) rather than per-game, matching
  // this file's own "one script, included unchanged by every game"
  // contract. Falls through to firing immediately if a page hasn't
  // included shared/confirm-dialog.js -- same graceful-degradation shape
  // every Python-side _confirm_dialog_ask() helper already uses -- so this
  // is strictly additive for pages that opt in and a no-op change for ones
  // that don't (yet).
  function forgetSavedCode() {
    localStorage.removeItem(STORAGE_KEY);
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
    const code = localStorage.getItem(STORAGE_KEY);
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
  let activeSlot = parseInt(localStorage.getItem(ACTIVE_SLOT_KEY), 10) || null;
  let slotConfirmed = false;

  function slotMode() {
    return Boolean(localStorage.getItem(HUB_AUTH_TOKEN_KEY));
  }
  function setActiveSlot(n, confirmed) {
    activeSlot = n;
    slotConfirmed = Boolean(confirmed);
    try { localStorage.setItem(ACTIVE_SLOT_KEY, String(n)); } catch (e) { /* convenience only */ }
  }
  function timeAgo(iso) {
    if (!iso) return "";
    const seconds = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
    if (seconds < 90) return "just now";
    if (seconds < 5400) return `${Math.round(seconds / 60)} min ago`;
    if (seconds < 129600) return `${Math.round(seconds / 3600)} h ago`;
    return `${Math.round(seconds / 86400)} d ago`;
  }

  async function refreshSlots() {
    if (!slotMode()) {
      slotsEl.hidden = true;
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/users/me/saves`, { headers: hubAuthHeaders(), cache: "no-store" });
      if (!res.ok) return;
      const saves = (await res.json()).filter((r) => r.game_id === GAME_ID && r.slot);
      slotRows = {};
      saves.forEach((r) => { slotRows[r.slot] = r; });
    } catch (err) {
      return;
    }
    renderSlots();
  }

  function renderSlots() {
    slotsEl.innerHTML = "";
    for (let n = 1; n <= SLOT_COUNT; n++) {
      const row = slotRows[n];
      const line = document.createElement("div");
      line.className = "save-widget-slot";
      const label = document.createElement("span");
      label.className = "save-widget-slot-label";
      label.textContent = row
        ? `${n}${activeSlot === n ? " ●" : ""} ${row.slot_name || "Save " + n} · ${timeAgo(row.updated_at || row.created_at)}`
        : `${n}${activeSlot === n ? " ●" : ""} Empty`;
      line.appendChild(label);
      if (row) {
        const load = document.createElement("button");
        load.type = "button";
        load.textContent = "Load";
        load.addEventListener("click", () => slotLoad(n));
        line.appendChild(load);
      }
      const save = document.createElement("button");
      save.type = "button";
      save.textContent = "Save here";
      save.addEventListener("click", async () => {
        statusEl.textContent = "Saving...";
        const ok = await slotSave(n);
        statusEl.textContent = ok ? `Saved to slot ${n}!` : "Save failed — try again.";
      });
      line.appendChild(save);
      slotsEl.appendChild(line);
    }
    slotsEl.hidden = false;
  }

  async function slotSave(n) {
    const state = readGameState();
    if (state === null) { statusEl.textContent = "Still loading — try again in a moment."; return false; }
    if (state === undefined) { statusEl.textContent = "This game hasn't wired up saving yet."; return false; }
    try {
      const res = await fetchWithRetry(
        `${API_BASE}/users/me/saves/${encodeURIComponent(GAME_ID)}/slots/${n}`,
        {
          method: "PUT",
          headers: Object.assign({ "Content-Type": "application/json" }, hubAuthHeaders()),
          body: JSON.stringify({ save_data: state }, undefinedToNull),
        }
      );
      if (!res.ok) throw new Error(`status ${res.status}`);
      const body = await res.json();
      slotRows[n] = body;
      setActiveSlot(n, true);
      try { localStorage.setItem(STORAGE_KEY, body.save_code); } catch (e) { /* convenience only */ }
      showActiveCode(body.save_code);
      renderSlots();
      return true;
    } catch (err) {
      console.error(`${GAME_ID} save-widget: slot save failed`, err);
      return false;
    }
  }

  async function slotLoad(n) {
    const row = slotRows[n];
    if (!row) return;
    if (!window.pyodide) { statusEl.textContent = "Still loading — try again in a moment."; return; }
    const loadState = window.pyodide.globals.get("load_state");
    if (!loadState) { statusEl.textContent = "This game hasn't wired up loading yet."; return; }
    try {
      loadState(window.pyodide.toPy(row.save_data));
      setActiveSlot(n, true);
      try { localStorage.setItem(STORAGE_KEY, row.save_code); } catch (e) { /* convenience only */ }
      showActiveCode(row.save_code);
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
      const card = document.createElement("div");
      card.className = "save-widget-chooser-card";
      card.setAttribute("role", "dialog");
      card.setAttribute("aria-modal", "true");
      const heading = document.createElement("p");
      heading.textContent = "Your account already has saves for this game. Where should this one go?";
      card.appendChild(heading);
      const done = (value) => { overlay.remove(); resolve(value); };
      for (let n = 1; n <= SLOT_COUNT; n++) {
        const row = slotRows[n];
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = row ? `Overwrite slot ${n}: ${row.slot_name || "Save " + n} (${timeAgo(row.updated_at || row.created_at)})` : `Save to empty slot ${n}`;
        button.addEventListener("click", () => done(n));
        card.appendChild(button);
      }
      const cancel = document.createElement("button");
      cancel.type = "button";
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
    await refreshSlots();
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

  // Core save logic (Z25b refactor) -- the ONE code path that actually talks
  // to the save endpoint, shared by the manual "Save Progress" button below
  // and the opt-in autosave timer further down, so autosave can't drift out
  // of sync with a manual save by duplicating its request-building logic.
  // Returns true/false; deliberately leaves ALL user-facing feedback (status
  // text, button disabling) to the caller, since the two call sites want
  // different feedback (a disabled "Saving..." button vs. a silent
  // unattended timer tick).
  async function doSave(onRetrying, silent) {
    if (slotMode()) return doSlotSave(Boolean(silent));
    const state = readGameState();
    if (state === null) {
      statusEl.textContent = "Still loading — try again in a moment.";
      return false;
    }
    if (state === undefined) {
      statusEl.textContent = "This game hasn't wired up saving yet.";
      return false;
    }
    try {
      const code = localStorage.getItem(STORAGE_KEY);
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
      localStorage.setItem(STORAGE_KEY, body.save_code);
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
    statusEl.textContent = ok === null ? "" : ok ? "Saved!" : "Save failed — try again.";
    saveButton.disabled = false;
    saveButton.textContent = "Save Progress";
  });

  // Z25b: opt-in autosave, every 5 minutes, default OFF -- a deliberate,
  // explicit exception to the "no auto-save timer" decision in
  // SAVE-BUTTON-INTEGRATION.md §5 (see that doc's new §7 for the writeup).
  // Calls the exact same doSave() the manual button uses; last-write-wins
  // (already this file's stated design principle) means an autosave and a
  // manual save can never meaningfully "race" each other in a way worth
  // guarding against.
  const AUTOSAVE_KEY = `autosave-enabled:${GAME_ID}`;
  const AUTOSAVE_INTERVAL_MS = 5 * 60 * 1000;
  let autosaveTimer = null;

  function isAutosaveEnabled() {
    try {
      return localStorage.getItem(AUTOSAVE_KEY) === "true";
    } catch (err) {
      return false;
    }
  }

  function setAutosaveEnabled(enabled) {
    try {
      localStorage.setItem(AUTOSAVE_KEY, enabled ? "true" : "false");
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

  // Restore on load. A brand-new visitor has no AUTOSAVE_KEY yet --
  // isAutosaveEnabled() returns false for a missing key, same as an
  // explicit "false", so the default is OFF either way. A returning player
  // who previously turned it on gets the timer running again automatically
  // from page load, without needing to re-check the box every visit.
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
      localStorage.setItem(STORAGE_KEY, body.save_code);
      showActiveCode(body.save_code);
      loadInput.value = "";
      statusEl.textContent = "Loaded!";
    } catch (err) {
      console.error(`${GAME_ID} save-widget: load failed for code ${code}`, err);
      statusEl.textContent = "Load failed — check the code and try again.";
    } finally {
      loadButton.disabled = false;
      loadButton.textContent = "Load";
    }
  });

  claimButton.addEventListener("click", async () => {
    const code = localStorage.getItem(STORAGE_KEY);
    if (!code) return;
    claimButton.disabled = true;
    claimButton.textContent = "Claiming...";
    try {
      const res = await fetchWithRetry(
        `${API_BASE}/saves/${code}/claim`,
        { method: "POST", headers: hubAuthHeaders() },
        () => (statusEl.textContent = "Claiming... (retrying)")
      );
      if (!res.ok) throw new Error(`status ${res.status}`);
      statusEl.textContent = "Save claimed to your account!";
      claimButton.hidden = true;
    } catch (err) {
      console.error(`${GAME_ID} save-widget: claim failed for code ${code}`, err);
      statusEl.textContent = "Claim failed — try again.";
      claimButton.disabled = false;
      claimButton.textContent = "Claim this save to your account";
    }
  });
})();
