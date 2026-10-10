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
 * Z-22 (placement): the widget is a small pill in the TOP-RIGHT corner, collapsed on every screen
 * size at every page load, showing a live "Saved 5 min ago" line that turns into the plain-text
 * warning "Save failed — try again" when the last save attempt (manual or autosave) failed. It
 * steps below any full-width bar fixed to the top (what's-new banner, mobile HUD, seasonal strip,
 * top ad bar), and on the Desktop boot it reserves its own corner in #pc-topbar. The opened panel
 * drops down from the pill and scrolls inside itself, leaving the bottom ad bar clear.
 *
 * Z-10 (time machine): the last 5 snapshots of the game state per game and slot are kept in
 * localStorage (size-guarded, failure is silent) and, signed in, on the backend
 * (/users/me/snapshots). One is taken just before a Load, a New Game or a restore overwrites the
 * current state, and on autosave at most once per 10 minutes; an empty or never-played default
 * state is never snapshotted. "Restore an earlier state" lists them with time and a one-line
 * summary (the page's share_result / copy_result_fields headline, else "N keys, X KB"), asks
 * through the shared confirm dialog, and snapshots the current state first so a restore can
 * itself be undone. window.NoyvjSaveWidget.snapshotNow(reason) lets the opening screen take one
 * before New Game.
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

  // Z-13: every sentence the player reads goes through tr(key, english, vars). The English text is
  // right here, so with no translation (English chosen, shared/i18n.js absent or not loaded yet, a key
  // missing from the language file) the widget reads exactly as it always did. A language other than
  // English asks for shared/i18n.js itself, so no game page needs a new <script> tag; when the strings
  // arrive, relabelStatic() fixes the parts already on screen.
  function tr(key, english, vars) {
    const i18n = window.NoyvjI18n;
    if (i18n) return i18n.t(key, english, vars);
    return vars ? english.replace(/\{(\w+)\}/g, (m, name) => (name in vars ? String(vars[name]) : m)) : english;
  }
  (function bootI18n() {
    try {
      const chosen = localStorage.getItem("hub_lang");
      if (!window.NoyvjI18n && chosen && chosen !== "en" && document.currentScript && document.currentScript.src) {
        const tag = document.createElement("script");
        tag.src = new URL("i18n.js", document.currentScript.src).href;
        document.head.appendChild(tag);
      }
    } catch (err) { /* storage blocked: stay in English */ }
  })();

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
        top: var(--save-widget-top, 6px);
        right: var(--save-widget-right, 6px);
        bottom: auto;
        z-index: 9999;
        background: rgba(18, 20, 31, 0.94);
        border: 1px solid #2a3a4c;
        border-radius: 12px;
        padding: 4px 6px;
        font-family: system-ui, -apple-system, sans-serif;
        font-size: 0.78rem;
        color: #eaeaf0;
        width: 224px;
        box-sizing: border-box;
        /* Opened, the panel drops down from the top corner. Cap it to the room between its top
           and the bottom ad bar (50px) and scroll inside it, so the toggle, Save Progress and Load
           stay reachable on a short or phone-sized viewport and the ad bar is never covered. */
        max-width: calc(100vw - 12px);
        max-height: calc(100vh - var(--save-widget-top, 6px) - 62px);
        max-height: calc(100dvh - var(--save-widget-top, 6px) - 62px);
        overflow-y: auto;
        overscroll-behavior: contain;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
      }
      #save-widget:not(.collapsed) { padding: 6px 10px 10px; border-radius: 10px; }
      /* A game's own stylesheet once pinned the collapsed widget to the bottom (bottom: 3px); with the
         widget anchored at the top that would stretch it down the screen, so bottom stays auto. */
      html body #save-widget[data-testid][data-testid] { bottom: auto; height: auto; }
      #save-widget .save-widget-header button { margin-top: 0; }
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
        position: relative;
      }
      /* Z-22: the pill and the Main menu button stay small (30px) on touch screens too; the
         44px touch target is kept as an invisible hit area, as the round info buttons do. */
      html #save-widget .save-widget-header .save-widget-toggle,
      html #save-widget .save-widget-header #noyvj-menu-button { min-height: 30px; position: relative; }
      html #save-widget .save-widget-header .save-widget-toggle::after,
      html #save-widget .save-widget-header #noyvj-menu-button::after { content: ""; position: absolute; inset: -7px -3px; }
      #save-widget .save-widget-toggle-icon { flex: 0 0 auto; }
      #save-widget .save-widget-saved-line { flex: 1 1 auto; min-width: 0; white-space: nowrap; font-size: 0.74rem; font-variant-numeric: tabular-nums; }
      #save-widget .save-widget-saved-line[data-state="failed"] { text-decoration: underline; text-decoration-style: wavy; text-underline-offset: 2px; color: #ffb4a8; }
      html[data-theme="light"] #save-widget .save-widget-saved-line[data-state="failed"] { color: #9a2a1a; }
      #save-widget .save-widget-warning { margin: 0.4rem 0 0; padding: 0.3rem 0.4rem; border: 1px solid currentColor; border-radius: 6px; font-size: 0.72rem; }
      /* The arrow is the actual "this collapses/expands" affordance --
         the label alone reads the same whether the panel is open or shut. */
      #save-widget .save-widget-toggle-arrow {
        display: inline-block;
        transition: none;
        font-size: 0.7rem;
        opacity: 0.85;
        flex: 0 0 auto;
      }
      #save-widget.collapsed .save-widget-toggle-arrow { transform: rotate(-90deg); }
      #save-widget.collapsed .save-widget-body { display: none; }
      #save-widget.collapsed { width: auto; overflow: visible; border-radius: 18px; padding: 2px 4px; }
      /* Collapsed, the Main menu button shrinks to its icon so the pill stays small. */
      #save-widget.collapsed .noyvj-menu-label { display: none; }
      /* Desktop boot: keep the shell's top bar out of the pill's corner. */
      html[data-layout="pc"] #pc-topbar { padding-right: var(--save-widget-reserve, 0px); }
      #save-widget .save-widget-restore-note { margin: 0.4rem 0 0; font-size: 0.72rem; opacity: 0.8; }
      #save-widget .save-widget-restore-note:empty { display: none; }
      #save-widget .save-widget-restore-list { list-style: none; margin: 0.3rem 0 0; padding: 0; display: grid; gap: 0.3rem; }
      #save-widget .save-widget-restore-item { display: grid; gap: 0.2rem; font-size: 0.72rem; padding: 0.3rem; border: 1px solid #2a3a4c; border-radius: 8px; }
      #save-widget .save-widget-restore-item-when { font-weight: 600; }
      #save-widget .save-widget-restore-item-summary { overflow-wrap: anywhere; opacity: 0.85; }
      #save-widget .save-widget-restore-item button { margin: 0; font-size: 0.72rem; padding: 0.3rem 0.35rem; }
      html[data-theme="light"] #save-widget .save-widget-restore-item { border-color: rgba(70, 95, 170, 0.3); }
      html[data-theme="light"] #save-widget .save-widget-restore-item button { background: linear-gradient(135deg, #dbe4fb, #c6d3f5); color: #1b2033; border: 1px solid rgba(70, 95, 170, 0.3); }
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
      <button type="button" class="save-widget-toggle" data-testid="save-widget-toggle"><span class="save-widget-toggle-icon" aria-hidden="true">&#128190;</span><span class="save-widget-saved-line" data-testid="save-widget-saved-line">Not saved yet</span><span class="save-widget-toggle-arrow" aria-hidden="true">&#9662;</span></button>
    </div>
    <div class="save-widget-body" data-testid="save-widget-body">
      <p class="save-widget-warning" role="status" data-testid="save-widget-warning" hidden>Warning: the last save did not go through. Press Save Progress to try again.</p>
      <button type="button" class="save-widget-save-button" data-testid="save-widget-save">Save Progress</button>
      <label class="save-widget-autosave-label"><input type="checkbox" class="save-widget-autosave-checkbox" data-testid="save-widget-autosave"> Autosave every 5 minutes</label>
      <p class="save-widget-code" data-testid="save-widget-code" hidden></p>
      <button type="button" class="save-widget-copy-button save-widget-link" data-testid="save-widget-copy" hidden>Copy code</button>
      <button type="button" class="save-widget-claim-button save-widget-link" data-testid="save-widget-claim" hidden>Claim this save to your account</button>
      <button type="button" class="save-widget-new-button save-widget-link" data-testid="save-widget-new" hidden>Start a new save (forget this code)</button>
      <div class="save-widget-slots" data-testid="save-widget-slots" hidden></div>
      <button type="button" class="save-widget-restore-toggle save-widget-link" data-testid="save-widget-restore-toggle" aria-expanded="false">Restore an earlier state</button>
      <div class="save-widget-restore" data-testid="save-widget-restore" hidden>
        <p class="save-widget-restore-note" data-testid="save-widget-restore-note"></p>
        <ul class="save-widget-restore-list" data-testid="save-widget-restore-list"></ul>
      </div>
      <input type="text" class="save-widget-load-input" data-testid="save-widget-load-input" placeholder="XXXX-XXXX" maxlength="9" autocomplete="off">
      <button type="button" class="save-widget-load-button" data-testid="save-widget-load">Load</button>
      <p class="save-widget-status" data-testid="save-widget-status"></p>
    </div>
  `;

  function mount() {
    document.body.appendChild(root);
  }
  // The labels written into the markup above, set again whenever the language changes.
  function relabelStatic() {
    const set = (selector, text) => { const el = root.querySelector(selector); if (el) el.textContent = text; };
    set(".save-widget-warning", tr("save.warning", "Warning: the last save did not go through. Press Save Progress to try again."));
    if (!root.querySelector(".save-widget-save-button").disabled) set(".save-widget-save-button", tr("save.saveButton", "Save Progress"));
    const autosaveLabel = root.querySelector(".save-widget-autosave-label");
    if (autosaveLabel && autosaveLabel.lastChild) autosaveLabel.lastChild.textContent = " " + tr("save.autosave", "Autosave every 5 minutes");
    set(".save-widget-copy-button", tr("save.copyCode", "Copy code"));
    set(".save-widget-claim-button", tr("save.claim", "Claim this save to your account"));
    set(".save-widget-new-button", tr("save.newSave", "Start a new save (forget this code)"));
    set(".save-widget-restore-toggle", tr("save.restoreToggle", "Restore an earlier state"));
    if (!root.querySelector(".save-widget-load-button").disabled) set(".save-widget-load-button", tr("save.load", "Load"));
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

  // Z-22: every page load starts collapsed, on every screen size (the pill is the whole widget
  // until the player opens it). aria-expanded + title say what the toggle will do.
  function syncToggleState() {
    const collapsed = root.classList.contains("collapsed");
    toggleButton.setAttribute("aria-expanded", String(!collapsed));
    toggleButton.title = collapsed ? tr("save.showOptions", "Show save/load options") : tr("save.hideOptions", "Hide save/load options");
    updatePlacement();
  }
  toggleButton.addEventListener("click", () => {
    root.classList.toggle("collapsed");
    syncToggleState();
  });
  root.classList.add("collapsed");

  // ---- Z-22: the live "Saved N min ago" line --------------------------------------------------
  const SAVED_AT_KEY = `savedat:${GAME_ID}`;
  const savedLineEl = root.querySelector(".save-widget-saved-line");
  const warningEl = root.querySelector(".save-widget-warning");
  let lastSaveAt = parseInt(lsGet(SAVED_AT_KEY), 10) || 0;
  let lastSaveFailed = false;

  function agoShort(ms) {
    const seconds = Math.max(0, (Date.now() - ms) / 1000);
    const now = tr("save.agoJustNow", "just now");
    if (seconds < 45) return { short: tr("save.pillJustNow", "just now"), long: now };
    if (seconds < 5400) {
      const n = Math.max(1, Math.round(seconds / 60));
      return { short: tr("save.pillMin", "{n} min ago", { n }), long: n === 1 ? tr("save.agoMinuteLong", "1 minute ago") : tr("save.agoMinutesLong", "{n} minutes ago", { n }) };
    }
    if (seconds < 129600) {
      const n = Math.round(seconds / 3600);
      return { short: tr("save.pillHour", "{n} h ago", { n }), long: n === 1 ? tr("save.agoHourLong", "1 hour ago") : tr("save.agoHoursLong", "{n} hours ago", { n }) };
    }
    const n = Math.round(seconds / 86400);
    return { short: tr("save.pillDay", "{n} d ago", { n }), long: n === 1 ? tr("save.agoDayLong", "1 day ago") : tr("save.agoDaysLong", "{n} days ago", { n }) };
  }

  // Plain words, never colour alone: the failure text replaces the time.
  function renderSavedLine() {
    let shortText;
    let longText;
    if (lastSaveFailed) {
      shortText = tr("save.pillFailed", "Save failed — try again");
      longText = lastSaveAt ? tr("save.failedLastSaved", "Save failed. Last saved {ago}", { ago: agoShort(lastSaveAt).long }) : tr("save.failed", "Save failed");
    } else if (!lastSaveAt) {
      shortText = tr("save.pillNotSaved", "Not saved yet");
      longText = tr("save.notSavedYet", "Not saved yet");
    } else {
      const ago = agoShort(lastSaveAt);
      shortText = tr("save.pillSaved", "Saved {ago}", { ago: ago.short });
      longText = tr("save.saved", "Saved {ago}", { ago: ago.long });
    }
    savedLineEl.textContent = shortText;
    savedLineEl.setAttribute("data-state", lastSaveFailed ? "failed" : lastSaveAt ? "saved" : "none");
    savedLineEl.title = longText;
    toggleButton.setAttribute("aria-label", tr("save.optionsAria", "Save and load options. {state}", { state: longText }));
    warningEl.hidden = !lastSaveFailed;
    updatePlacement();
  }
  function recordSaveSuccess() {
    lastSaveAt = Date.now();
    lastSaveFailed = false;
    lsSet(SAVED_AT_KEY, String(lastSaveAt));
    renderSavedLine();
  }
  // Z-7 / Z-17: after a SUCCESSFUL save only, tell the shared profile helper how many achievements
  // the saved state holds (shared/profile.js adds the visible-tab seconds itself and posts only for a
  // signed-in player) and tell the Report a problem dialog which save schema this state carries.
  // Never awaited, never throws: it must not delay or break a save.
  function afterSaveSuccess(state) {
    try {
      const earned = state && Array.isArray(state.achievements_earned) ? state.achievements_earned : null;
      if (window.NoyvjProfile && typeof window.NoyvjProfile.update === "function") {
        const info = { game: GAME_ID };
        if (earned) info.achievements = earned;
        window.NoyvjProfile.update(info);
      }
      if (state && state.schema_version != null && window.NoyvjReport && typeof window.NoyvjReport.configure === "function") {
        window.NoyvjReport.configure({ schemaVersion: state.schema_version });
      }
    } catch (err) { /* a profile or report helper problem never touches saving */ }
  }
  function recordSaveFailure() {
    lastSaveFailed = true;
    renderSavedLine();
  }
  function forgetSavedTime() {
    lastSaveAt = 0;
    lastSaveFailed = false;
    lsRemove(SAVED_AT_KEY);
    renderSavedLine();
  }
  setInterval(() => { if (!document.hidden) renderSavedLine(); }, 20000);

  // ---- Z-22: top-corner placement --------------------------------------------------------------
  // The pill sits at the top-right. Below any full-width bar fixed to the top (what's-new banner,
  // mobile HUD, seasonal strip, a top ad bar) it steps down so it never covers one; on the Desktop
  // boot it reserves its own corner in #pc-topbar (--save-widget-reserve, used by the rule below).
  let pillWidth = 0;
  let pillHeight = 0;
  let placing = false;
  // Small floating pills that games put in the top-right corner themselves (the Desktop boot's theme
  // toggle): the widget slides left of one instead of covering it.
  const CORNER_NEIGHBOURS = ["#theme-toggle-floating", "#story-toggle"];
  function visibleFixed(el) {
    const cs = getComputedStyle(el);
    return cs.position === "fixed" && cs.display !== "none" && cs.visibility !== "hidden";
  }
  function updatePlacement() {
    if (placing || !document.body || !root.isConnected) return;
    placing = true;
    try {
      let top = 6;
      const vw = window.innerWidth;
      for (const el of document.body.children) {
        if (el === root || el.id === "opening-screen") continue;
        if (!visibleFixed(el)) continue;
        const r = el.getBoundingClientRect();
        if (r.height < 8 || r.height > 160 || r.width < vw * 0.6 || r.top > 4 || r.bottom <= 0) continue;
        top = Math.max(top, Math.ceil(r.bottom) + 4);
      }
      root.style.setProperty("--save-widget-top", `${top}px`);
      if (root.classList.contains("collapsed")) {
        const box = root.getBoundingClientRect();
        pillWidth = Math.max(pillWidth, Math.ceil(box.width));
        pillHeight = Math.max(pillHeight, Math.ceil(box.height));
      }
      if (pillWidth) {
        let right = 6;
        for (let pass = 0; pass < 2; pass++) {
          for (const sel of CORNER_NEIGHBOURS) {
            const el = document.querySelector(sel);
            if (!el || !visibleFixed(el)) continue;
            const r = el.getBoundingClientRect();
            const left = vw - right - pillWidth;
            if (r.width && r.right > left && r.left < vw - right && r.top < top + pillHeight && r.bottom > top) right = Math.max(right, Math.ceil(vw - r.left + 6));
          }
        }
        root.style.setProperty("--save-widget-right", `${right}px`);
        // Desktop boot: the top bar stops short of the pill's left edge.
        const pc = window.NOYVJ_LAYOUT === "pc" || document.documentElement.getAttribute("data-layout") === "pc";
        const bar = pc && document.getElementById("pc-topbar");
        if (bar) {
          const reserve = Math.max(0, Math.ceil(bar.getBoundingClientRect().right - (vw - right - pillWidth - 8)));
          document.documentElement.style.setProperty("--save-widget-reserve", `${reserve}px`);
        }
      }
    } catch (e) { /* placement is cosmetic */ } finally { placing = false; }
  }
  window.addEventListener("resize", updatePlacement);
  setInterval(() => { if (!document.hidden) updatePlacement(); }, 1500);
  if (window.MutationObserver) {
    const start = () => new MutationObserver(updatePlacement).observe(document.body, { childList: true });
    if (document.body) start(); else document.addEventListener("DOMContentLoaded", start);
  }
  if (document.body) updatePlacement(); else document.addEventListener("DOMContentLoaded", updatePlacement);
  renderSavedLine();
  syncToggleState();

  // Z-13: a language file that arrives after the widget was built relabels what is already on screen.
  if (window.NoyvjI18n && window.NoyvjI18n.lang() !== "en") relabelStatic();
  document.addEventListener("noyvj-i18n-change", () => {
    relabelStatic();
    renderSavedLine();
    syncToggleState();
    if (!codeDisplay.hidden) { const remembered = lsGet(STORAGE_KEY); if (remembered) codeDisplay.textContent = tr("save.code", "Code: {code}", { code: remembered }); }
    if (slotMode() && Object.keys(slotRows).length) renderSlots();
  });

  // `owned` = the code came from this account's own slots, so there is nothing to claim.
  function showActiveCode(code, owned) {
    codeDisplay.textContent = tr("save.code", "Code: {code}", { code });
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
      applyLoad(loadState, mostRecent.save_data, "load");
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
    statusEl.textContent = message || tr("save.continued", "Continued your most recent save.");
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
      forgetSavedTime();
      return false;
    }
    return loadLatestFromAccount();
  }

  (async () => {
    const loaded = await tryAutoLoadFromAccount();
    if (slotMode()) refreshSlots(true);
    syncPendingSnapshots();
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
    forgetSavedTime();
    statusEl.textContent = tr("save.freshCode", "Next save starts a fresh code.");
  }

  newButton.addEventListener("click", () => {
    if (window.ConfirmDialog) {
      window.ConfirmDialog.ask({
        id: `${GAME_ID}-save-widget-forget-code`,
        message: tr("save.newSaveConfirm",
          "Start a new save? This forgets your current save code in this browser -- " +
          "your progress under that code isn't deleted from the server and can still " +
          "be loaded later by pasting the code back in, but you'll need to have saved " +
          "it somewhere first. This browser won't remember it anymore."),
        confirmLabel: tr("save.newSaveGo", "Start a new save"),
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
        statusEl.textContent = tr("save.copyFailed", "Couldn't copy — code is shown above.");
        return;
      }
    }
    statusEl.textContent = tr("save.copied", "Code copied!");
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
    if (seconds < 90) return tr("save.agoJustNow", "just now");
    if (seconds < 5400) return tr("save.agoMin", "{n} min ago", { n: Math.round(seconds / 60) });
    if (seconds < 129600) return tr("save.agoHour", "{n} h ago", { n: Math.round(seconds / 3600) });
    return tr("save.agoDay", "{n} d ago", { n: Math.round(seconds / 86400) });
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
          setFailure(tr("save.signInExpired", "Your sign-in has expired — sign in again from the hub."));
          return false;
        }
        if (!res.ok) throw new Error(`status ${res.status}`);
        raw = await res.json();
      }
      const saves = raw.filter((r) => r.game_id === GAME_ID && r.slot);
      slotRows = {};
      saves.forEach((r) => { slotRows[r.slot] = r; });
      slotsKnown = true;
      // The active slot's own timestamp tells "saved N min ago" for a returning player (never for
      // a fresh game: with no active slot nothing is claimed).
      const activeRow = activeSlot && slotRows[activeSlot];
      if (activeRow && !lastSaveFailed) {
        const t = parseTime(activeRow.updated_at || activeRow.created_at);
        if (t > lastSaveAt) { lastSaveAt = t; renderSavedLine(); }
      }
    } catch (err) {
      console.error(`${GAME_ID} save-widget: refreshing save slots failed`, err);
      if (!slotsKnown) setFailure(tr("save.savesUnreachable", "Couldn't reach your saves just now — try again."));
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
        ? `${n}${activeSlot === n ? " ●" : ""} ${row.slot_name || tr("save.slotName", "Save {n}", { n })} · ${timeAgo(row.updated_at || row.created_at)}`
        : `${n}${activeSlot === n ? " ●" : ""} ${tr("save.slotEmpty", "Empty")}`;
      line.appendChild(label);
      if (row) {
        const load = document.createElement("button");
        load.type = "button";
        load.setAttribute("data-testid", `save-widget-slot-${n}-load`);
        load.textContent = tr("save.load", "Load");
        load.addEventListener("click", () => slotLoad(n));
        line.appendChild(load);
      }
      const save = document.createElement("button");
      save.type = "button";
      save.setAttribute("data-testid", `save-widget-slot-${n}-save`);
      save.textContent = tr("save.saveHere", "Save here");
      save.addEventListener("click", async () => {
        // An explicit tap on a slot that holds something else (not the one this game
        // was loaded from or last saved to) asks first, so a mis-tap can't replace it.
        if (slotRows[n] && !(activeSlot === n && slotConfirmed)) {
          const go = await confirmOverwrite(n);
          if (!go) return;
        }
        statusEl.textContent = tr("save.saving", "Saving...");
        saveFailureNote = "";
        const ok = await slotSave(n);
        statusEl.textContent = ok ? tr("save.savedToSlot", "Saved to slot {n}!", { n }) : (saveFailureNote || tr("save.failedTryAgain", "Save failed — try again."));
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
        message: tr("save.overwriteConfirm", "Overwrite slot {n} ({name}, {ago}) with your current progress? The old save in that slot is replaced.",
          { n, name: (row && row.slot_name) || tr("save.slotName", "Save {n}", { n }), ago: timeAgo(row && (row.updated_at || row.created_at)) }),
        confirmLabel: tr("save.overwriteGo", "Overwrite slot {n}", { n }),
        allowSkip: false,
        onConfirm: () => resolve(true),
      });
    });
  }

  async function slotSave(n) {
    const state = readGameState();
    if (state === null) { setFailure(tr("save.stillLoading", "Still loading — try again in a moment.")); return false; }
    if (state === undefined) { setFailure(tr("save.notWiredSave", "This game hasn't wired up saving yet.")); return false; }
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
        setFailure(tr("save.signInExpired", "Your sign-in has expired — sign in again from the hub."));
        recordSaveFailure();
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
      recordSaveSuccess();
      afterSaveSuccess(state);
      return true;
    } catch (err) {
      console.error(`${GAME_ID} save-widget: slot save failed`, err);
      recordSaveFailure();
      return false;
    }
  }

  async function slotLoad(n) {
    if (!slotRows[n]) return;
    // Re-read the rows first: another tab or device may have saved here since this
    // panel last looked. If the refresh fails, fall back to what is on screen.
    await refreshSlots();
    const row = slotRows[n];
    if (!row) { statusEl.textContent = tr("save.slotEmptyNow", "Slot {n} is empty now.", { n }); return; }
    if (!window.pyodide) { statusEl.textContent = tr("save.stillLoading", "Still loading — try again in a moment."); return; }
    const loadState = window.pyodide.globals.get("load_state");
    if (!loadState) { statusEl.textContent = tr("save.notWiredLoad", "This game hasn't wired up loading yet."); return; }
    try {
      applyLoad(loadState, row.save_data, "load");
      setActiveSlot(n, true);
      try { lsSet(STORAGE_KEY, row.save_code); } catch (e) { /* convenience only */ }
      showActiveCode(row.save_code, true);
      renderSlots();
      statusEl.textContent = tr("save.loadedSlot", "Loaded slot {n}!", { n });
    } catch (err) {
      console.error(`${GAME_ID} save-widget: slot load failed`, err);
      statusEl.textContent = tr("save.loadFailed", "Load failed — try again.");
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
      heading.textContent = tr("save.chooserHeading", "Your account already has saves for this game. Where should this one go?");
      card.appendChild(heading);
      const done = (value) => { document.removeEventListener("keydown", onKey, true); overlay.remove(); resolve(value); };
      const onKey = (e) => { if (e.key === "Escape") { e.stopPropagation(); done(null); } };
      document.addEventListener("keydown", onKey, true);
      for (let n = 1; n <= SLOT_COUNT; n++) {
        const row = slotRows[n];
        const button = document.createElement("button");
        button.type = "button";
        button.setAttribute("data-testid", `save-widget-chooser-slot-${n}`);
        button.textContent = row
          ? tr("save.chooserOverwrite", "Overwrite slot {n}: {name} ({ago})", { n, name: row.slot_name || tr("save.slotName", "Save {n}", { n }), ago: timeAgo(row.updated_at || row.created_at) })
          : tr("save.chooserEmpty", "Save to empty slot {n}", { n });
        button.addEventListener("click", () => done(n));
        card.appendChild(button);
      }
      const cancel = document.createElement("button");
      cancel.type = "button";
      cancel.setAttribute("data-testid", "save-widget-chooser-cancel");
      cancel.textContent = tr("save.cancel", "Cancel");
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
    if (!fresh && !slotsKnown) { recordSaveFailure(); return false; }
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

  // ---- Z-10: the time machine -------------------------------------------------------------------
  // Snapshots of the game state, kept per game and slot (the newest SNAP_COUNT of each) in
  // localStorage and, signed in, on the backend. Taken just before a Load / New Game / restore
  // overwrites the current state, and on autosave at most once per SNAP_AUTO_GAP_MS. An empty or
  // never-played (boot default) state is never snapshotted. Every storage and network step is
  // allowed to fail without the widget noticing: a snapshot is a convenience, not a save.
  const SNAP_COUNT = 5;
  const SNAP_KEY = `snapshots:${GAME_ID}`;
  const SNAP_AUTO_KEY = `snapshot-auto-at:${GAME_ID}`;
  const SNAP_ENTRY_MAX_BYTES = 150000;    // larger states are not kept in localStorage (quota guard)
  const SNAP_LOCAL_MAX_BYTES = 450000;    // this game's local snapshots together
  const SNAP_REMOTE_MAX_BYTES = 900000;   // the backend refuses above 1 MB
  const SNAP_KEEPALIVE_MAX_BYTES = 60000; // a keepalive request may carry about 64 KB
  const SNAP_AUTO_GAP_MS = 10 * 60 * 1000;
  const SNAP_LIST_MAX = 15;

  function stateJson(state) { return JSON.stringify(state, undefinedToNull); }
  function kbText(n) { return `${(n / 1024).toFixed(n < 10240 ? 1 : 0)} KB`; }

  // The state the game booted with: a snapshot equal to it is "default" and never kept. Captured the
  // first time the state is readable and always before the widget itself loads anything over it.
  let baselineJson = null;
  let widgetLoaded = false;
  function ensureBaseline() {
    if (baselineJson !== null || widgetLoaded) return;
    try {
      const state = readGameState();
      if (state && typeof state === "object") baselineJson = stateJson(state);
    } catch (err) { /* no baseline */ }
  }
  waitForLoadState().then(ensureBaseline, () => {});
  function isMeaningful(state) {
    if (!state || typeof state !== "object" || Array.isArray(state) || !Object.keys(state).length) return false;
    return baselineJson === null || stateJson(state) !== baselineJson;
  }
  // Every widget-driven load goes through here: baseline first, then (unless it is the autoload
  // at page start, which finds only the default state) a snapshot of what is about to be replaced.
  function applyLoad(loadState, data, snapshotReason) {
    ensureBaseline();
    if (snapshotReason) takeSnapshot(snapshotReason);
    loadState(window.pyodide.toPy(data));
    widgetLoaded = true;
  }

  function headlineOf(fields) {
    let f = fields;
    if (typeof f === "string") { try { f = JSON.parse(f); } catch (err) { return ""; } }
    if (!f || typeof f !== "object") return "";
    const bits = [];
    if (f.score !== undefined && f.score !== null && f.score !== "") {
      const score = typeof f.score === "number" ? f.score.toLocaleString("en-US", { maximumFractionDigits: 2 }) : String(f.score);
      bits.push(f.unit ? `${score} ${f.unit}` : score);
    }
    (Array.isArray(f.stats) ? f.stats : []).slice(0, 2).forEach((p) => {
      if (typeof p === "string" || typeof p === "number") bits.push(String(p));
      else if (p && typeof p.n === "number") bits.push(`${p.n} ${p.n === 1 ? p.one : (p.many || p.one)}`);
    });
    return bits.join(", ").replace(/\s+/g, " ").trim().slice(0, 120);
  }
  // One line for the list: the game's own copy-result headline if the page exposes one, else "N keys, X KB".
  function summarize(state, jsonLength) {
    const globals = window.pyodide && window.pyodide.globals;
    for (const name of ["share_result", "copy_result_fields"]) {
      try {
        const fn = globals && globals.get(name);
        if (!fn) continue;
        let value = fn();
        if (value && typeof value.toJs === "function") {
          const proxy = value;
          value = proxy.toJs({ dict_converter: Object.fromEntries });
          if (typeof proxy.destroy === "function") proxy.destroy();
        }
        const headline = headlineOf(value);
        if (headline) return headline;
      } catch (err) { /* fall back to the generic line */ }
    }
    const keys = Object.keys(state).length;
    return `${keys} ${keys === 1 ? "key" : "keys"}, ${kbText(jsonLength)}`;
  }

  function readLocalSnaps() {
    try {
      const list = JSON.parse(lsGet(SNAP_KEY) || "[]");
      return (Array.isArray(list) ? list : [])
        .filter((e) => e && typeof e.id === "string" && typeof e.json === "string" && typeof e.t === "number")
        .sort((a, b) => b.t - a.t);
    } catch (err) { return []; }
  }
  // Newest first in, per slot trimmed to SNAP_COUNT, then trimmed by size from the oldest end.
  function writeLocalSnaps(list) {
    const perSlot = {};
    let kept = list.filter((e) => (perSlot[e.slot] = (perSlot[e.slot] || 0) + 1) <= SNAP_COUNT);
    const total = () => kept.reduce((n, e) => n + e.json.length, 0);
    while (kept.length > 1 && total() > SNAP_LOCAL_MAX_BYTES) kept = kept.slice(0, -1);
    for (let attempt = 0; attempt < 6; attempt++) {
      try { localStorage.setItem(SNAP_KEY, JSON.stringify(kept)); return; }
      catch (err) {
        if (!kept.length) return;            // storage blocked or full: nothing to keep
        kept = kept.slice(0, Math.floor(kept.length / 2));   // quota: drop the older half and retry
      }
    }
  }

  // Uploads still on their way, so the restore list can wait for them instead of listing a snapshot
  // twice (once local without its backend id, once from the server).
  const uploadsInFlight = new Set();
  function trackUpload(promise) {
    uploadsInFlight.add(promise);
    const done = () => uploadsInFlight.delete(promise);
    promise.then(done, done);
    return promise;
  }
  async function uploadSnapshot(entry, keepalive) {
    if (!slotMode()) return false;
    try {
      const body = `{"game_id":${JSON.stringify(GAME_ID)},"slot":${entry.slot},"summary":${JSON.stringify(entry.summary || "")},"save_data":${entry.json}}`;
      const res = await fetch(`${API_BASE}/users/me/snapshots`, {
        method: "POST",
        headers: Object.assign({ "Content-Type": "application/json" }, hubAuthHeaders()),
        body,
        keepalive: Boolean(keepalive) && body.length <= SNAP_KEEPALIVE_MAX_BYTES,
      });
      if (!res.ok) {
        // A refusal that retrying cannot change (too large, bad shape) is remembered so it is not resent.
        if (res.status >= 400 && res.status < 500 && res.status !== 401 && res.status !== 429) markLocal(entry.id, { dead: true });
        return false;
      }
      const saved = await res.json();
      markLocal(entry.id, { rid: saved.id });
      entry.rid = saved.id;
      return true;
    } catch (err) { return false; }   // offline: the start-up sweep tries again next visit
  }
  function markLocal(id, fields) {
    const list = readLocalSnaps();
    const hit = list.find((e) => e.id === id);
    if (hit) { Object.assign(hit, fields); writeLocalSnaps(list); }
  }
  async function syncPendingSnapshots() {
    if (!slotMode()) return;
    const pending = readLocalSnaps().filter((e) => !e.rid && !e.dead && e.json.length <= SNAP_REMOTE_MAX_BYTES).reverse().slice(-SNAP_COUNT);
    for (const entry of pending) { if (!(await trackUpload(uploadSnapshot(entry, false)))) break; }
  }

  // Returns the new local entry, or null when nothing was kept (empty/default state, unchanged since
  // the last snapshot of that slot, state unreadable). Never throws.
  function takeSnapshot(reason, opts) {
    try {
      const state = readGameState();
      if (!state || !isMeaningful(state)) return null;
      const json = stateJson(state);
      const slot = slotMode() ? (activeSlot || 0) : 0;
      const list = readLocalSnaps();
      const newestHere = list.find((e) => e.slot === slot);
      if (newestHere && newestHere.json === json) return null;
      const entry = {
        id: `s${Date.now().toString(36)}${Math.random().toString(36).slice(2, 7)}`, t: Date.now(), slot,
        summary: summarize(state, json.length), size: json.length, reason: reason || "", json, rid: null,
      };
      if (json.length <= SNAP_ENTRY_MAX_BYTES) {
        list.unshift(entry);
        writeLocalSnaps(list);
      }
      if (slotMode() && json.length <= SNAP_REMOTE_MAX_BYTES) trackUpload(uploadSnapshot(entry, Boolean(opts && opts.keepalive)));
      return entry;
    } catch (err) {
      console.warn(`${GAME_ID} save-widget: snapshot skipped`, err);
      return null;
    }
  }
  // Autosave's snapshot, at most once per SNAP_AUTO_GAP_MS (remembered across reloads).
  function maybeAutoSnapshot() {
    const last = parseInt(lsGet(SNAP_AUTO_KEY), 10) || 0;
    if (Date.now() - last < SNAP_AUTO_GAP_MS) return null;
    const entry = takeSnapshot("autosave");
    if (entry) lsSet(SNAP_AUTO_KEY, String(Date.now()));
    return entry;
  }

  // ---- the "Restore an earlier state" list ----
  const restoreToggle = root.querySelector(".save-widget-restore-toggle");
  const restoreBox = root.querySelector(".save-widget-restore");
  const restoreNote = root.querySelector(".save-widget-restore-note");
  const restoreList = root.querySelector(".save-widget-restore-list");
  let restoreRender = 0;

  function whenText(t) {
    const stamp = new Date(t).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
    return `${stamp} (${agoShort(t).short})`;
  }

  async function renderRestoreList() {
    const mine = ++restoreRender;
    restoreNote.textContent = tr("save.loadingDots", "Loading…");
    restoreList.innerHTML = "";
    let items = readLocalSnaps().map((e) => ({ t: e.t, slot: e.slot, summary: e.summary, size: e.size, local: e, rid: e.rid }));
    let remoteFailed = false;
    if (slotMode()) {
      if (uploadsInFlight.size) await Promise.race([Promise.allSettled([...uploadsInFlight]), sleep(4000)]);
      items = readLocalSnaps().map((e) => ({ t: e.t, slot: e.slot, summary: e.summary, size: e.size, local: e, rid: e.rid }));
      try {
        const res = await fetchWithRetry(`${API_BASE}/users/me/snapshots?game_id=${encodeURIComponent(GAME_ID)}`, { headers: hubAuthHeaders(), cache: "no-store" });
        if (!res.ok) throw new Error(`status ${res.status}`);
        (await res.json()).forEach((r) => {
          if (items.some((i) => i.rid === r.id)) return;
          items.push({ t: parseTime(r.created_at), slot: r.slot, summary: r.summary, size: r.size, rid: r.id });
        });
      } catch (err) { remoteFailed = true; }
    }
    if (mine !== restoreRender) return;   // a newer render superseded this one
    items.sort((a, b) => b.t - a.t);
    items = items.slice(0, SNAP_LIST_MAX);
    restoreNote.textContent = items.length
      ? (remoteFailed ? tr("save.snapshotsUnreachable", "Couldn't reach your account's snapshots, so this lists the ones in this browser.") : "")
      : tr("save.noSnapshots", "No earlier states yet. One is kept before a load or a new game, and while autosave is on.");
    items.forEach((item, i) => {
      const li = document.createElement("li");
      li.className = "save-widget-restore-item";
      li.setAttribute("data-testid", `save-widget-restore-item-${i + 1}`);
      const when = document.createElement("span");
      when.className = "save-widget-restore-item-when";
      when.textContent = `${whenText(item.t)}${item.slot ? ` · ${tr("save.slotWord", "slot {n}", { n: item.slot })}` : ""}`;
      const summary = document.createElement("span");
      summary.className = "save-widget-restore-item-summary";
      summary.textContent = item.summary || tr("save.earlierState", "Earlier state");
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = tr("save.restore", "Restore");
      button.setAttribute("data-testid", `save-widget-restore-item-${i + 1}-restore`);
      button.addEventListener("click", () => askRestore(item));
      li.append(when, summary, button);
      restoreList.appendChild(li);
    });
  }

  restoreToggle.addEventListener("click", () => {
    const open = restoreBox.hidden;
    restoreBox.hidden = !open;
    restoreToggle.setAttribute("aria-expanded", String(open));
    if (open) renderRestoreList();
  });

  function askRestore(item) {
    const message = tr("save.restoreConfirm",
      "Restore the state from {when} ({summary})? Your current progress is snapshotted first, so you can undo this from the same list.",
      { when: whenText(item.t), summary: item.summary || tr("save.earlierStateLower", "earlier state") });
    if (window.ConfirmDialog) {
      window.ConfirmDialog.ask({
        id: `${GAME_ID}-save-widget-restore`, message, confirmLabel: tr("save.restore", "Restore"), allowSkip: false,
        onConfirm: () => doRestore(item),
      });
    } else {
      doRestore(item);
    }
  }

  async function doRestore(item) {
    if (!window.pyodide) { statusEl.textContent = tr("save.stillLoading", "Still loading — try again in a moment."); return; }
    const loadState = window.pyodide.globals.get("load_state");
    if (!loadState) { statusEl.textContent = tr("save.notWiredLoad", "This game hasn't wired up loading yet."); return; }
    let data;
    try {
      if (item.local) data = JSON.parse(item.local.json);
      else {
        const res = await fetchWithRetry(`${API_BASE}/users/me/snapshots/${encodeURIComponent(item.rid)}`, { headers: hubAuthHeaders(), cache: "no-store" });
        if (!res.ok) throw new Error(`status ${res.status}`);
        data = (await res.json()).save_data;
      }
    } catch (err) {
      console.error(`${GAME_ID} save-widget: fetching a snapshot failed`, err);
      statusEl.textContent = tr("save.snapshotFetchFailed", "Couldn't fetch that snapshot — try again.");
      return;
    }
    try {
      applyLoad(loadState, data, "before-restore");
      statusEl.textContent = tr("save.restored", "Restored. Your previous state is first in the list, so you can undo this.");
    } catch (err) {
      console.error(`${GAME_ID} save-widget: restore failed`, err);
      statusEl.textContent = tr("save.restoreFailed", "Restore failed — try again.");
    }
    if (!restoreBox.hidden) renderRestoreList();
  }

  // The ONE code path that talks to the save endpoint, shared by the Save button and the opt-in
  // autosave timer so they cannot drift apart. Returns true/false and leaves all user-facing
  // feedback to the caller (a disabled "Saving..." button vs. a silent timer tick).
  async function doSave(onRetrying, silent) {
    saveFailureNote = "";
    if (slotMode()) return doSlotSave(Boolean(silent));
    const state = readGameState();
    if (state === null) {
      setFailure(tr("save.stillLoading", "Still loading — try again in a moment."));
      return false;
    }
    if (state === undefined) {
      setFailure(tr("save.notWiredSave", "This game hasn't wired up saving yet."));
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
      recordSaveSuccess();
      afterSaveSuccess(state);
      return true;
    } catch (err) {
      console.error(`${GAME_ID} save-widget: save failed`, err);
      recordSaveFailure();
      return false;
    }
  }

  saveButton.addEventListener("click", async () => {
    saveButton.disabled = true;
    saveButton.textContent = tr("save.saving", "Saving...");
    const ok = await doSave(() => (statusEl.textContent = tr("save.savingRetry", "Saving... (retrying)")));
    statusEl.textContent = ok === null ? "" : ok ? tr("save.savedAt", "Saved at {time}", { time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) }) : (saveFailureNote || tr("save.failedTryAgain", "Save failed — try again."));
    saveButton.disabled = false;
    saveButton.textContent = tr("save.saveButton", "Save Progress");
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
    maybeAutoSnapshot();
    const ok = await doSave(undefined, true);
    if (!ok) return;
    const autosavedText = tr("save.autosaved", "Autosaved");
    statusEl.textContent = autosavedText;
    setTimeout(() => {
      if (statusEl.textContent === autosavedText) statusEl.textContent = previousStatus;
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
      statusEl.textContent = tr("save.stillLoading", "Still loading — try again in a moment.");
      return;
    }
    const loadState = window.pyodide.globals.get("load_state");
    if (!loadState) {
      statusEl.textContent = tr("save.notWiredLoad", "This game hasn't wired up loading yet.");
      return;
    }
    const code = loadInput.value.trim().toUpperCase();
    if (!code) {
      statusEl.textContent = tr("save.enterCode", "Enter a save code first.");
      return;
    }
    loadButton.disabled = true;
    loadButton.textContent = tr("save.loading", "Loading...");
    try {
      const res = await fetchWithRetry(`${API_BASE}/saves/${code}`, undefined, () => (
        statusEl.textContent = tr("save.loadingRetry", "Loading... (retrying)")
      ));
      if (!res.ok) throw new Error(`status ${res.status}`);
      const body = await res.json();
      applyLoad(loadState, body.save_data, "load");
      lsSet(STORAGE_KEY, body.save_code);
      showActiveCode(body.save_code);
      loadInput.value = "";
      statusEl.textContent = tr("save.loaded", "Loaded!");
    } catch (err) {
      console.error(`${GAME_ID} save-widget: load failed for code ${code}`, err);
      statusEl.textContent = navigator.onLine === false
        ? tr("save.loadOffline", "Load failed — you appear to be offline.")
        : tr("save.loadBadCode", "Load failed — check the code (format XXXX-XXXX) and try again.");
    } finally {
      loadButton.disabled = false;
      loadButton.textContent = tr("save.load", "Load");
    }
  });

  claimButton.addEventListener("click", async () => {
    const code = lsGet(STORAGE_KEY);
    if (!code) return;
    claimButton.disabled = true;
    claimButton.textContent = tr("save.claiming", "Claiming...");
    try {
      const res = await fetchWithRetry(
        `${API_BASE}/saves/${code}/claim`,
        { method: "POST", headers: hubAuthHeaders() },
        () => (statusEl.textContent = tr("save.claimingRetry", "Claiming... (retrying)"))
      );
      if (res.status === 409) {
        // Either every slot for this game is taken, or the code is another account's.
        let detail = "";
        try { detail = (await res.json()).detail || ""; } catch (e) { /* no body */ }
        statusEl.textContent = /slots/i.test(detail)
          ? tr("save.slotsFull", "All 3 save slots are full — use \"Save here\" on a slot to replace one instead.")
          : tr("save.otherAccount", "That save already belongs to another account.");
        claimButton.disabled = false;
        claimButton.textContent = tr("save.claim", "Claim this save to your account");
        return;
      }
      if (!res.ok) throw new Error(`status ${res.status}`);
      let claimed = null;
      try { claimed = await res.json(); } catch (e) { /* the claim itself worked */ }
      claimButton.hidden = true;
      claimButton.disabled = false;
      claimButton.textContent = tr("save.claim", "Claim this save to your account");
      if (claimed && claimed.slot) {
        // The claimed save took a slot; that is now the one being played.
        setActiveSlot(claimed.slot, true);
        await refreshSlots();
        statusEl.textContent = tr("save.claimedSlot", "Save claimed to your account (slot {n})!", { n: claimed.slot });
      } else {
        statusEl.textContent = tr("save.claimed", "Save claimed to your account!");
      }
    } catch (err) {
      console.error(`${GAME_ID} save-widget: claim failed for code ${code}`, err);
      statusEl.textContent = tr("save.claimFailed", "Claim failed — try again.");
      claimButton.disabled = false;
      claimButton.textContent = tr("save.claim", "Claim this save to your account");
    }
  });

  // Small public API for the opening screen's "Main menu" re-entry (UX-8).
  window.NoyvjSaveWidget = {
    // Z-10: snapshot the current state now (the opening screen calls this before New Game).
    // Resolves nothing and never throws; true when a snapshot was kept.
    snapshotNow(reason) { return Boolean(takeSnapshot(reason || "manual", { keepalive: true })); },
    // This browser's snapshots for this game, newest first (read-only copy).
    localSnapshots() { return readLocalSnaps().map(({ json, ...rest }) => rest); },
    // Loads the account's latest save (signed in) or the remembered save code
    // (anonymous). Resolves true if something was loaded.
    async loadLatest() {
      if (slotMode()) {
        const ok = await loadLatestFromAccount(tr("save.loadedLatest", "Loaded your latest save."));
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
