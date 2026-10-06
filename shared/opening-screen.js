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
 * Back to the main page (UX-8): after the screen is dismissed, a small "Main menu"
 * control (built here) re-opens it at any time without losing progress. It sits in
 * the save widget's header row (bottom-right, next to Save / Load) on the Classic
 * page, and in the shell's own Menu window on the Desktop boot (pages with a
 * #pc-topbar); with neither, it is a small fixed button. window.NoyvjOpeningScreen
 * .show() does the same from any other control. Re-opened this way "Continue" reads
 * "Resume game" (it only closes the screen), "Load latest save" is a separate
 * choice, and "New Game" always asks first and then restarts the page fresh.
 * The main page also links back to the hub ("All games").
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
  const NEW_GAME_KEY = `opening-new-game:${GAME_ID}`;
  const TOKEN_KEY = typeof HUB_AUTH_TOKEN_KEY !== "undefined" ? HUB_AUTH_TOKEN_KEY : "hub_bearer_token";

  function lsGet(key) {
    try { return localStorage.getItem(key); } catch (err) { return null; }
  }
  function lsRemove(key) {
    try { localStorage.removeItem(key); } catch (err) { /* non-fatal */ }
  }

  // "New Game" chosen from the main menu mid-play reloads the page (the only generic way
  // to reset any game) and leaves this one-shot flag so the fresh page knows the player
  // already chose New Game: the account's latest save must not be loaded over it.
  let startedFresh = false;
  try {
    startedFresh = sessionStorage.getItem(NEW_GAME_KEY) === "1";
    sessionStorage.removeItem(NEW_GAME_KEY);
  } catch (err) { /* non-fatal */ }

  // The page counts as "in play" once the first overlay has been answered, and from the
  // start when "#play" skips it.
  let overlayRoot = null;
  let inPlay = false;
  let skipFirstScreen = false;
  if (location.hash === "#play") {
    skipFirstScreen = true;
    resolveChoice(startedFresh ? "new" : "continue");
  }

  const STYLE_ID = "opening-screen-styles";
  function injectStyles() {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent = `
      /* UX-6: the card is centred with auto margins inside a scrolling flex container, so
         a short window (or a tall card with several saves) scrolls instead of clipping the
         top and bottom, and the save widget (z-index 9999, bottom-right) is hidden while
         this screen is up rather than sitting on top of its buttons. */
      html.opening-screen-open #save-widget { visibility: hidden; }
      #opening-screen {
        position: fixed; inset: 0; z-index: 9000;
        display: flex; justify-content: center;
        overflow-y: auto; overscroll-behavior: contain; box-sizing: border-box;
        padding: 1rem;
        background: radial-gradient(ellipse at 50% 30%, rgba(30, 34, 58, 0.97), rgba(8, 9, 16, 0.99));
        color: #e8eaf6; font-family: inherit;
      }
      #opening-screen .opening-card {
        width: min(26rem, 100%); text-align: center; margin: auto 0;
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
      #opening-screen .opening-row { display: flex; flex-wrap: wrap; gap: 0.5rem; }
      #opening-screen .opening-row > * { flex: 1 1 8rem; min-width: 0; overflow-wrap: anywhere; }
      #opening-screen .opening-back { font-size: 0.85rem; opacity: 0.7; margin-top: 0.4rem; }
      #opening-screen [hidden] { display: none; }
      #opening-screen .opening-hub { font-size: 0.9rem; opacity: 0.85; }
      #noyvj-menu-button { font: inherit; font-size: 0.72rem; cursor: pointer; border-radius: 6px; }
      #noyvj-menu-button.noyvj-menu-button-fixed { position: fixed; right: 12px; bottom: 12px; z-index: 9990; padding: 0.35rem 0.6rem;
        background: rgba(18, 20, 31, 0.94); color: #eaeaf0; border: 1px solid #2a3a4c; box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4); }
      html[data-theme="light"] #noyvj-menu-button.noyvj-menu-button-fixed { background: rgba(255, 255, 255, 0.96); color: #1b2033; border-color: rgba(70, 95, 170, 0.3); }
    `;
    document.head.appendChild(style);
  }

  function signedIn() { return Boolean(lsGet(TOKEN_KEY)); }
  function storedCode() { return lsGet(SAVE_KEY); }
  function hasSave() { return signedIn() || Boolean(storedCode()); }

  // The backend sends timestamps with a UTC offset (Postgres) or, from a naive-timestamp
  // database, with none; a bare "2026-10-06T18:05:17" is UTC, not local time.
  function parseTime(iso) {
    if (!iso) return 0;
    const text = String(iso);
    const hasZone = /(Z|[+-]\d{2}:?\d{2})$/i.test(text);
    const ms = new Date(hasZone ? text : `${text}Z`).getTime();
    return Number.isNaN(ms) ? 0 : ms;
  }

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

  function build(menuMode) {
    injectStyles();
    const root = document.createElement("div");
    root.id = "opening-screen";
    root.setAttribute("role", "dialog");
    root.setAttribute("aria-modal", "true");
    root.setAttribute("aria-label", `${GAME_NAME} — ${menuMode ? "main menu" : "start"}`);
    root.innerHTML = `
      <div class="opening-card">
        <h1></h1>
        <p class="opening-sub opening-tagline"></p>
        <div class="opening-menu">
          <button type="button" class="opening-primary" data-action="continue" hidden><span class="opening-continue-label">Continue</span><small class="opening-continue-note"></small></button>
          <button type="button" data-action="load-latest" hidden>Load latest save</button>
          <button type="button" class="opening-primary" data-action="new">New Game</button>
          <button type="button" data-action="saves">Saves</button>
          <button type="button" data-action="layout" hidden></button>
          <div class="opening-row">
            <button type="button" data-action="settings" hidden>Settings</button>
            <button type="button" data-action="info" hidden>Info</button>
            <a class="opening-button" data-action="feedback" target="_blank" rel="noopener" href="../../index.html#site-feedback-section">Feedback</a>
          </div>
          <a class="opening-button opening-hub" data-action="hub" href="../../index.html">&larr; All games</a>
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

  let previousOverflow = "";
  let escapeHandler = null;

  function close(root) {
    root.remove();
    if (overlayRoot === root) overlayRoot = null;
    document.documentElement.classList.remove("opening-screen-open");
    if (previousOverflow) document.body.style.overflow = previousOverflow;
    else document.body.style.removeProperty("overflow");
    previousOverflow = "";
    if (escapeHandler) {
      document.removeEventListener("keydown", escapeHandler, true);
      escapeHandler = null;
    }
    // Whatever way the screen was answered, play has begun: the way back is now available.
    inPlay = true;
    ensureMenuControl(true);
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
    const seconds = Math.max(0, (Date.now() - parseTime(iso)) / 1000);
    if (seconds < 90) return "just now";
    if (seconds < 5400) return `${Math.round(seconds / 60)} min ago`;
    if (seconds < 129600) return `${Math.round(seconds / 3600)} h ago`;
    return `${Math.round(seconds / 86400)} d ago`;
  }

  // U4b: "Slot 2 · 3 h ago" under Continue. Best effort, silent on any failure.
  // A signed-in player with no code remembered here and no account save for this game
  // has nothing to continue, so the Continue button is hidden again (menuMode keeps it:
  // there it means "back to the game", which always exists).
  async function fillContinueNote(root, menuMode) {
    const note = root.querySelector(".opening-continue-note");
    const continueButton = root.querySelector('[data-action="continue"]');
    try {
      let text = "";
      if (signedIn()) {
        const token = lsGet(TOKEN_KEY);
        const res = await fetch(`${API_BASE}/users/me/saves`, { headers: { Authorization: `Bearer ${token}` }, cache: "no-store" });
        if (!res.ok) return;
        const mine = (await res.json()).filter((r) => r.game_id === GAME_ID)
          .sort((a, b) => parseTime(b.updated_at || b.created_at) - parseTime(a.updated_at || a.created_at));
        if (!mine.length) {
          if (!menuMode && !storedCode() && continueButton && root.isConnected) continueButton.hidden = true;
          const loadLatest = root.querySelector('[data-action="load-latest"]');
          if (loadLatest && !storedCode()) loadLatest.hidden = true;
          return;
        }
        text = `${mine[0].slot ? "Slot " + mine[0].slot + " · " : ""}${timeAgo(mine[0].updated_at || mine[0].created_at)}`;
      } else if (storedCode()) {
        const res = await fetch(`${API_BASE}/saves/${encodeURIComponent(storedCode())}`, { cache: "no-store" });
        if (!res.ok) return;
        const body = await res.json();
        text = `Saved ${timeAgo(body.updated_at || body.created_at)}`;
      }
      if (menuMode) {
        const loadLatest = root.querySelector('[data-action="load-latest"]');
        if (loadLatest && text) loadLatest.title = `Latest save: ${text}`;
      } else {
        note.textContent = text;
      }
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

  function askNewGame(root, menuMode) {
    const code = storedCode();
    const go = () => {
      resolveChoice("new");
      if (code) lsRemove(SAVE_KEY);
      if (menuMode) {
        // A game is already running in this page: reload for a clean start. The flag tells
        // the fresh page that New Game was chosen (so no save is loaded over it) and it
        // goes straight to the tutorial offer. Nothing saved on the server is touched.
        try { sessionStorage.setItem(NEW_GAME_KEY, "1"); } catch (err) { /* falls back to a plain reload */ }
        // "#play" (a deep link that skips this screen) is dropped so the fresh page offers the tutorial.
        if (location.hash === "#play") {
          try { history.replaceState(null, "", location.pathname + location.search); } catch (err) { /* keep the hash */ }
        }
        location.reload();
        return;
      }
      afterNewGame(root);
    };
    if (menuMode) {
      const message = "Start a new game? Progress you have not saved is lost" +
        (code ? `, and this browser stops using your current save code (${code}), which stays valid for loading, so note it down first if you want to keep it.` : ".");
      if (window.ConfirmDialog) {
        window.ConfirmDialog.ask({
          id: `opening-new-menu-${GAME_ID}`, message, confirmLabel: "Start new game", allowSkip: false, onConfirm: go,
        });
      } else if (window.confirm(message)) {
        go();
      }
      return;
    }
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

  // Menu mode: reload the latest save over the running game, after asking.
  function askLoadLatest(root) {
    const status = root.querySelector(".opening-status");
    const go = async () => {
      status.hidden = false;
      status.textContent = "Loading your latest save…";
      const api = window.NoyvjSaveWidget;
      let ok = false;
      try { ok = Boolean(api && (await api.loadLatest())); } catch (err) { ok = false; }
      if (ok) {
        close(root);
      } else {
        status.textContent = "Couldn't load a save just now. Your game is unchanged.";
      }
    };
    const message = "Load your latest save? Progress since you last saved is replaced by that save.";
    if (window.ConfirmDialog) {
      window.ConfirmDialog.ask({ id: `opening-load-latest-${GAME_ID}`, message, confirmLabel: "Load latest save", allowSkip: false, onConfirm: go });
    } else if (window.confirm(message)) {
      go();
    }
  }

  // menuMode = the screen is being re-opened mid-play from the Main menu control.
  function show(menuMode, afterNew) {
    if (overlayRoot) return overlayRoot;
    const root = build(Boolean(menuMode));
    overlayRoot = root;
    document.body.appendChild(root);
    document.documentElement.classList.add("opening-screen-open");
    previousOverflow = document.body.style.overflow || "";
    document.body.style.overflow = "hidden";
    const q = (action) => root.querySelector(`[data-action="${action}"]`);
    if (menuMode) {
      // Back to the main page without touching the game: Continue becomes "Resume".
      q("continue").hidden = false;
      q("continue").querySelector(".opening-continue-label").textContent = "Resume game";
      q("continue").querySelector(".opening-continue-note").textContent = "Back to where you are now";
      if (hasSave()) q("load-latest").hidden = false;
      escapeHandler = (e) => {
        if (e.key !== "Escape" || document.querySelector("#confirm-dialog-overlay:not([hidden])")) return;
        e.stopPropagation();
        close(root);
      };
      document.addEventListener("keydown", escapeHandler, true);
    } else if (hasSave()) {
      q("continue").hidden = false;
    }
    if (document.getElementById("settings-toggle-button")) q("settings").hidden = false;
    if (document.getElementById("info-page-toggle-button")) q("info").hidden = false;

    // PC version plan: a game with a Desktop boot (shared/layout-pref.js) offers the
    // other boot here, before anything is played. Saves are shared, so it only costs
    // a reload. Desktop is only offered on a wide window with a mouse-like pointer.
    const layout = window.NoyvjLayout;
    if (layout) {
      const toPc = layout.current !== "pc";
      if (!toPc || layout.capable()) {
        q("layout").hidden = false;
        q("layout").textContent = toPc ? "Switch to Desktop layout" : "Switch to Classic layout";
        q("layout").addEventListener("click", () => layout.switchTo(toPc ? "pc" : "classic"));
      }
    }
    q("continue").addEventListener("click", () => (menuMode ? close(root) : doContinue(root)));
    q("load-latest").addEventListener("click", () => askLoadLatest(root));
    q("new").addEventListener("click", () => askNewGame(root, menuMode));
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
    if (hasSave()) fillContinueNote(root, Boolean(menuMode));
    q("tutorial-yes").addEventListener("click", () => startTutorial(root));
    q("tutorial-no").addEventListener("click", () => close(root));
    if (afterNew) afterNewGame(root);
    else {
      const first = root.querySelector("button:not([hidden])");
      if (first) first.focus({ preventScroll: true });
    }
    return root;
  }

  // ---- UX-8: the way back to this screen ------------------------------------------------

  function reopen() {
    if (overlayRoot) return;
    show(true);
  }

  const MENU_TITLE = "Back to the game's main page (Continue, New Game, Saves, Settings)";

  function menuButton(label) {
    const button = document.createElement("button");
    button.type = "button";
    button.id = "noyvj-menu-button";
    button.textContent = label || "\u2630 Menu";
    button.title = MENU_TITLE;
    button.setAttribute("aria-label", "Main menu");
    button.addEventListener("click", reopen);
    return button;
  }

  const isDesktopBoot = () => window.NOYVJ_LAYOUT === "pc" || Boolean(document.getElementById("pc-topbar"));

  // Classic page: one small button in the save widget's header row (bottom-right, beside
  // Save / Load). Desktop boot (a #pc-topbar page): an entry at the top of the shell's Menu
  // window, since the shell owns the screen edges there. Only if neither host exists (or,
  // with `final`, never showed up) is it a small fixed button. Idempotent; called again when
  // a host may have appeared, because script order is not guaranteed.
  function ensureMenuControl(final) {
    if (!inPlay || document.getElementById("noyvj-menu-button")) return;
    if (isDesktopBoot()) {
      const pcMenu = document.getElementById("pc-menu-panel");
      if (pcMenu) {
        const group = document.createElement("div");
        group.className = "pc-menu-group";
        group.id = "noyvj-menu-pc-entry";
        const heading = document.createElement("h3");
        heading.textContent = "Main page";
        const button = menuButton("\u2630 Main menu");
        button.className = "secondary";
        group.append(heading, button);
        pcMenu.insertBefore(group, pcMenu.firstChild);
        return;
      }
      if (!final) return;
    } else {
      const header = document.querySelector("#save-widget .save-widget-header");
      if (header) {
        const button = menuButton();
        button.className = "noyvj-menu-button";
        header.insertBefore(button, header.firstChild);
        return;
      }
      if (!final && !document.body) return;
    }
    const button = menuButton();
    button.className = "noyvj-menu-button noyvj-menu-button-fixed";
    injectStyles();
    document.body.appendChild(button);
  }

  window.NoyvjOpeningScreen.show = reopen;
  window.NoyvjOpeningScreen.isOpen = () => Boolean(overlayRoot);

  function boot() {
    injectStyles();
    if (skipFirstScreen) {
      inPlay = true;
      ensureMenuControl();
    } else if (startedFresh) {
      resolveChoice("new");
      show(false, true);
    } else {
      show(false);
    }
    // The save widget (mounted by its own script) and the Desktop shell build their hosts
    // at load; pick them up once they exist instead of assuming an order.
    // Only the first answer to the screen ends this wait early; the host check is re-run on
    // close() too, so a slow shell or widget is still picked up.
    waitFor(() => document.querySelector(isDesktopBoot() ? "#pc-menu-panel" : "#save-widget .save-widget-header"), 8000, 200)
      .then(() => ensureMenuControl(false));
    setTimeout(() => ensureMenuControl(true), 8500);
  }

  if (document.body) boot();
  else document.addEventListener("DOMContentLoaded", boot);
})();
