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
 * save. No auto-save, no conflict resolution — one explicit button, one
 * explicit save point, last write wins. See §5 of the design doc for why.
 *
 * Signed-in autoload: on page load, if signed in, the widget fetches the
 * account's saves for this game and, if any exist, loads the most recently
 * updated one automatically — the account is the source of truth once
 * signed in, ahead of whatever anonymous code happens to be remembered in
 * this browser's localStorage for this game. Without this, a returning
 * signed-in player who forgot to paste in their code by hand would see a
 * blank farm/city/settlement every time and reasonably read that as "my
 * save keeps resetting" — it wasn't resetting, it just was never loading.
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
  const AUTH_TOKEN_KEY = "hub_bearer_token";

  // REVIEW(reuse): duplicated in script.js (getBearerToken/authHeaders) —
  // both independently hardcode the "hub_bearer_token" localStorage key and
  // build the same Authorization header object. A future key rename in one
  // file without the other would silently break auth-gated save loading.
  function authHeaders() {
    const token = localStorage.getItem(AUTH_TOKEN_KEY);
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  if (!document.getElementById("save-widget-styles")) {
    const style = document.createElement("style");
    style.id = "save-widget-styles";
    style.textContent = `
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
        text-align: left;
      }
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
    <button type="button" class="save-widget-toggle">&#128190; Save / Load</button>
    <div class="save-widget-body">
      <button type="button" class="save-widget-save-button">Save Progress</button>
      <p class="save-widget-code" hidden></p>
      <button type="button" class="save-widget-claim-button save-widget-link" hidden>Claim this save to your account</button>
      <button type="button" class="save-widget-new-button save-widget-link" hidden>Start a new save (forget this code)</button>
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
  const codeDisplay = root.querySelector(".save-widget-code");
  const claimButton = root.querySelector(".save-widget-claim-button");
  const newButton = root.querySelector(".save-widget-new-button");
  const loadInput = root.querySelector(".save-widget-load-input");
  const loadButton = root.querySelector(".save-widget-load-button");
  const statusEl = root.querySelector(".save-widget-status");
  const toggleButton = root.querySelector(".save-widget-toggle");

  toggleButton.addEventListener("click", () => root.classList.toggle("collapsed"));

  function showActiveCode(code) {
    codeDisplay.textContent = `Code: ${code}`;
    codeDisplay.hidden = false;
    newButton.hidden = false;
    claimButton.hidden = !localStorage.getItem(AUTH_TOKEN_KEY);
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
    const token = localStorage.getItem(AUTH_TOKEN_KEY);
    if (!token) return false;
    let saves;
    try {
      const res = await fetch(`${API_BASE}/users/me/saves`, { headers: authHeaders() });
      if (!res.ok) return false;
      saves = await res.json();
    // REVIEW(observability): `err` is discarded here and in every other catch
    // in this file — nothing is logged to the console, so a user-reported
    // "my save isn't loading" is undebuggable from the browser side: no way
    // to tell network failure vs. bad response vs. JSON parse error apart.
    } catch (err) {
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
      return false;
    }
    try {
      loadState(window.pyodide.toPy(mostRecent.save_data));
    } catch (err) {
      return false;
    }
    localStorage.setItem(STORAGE_KEY, mostRecent.save_code);
    showActiveCode(mostRecent.save_code);
    // This came from GET /users/me/saves -- the account's own saves list --
    // so it's already claimed to this account. Offering to claim it again
    // would be redundant (and confusing) even though it's a harmless no-op.
    claimButton.hidden = true;
    statusEl.textContent = "Continued your most recent save.";
    return true;
  }

  (async () => {
    if (await tryAutoLoadFromAccount()) return;
    const existingCode = localStorage.getItem(STORAGE_KEY);
    if (existingCode) showActiveCode(existingCode);
  })();

  newButton.addEventListener("click", () => {
    localStorage.removeItem(STORAGE_KEY);
    codeDisplay.hidden = true;
    newButton.hidden = true;
    claimButton.hidden = true;
    statusEl.textContent = "Next save starts a fresh code.";
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
      return undefined;
    } finally {
      if (proxy && typeof proxy.destroy === "function") proxy.destroy();
    }
  }

  saveButton.addEventListener("click", async () => {
    const state = readGameState();
    if (state === null) {
      statusEl.textContent = "Still loading — try again in a moment.";
      return;
    }
    if (state === undefined) {
      statusEl.textContent = "This game hasn't wired up saving yet.";
      return;
    }
    saveButton.disabled = true;
    saveButton.textContent = "Saving...";
    try {
      const code = localStorage.getItem(STORAGE_KEY);
      const res = await fetch(code ? `${API_BASE}/saves/${code}` : `${API_BASE}/saves`, {
        method: code ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(
          code ? { save_data: state } : { game_id: GAME_ID, save_data: state },
          undefinedToNull
        ),
      });
      if (!res.ok) throw new Error(`status ${res.status}`);
      const body = await res.json();
      localStorage.setItem(STORAGE_KEY, body.save_code);
      showActiveCode(body.save_code);
      statusEl.textContent = "Saved!";
    } catch (err) {
      statusEl.textContent = "Save failed — try again.";
    } finally {
      saveButton.disabled = false;
      saveButton.textContent = "Save Progress";
    }
  });

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
      const res = await fetch(`${API_BASE}/saves/${code}`);
      if (!res.ok) throw new Error(`status ${res.status}`);
      const body = await res.json();
      loadState(window.pyodide.toPy(body.save_data));
      localStorage.setItem(STORAGE_KEY, body.save_code);
      showActiveCode(body.save_code);
      loadInput.value = "";
      statusEl.textContent = "Loaded!";
    } catch (err) {
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
      const res = await fetch(`${API_BASE}/saves/${code}/claim`, {
        method: "POST",
        headers: authHeaders(),
      });
      if (!res.ok) throw new Error(`status ${res.status}`);
      statusEl.textContent = "Save claimed to your account!";
      claimButton.hidden = true;
    } catch (err) {
      statusEl.textContent = "Claim failed — try again.";
      claimButton.disabled = false;
      claimButton.textContent = "Claim this save to your account";
    }
  });
})();
