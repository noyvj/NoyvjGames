/*
 * Shared opening screen (U4) — a per-game "homepage" shown before the game
 * itself, so the growing toolbar of buttons stops being the first thing a
 * player meets. One include per game, right after shared/save-widget.js:
 *   <script src="../../shared/opening-screen.js" data-game-id="<slug>"
 *           data-game-name="<Display Name>"></script>
 *
 * Every game starts from this same basic layout (per the user's U4 answer:
 * each game is built separately from a common starting point, then
 * personalised). Buttons:
 *   Continue  -- first, and only when a save exists (signed in, or a stored
 *                save code for this browser); loads the latest save.
 *   New Game  -- starts fresh; then offers the tutorial (the tutorial no
 *                longer auto-starts, it is offered only from here).
 *   Saves     -- closes the screen and opens the save/load panel.
 *   Settings / Info -- click the game's own #settings-toggle-button /
 *                #info-page-toggle-button, hidden if the game has neither.
 *   Feedback  -- opens the hub's feedback form in a new tab.
 *
 * Coordination with the other shared scripts (all optional):
 *   - window.NoyvjOpeningScreen.choice is a promise resolving "continue" or
 *     "new". save-widget.js waits on it before its signed-in autoload, so a
 *     New Game is never overwritten by the account's latest save.
 *   - window.__openingScreenOwnsTutorial tells shared/tutorial.js not to
 *     auto-start on first visit.
 *   - Adding "#play" to the URL skips the screen (choice "continue"), which
 *     keeps deep links and automated checks working.
 * Personalisation (U4b): data-tagline sets the line under the title; Continue
 * shows when (and which slot) the latest save was made; and a game that has a
 * visual-set switcher (today only Le Champ de Mots, via
 * window.ChampDeMotsVisualStyle, desktop widths only) gets a "pick a look"
 * step after New Game, with the live example being the page itself and a
 * "you can change this later in Settings" note. Dark/light lives in general
 * Settings (Y11).
 */
(function () {
  const SCRIPT = document.currentScript;
  const GAME_ID = SCRIPT && SCRIPT.dataset.gameId;
  const GAME_NAME = (SCRIPT && SCRIPT.dataset.gameName) || GAME_ID;
  const TAGLINE = (SCRIPT && SCRIPT.dataset.tagline) || "Welcome. Pick up where you left off, or start fresh.";
  const API_BASE = "https://noyvjgames.fastapicloud.dev";
  if (!GAME_ID) {
    console.error("opening-screen.js: missing required data-game-id attribute on its <script> tag");
    return;
  }

  let resolveChoice;
  const choice = new Promise((resolve) => { resolveChoice = resolve; });
  window.NoyvjOpeningScreen = { choice };
  window.__openingScreenOwnsTutorial = true;

  const SAVE_KEY = `savecode:${GAME_ID}`;
  const TOKEN_KEY = typeof HUB_AUTH_TOKEN_KEY !== "undefined" ? HUB_AUTH_TOKEN_KEY : "hub_bearer_token";

  function lsGet(key) {
    try { return localStorage.getItem(key); } catch (err) { return null; }
  }
  function lsRemove(key) {
    try { localStorage.removeItem(key); } catch (err) { /* non-fatal */ }
  }

  if (location.hash === "#play") {
    resolveChoice("continue");
    return;
  }

  const STYLE_ID = "opening-screen-styles";
  function injectStyles() {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent = `
      #opening-screen {
        position: fixed; inset: 0; z-index: 9000;
        display: flex; align-items: center; justify-content: center;
        padding: 1rem;
        background: radial-gradient(ellipse at 50% 30%, rgba(30, 34, 58, 0.97), rgba(8, 9, 16, 0.99));
        color: #e8eaf6; font-family: inherit;
      }
      #opening-screen .opening-card {
        width: min(26rem, 100%); text-align: center;
        display: flex; flex-direction: column; gap: 0.6rem;
      }
      #opening-screen h1 { margin: 0 0 0.2rem; font-size: 2rem; }
      #opening-screen .opening-sub { margin: 0 0 0.8rem; opacity: 0.75; font-size: 0.95rem; }
      #opening-screen button, #opening-screen a.opening-button {
        display: block; box-sizing: border-box; width: 100%;
        padding: 0.8rem 1rem; font: inherit; font-size: 1rem; text-align: center;
        color: inherit; text-decoration: none; cursor: pointer;
        background: rgba(140, 160, 255, 0.1);
        border: 1px solid rgba(140, 160, 255, 0.3); border-radius: 12px;
      }
      #opening-screen button:hover, #opening-screen a.opening-button:hover,
      #opening-screen button:focus-visible, #opening-screen a.opening-button:focus-visible {
        background: rgba(140, 160, 255, 0.22); outline: none;
      }
      #opening-screen .opening-primary {
        background: rgba(140, 160, 255, 0.28); border-color: rgba(170, 190, 255, 0.6); font-weight: 600;
      }
      #opening-screen .opening-continue-note { display: block; font-size: 0.75rem; font-weight: 400; opacity: 0.75; }
      #opening-screen .opening-continue-note:empty { display: none; }
      #opening-screen .opening-style-buttons { display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; margin-bottom: 0.6rem; }
      #opening-screen .opening-style-buttons button[aria-pressed="true"] { border-color: #a9c3ff; background: rgba(140, 160, 255, 0.3); }
      #opening-screen .opening-row { display: flex; gap: 0.5rem; }
      #opening-screen .opening-row > * { flex: 1 1 0; }
      #opening-screen .opening-back { font-size: 0.85rem; opacity: 0.7; margin-top: 0.4rem; }
      #opening-screen [hidden] { display: none; }
    `;
    document.head.appendChild(style);
  }

  function signedIn() { return Boolean(lsGet(TOKEN_KEY)); }
  function storedCode() { return lsGet(SAVE_KEY); }
  function hasSave() { return signedIn() || Boolean(storedCode()); }

  function waitFor(predicate, timeoutMs, intervalMs) {
    return new Promise((resolve) => {
      const started = Date.now();
      (function check() {
        if (predicate()) return resolve(true);
        if (Date.now() - started > (timeoutMs || 15000)) return resolve(false);
        setTimeout(check, intervalMs || 150);
      })();
    });
  }
  const gameReady = () => Boolean(window.pyodide && window.pyodide.globals.get("load_state"));

  function build() {
    injectStyles();
    const root = document.createElement("div");
    root.id = "opening-screen";
    root.setAttribute("role", "dialog");
    root.setAttribute("aria-modal", "true");
    root.setAttribute("aria-label", `${GAME_NAME} — start`);
    root.innerHTML = `
      <div class="opening-card">
        <h1></h1>
        <p class="opening-sub opening-tagline"></p>
        <div class="opening-menu">
          <button type="button" class="opening-primary" data-action="continue" hidden>Continue<small class="opening-continue-note"></small></button>
          <button type="button" class="opening-primary" data-action="new">New Game</button>
          <button type="button" data-action="saves">Saves</button>
          <div class="opening-row">
            <button type="button" data-action="settings" hidden>Settings</button>
            <button type="button" data-action="info" hidden>Info</button>
            <a class="opening-button" data-action="feedback" target="_blank" rel="noopener" href="../../index.html#site-feedback-section">Feedback</a>
          </div>
        </div>
        <div class="opening-style" hidden>
          <p class="opening-sub">Pick a look for your farm. You can change this any time in Settings.</p>
          <div class="opening-style-buttons"></div>
          <button type="button" class="opening-primary" data-action="style-confirm">Confirm</button>
        </div>
        <div class="opening-tutorial" hidden>
          <p class="opening-sub">Want a quick tutorial first?</p>
          <button type="button" class="opening-primary" data-action="tutorial-yes">Show me how it works</button>
          <button type="button" data-action="tutorial-no">Skip, just play</button>
        </div>
        <p class="opening-status" role="status" hidden></p>
      </div>`;
    root.querySelector("h1").textContent = GAME_NAME;
    root.querySelector(".opening-tagline").textContent = TAGLINE;
    return root;
  }

  function close(root) {
    root.remove();
    document.body.style.removeProperty("overflow");
  }

  function clickIfPresent(id) {
    const el = document.getElementById(id);
    if (el) el.click();
    return Boolean(el);
  }

  async function doContinue(root) {
    resolveChoice("continue");
    const code = storedCode();
    if (!signedIn() && code) {
      const status = root.querySelector(".opening-status");
      status.hidden = false;
      status.textContent = "Loading your save…";
      if (await waitFor(gameReady, 20000)) {
        const input = document.querySelector(".save-widget-load-input");
        const button = document.querySelector(".save-widget-load-button");
        if (input && button) {
          input.value = code;
          button.click();
        }
      }
    }
    close(root);
  }

  function timeAgo(iso) {
    if (!iso) return "";
    const seconds = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
    if (seconds < 90) return "just now";
    if (seconds < 5400) return `${Math.round(seconds / 60)} min ago`;
    if (seconds < 129600) return `${Math.round(seconds / 3600)} h ago`;
    return `${Math.round(seconds / 86400)} d ago`;
  }

  // U4b: "Slot 2 · 3 h ago" under Continue. Best effort, silent on any failure.
  async function fillContinueNote(root) {
    const note = root.querySelector(".opening-continue-note");
    try {
      let text = "";
      if (signedIn()) {
        const token = lsGet(TOKEN_KEY);
        const res = await fetch(`${API_BASE}/users/me/saves`, { headers: { Authorization: `Bearer ${token}` }, cache: "no-store" });
        if (!res.ok) return;
        const mine = (await res.json()).filter((r) => r.game_id === GAME_ID)
          .sort((a, b) => new Date(b.updated_at || b.created_at) - new Date(a.updated_at || a.created_at));
        if (!mine.length) return;
        text = `${mine[0].slot ? "Slot " + mine[0].slot + " · " : ""}${timeAgo(mine[0].updated_at || mine[0].created_at)}`;
      } else if (storedCode()) {
        const res = await fetch(`${API_BASE}/saves/${encodeURIComponent(storedCode())}`, { cache: "no-store" });
        if (!res.ok) return;
        const body = await res.json();
        text = `Saved ${timeAgo(body.updated_at || body.created_at)}`;
      }
      note.textContent = text;
    } catch (err) { /* offline or not deployed yet: leave the note empty */ }
  }

  const STYLE_LABELS = { highdef: "High-def", lowpoly: "Low-poly", textbased: "Text-based", cartoon: "Cartoon" };

  function showStyleStep(root) {
    const picker = window.ChampDeMotsVisualStyle;
    const wide = window.matchMedia && window.matchMedia("(min-width: 768px)").matches;
    if (!picker || !wide) return false;
    const box = root.querySelector(".opening-style-buttons");
    box.innerHTML = "";
    const current = document.documentElement.getAttribute("data-visual-style") || picker.DEFAULT_STYLE;
    picker.STYLES.forEach((name) => {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = STYLE_LABELS[name] || name;
      button.setAttribute("aria-pressed", String(name === current));
      button.addEventListener("click", () => {
        picker.applyStyle(name);
        box.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b === button)));
      });
      box.appendChild(button);
    });
    root.querySelector(".opening-style").hidden = false;
    return true;
  }

  function afterNewGame(root) {
    root.querySelector(".opening-menu").hidden = true;
    if (showStyleStep(root)) return;
    showTutorialOffer(root);
  }

  function showTutorialOffer(root) {
    root.querySelector(".opening-style").hidden = true;
    if (window.GameTutorial) {
      root.querySelector(".opening-tutorial").hidden = false;
      root.querySelector('[data-action="tutorial-yes"]').focus();
    } else {
      close(root);
    }
  }

  function askNewGame(root) {
    const code = storedCode();
    const go = () => {
      resolveChoice("new");
      if (code) lsRemove(SAVE_KEY);
      afterNewGame(root);
    };
    if (code && window.ConfirmDialog) {
      window.ConfirmDialog.ask({
        id: `opening-new-${GAME_ID}`,
        message: `Start a new game? Your current save code is ${code}. It stays valid for loading, but this browser will stop using it, so note it down first if you want to keep it.`,
        confirmLabel: "Start new game",
        allowSkip: false,
        onConfirm: go,
      });
    } else {
      go();
    }
  }

  async function startTutorial(root) {
    close(root);
    if (await waitFor(gameReady, 20000)) {
      setTimeout(() => {
        if (window.GameTutorial && typeof window.GameTutorial.start === "function") {
          window.GameTutorial.start();
        }
      }, 800);
    }
  }

  function show() {
    const root = build();
    document.body.appendChild(root);
    document.body.style.overflow = "hidden";
    const q = (action) => root.querySelector(`[data-action="${action}"]`);
    if (hasSave()) q("continue").hidden = false;
    if (document.getElementById("settings-toggle-button")) q("settings").hidden = false;
    if (document.getElementById("info-page-toggle-button")) q("info").hidden = false;

    q("continue").addEventListener("click", () => doContinue(root));
    q("new").addEventListener("click", () => askNewGame(root));
    q("saves").addEventListener("click", () => {
      resolveChoice("continue");
      close(root);
      const widget = document.getElementById("save-widget");
      if (widget) {
        const toggle = widget.querySelector(".save-widget-toggle");
        if (toggle && toggle.getAttribute("aria-expanded") === "false") toggle.click();
        widget.scrollIntoView({ block: "center" });
        const input = widget.querySelector(".save-widget-load-input");
        if (input) input.focus();
      }
    });
    for (const [action, id] of [["settings", "settings-toggle-button"], ["info", "info-page-toggle-button"]]) {
      q(action).addEventListener("click", () => {
        resolveChoice("continue");
        close(root);
        clickIfPresent(id);
      });
    }
    q("style-confirm").addEventListener("click", () => showTutorialOffer(root));
    if (hasSave()) fillContinueNote(root);
    q("tutorial-yes").addEventListener("click", () => startTutorial(root));
    q("tutorial-no").addEventListener("click", () => close(root));
    const first = root.querySelector("button:not([hidden])");
    if (first) first.focus();
  }

  if (document.body) show();
  else document.addEventListener("DOMContentLoaded", show);
})();
