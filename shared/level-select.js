/*
 * Shared level select (planning/TODO.md W-1, from your Round 3 answer: "a
 * level select where every 5 levels is either a game mode or a new mechanic").
 * Used first by Canopy (GB-13, GB-15, GB-16). Full guide with the data shape,
 * keyboard map and adoption steps: planning/SHARED-COMPONENTS.md.
 *
 * Easiest adoption (unchanged since the first version) is one include per game:
 *   <button id="levels-open-button" type="button">Levels</button>
 *   <script src="../../shared/level-select.js" data-game-id="canopy"
 *           data-levels="levels.json" data-open="#levels-open-button"></script>
 *
 * levels.json:
 *   { "title": "Canopy levels",
 *     "levels": [ { "id": "wren_hollow", "title": "Wren Hollow",
 *                   "kind": "level",            // "level" | "mode" | "mechanic"
 *                   "blurb": "The standard forest.",
 *                   "requires": [],             // ids that must be completed first
 *                   "requires_count": 0,        // OR: this many OTHER levels completed
 *                   "unlock_text": "",          // optional wording for the lock reason
 *                   "better": "higher",         // "higher" | "lower": which result is best
 *                   "unit": "points"            // optional unit shown after a numeric best
 *                 }, ... ] }
 * Levels are shown in order, in rows of five; by convention every fifth entry
 * (5, 10, 15 ...) is a "mode" (a different way to play) or a "mechanic" (a rule
 * the base game does not have): `mode: true` is shorthand for kind "mode", and
 * NoyvjLevels.logic.audit(levels) lists any fifth entry that is neither.
 *
 * Games talk to it through window.NoyvjLevels:
 *   complete(id, result?)  mark a level completed; `result` is a number, a string,
 *                          or { value, text } and replaces the stored best only if
 *                          it is better ("better" on the level)
 *   isDone(id) / done() / best(id)   read progress
 *   open() / close() / refresh()
 *   configure({ state, onChange, onStart, canPlay })
 *       state    { done: [ids], best: { id: { value, text } } } loaded from the game's
 *                own save (applied now, or when the file arrives)
 *       onChange(state) called with a fresh copy after every change; once supplied,
 *                this component stores NOTHING itself (no localStorage)
 *       onStart(id, level) called when Play is pressed on an unlocked level
 *       canPlay(level) optional extra gate: true, false, or a reason string
 *   getState() / setState(state) / ready() / levels()
 *   create(options)        an independent instance (no script tag needed):
 *       { game, title, levels, state, onChange, onStart, canPlay, trigger }
 * and it still calls window.NoyvjLevelStart(levelId) (for Python: assign a proxy)
 * as before. WITHOUT configure({ onChange }) progress falls back to localStorage
 * (`levels:<game>`, done ids only), exactly as the first version did. Text is
 * written with textContent only, and a missing or malformed levels.json leaves
 * the game unchanged.
 *
 * Accessibility: a modal dialog (focus moves in on open, Tab stays inside,
 * Escape closes and focus returns to the opener); the levels are an ordered list
 * with ONE tab stop (roving focus, arrow keys move by card, Home/End jump) and
 * every locked card stays focusable so a screen reader can read why it is locked;
 * state is a glyph plus a word plus a border style (solid thick = completed,
 * solid = ready, dashed = locked), never colour alone; modes and mechanics get a
 * double border and a tag; transitions are off under prefers-reduced-motion and
 * data-reduced-motion="true"; colours are tokens that follow html[data-theme].
 */
(function (root) {
  "use strict";

  const KINDS = { level: "Level", mode: "Game mode", mechanic: "New mechanic" };
  const KIND_GLYPH = { level: "", mode: "★ ", mechanic: "✦ " };
  const COLUMNS = 5;
  let instanceCounter = 0;

  // ---- pure logic ---------------------------------------------------------

  function normaliseLevels(list) {
    const seen = new Set();
    const out = [];
    (Array.isArray(list) ? list : []).forEach((l) => {
      if (!l || typeof l.id !== "string" || typeof l.title !== "string" || seen.has(l.id)) return;
      seen.add(l.id);
      const kind = l.kind in KINDS ? l.kind : l.mode === true ? "mode" : "level";
      out.push(Object.assign({}, l, { kind }));
    });
    return out;
  }

  function emptyState() { return { done: [], best: {} }; }

  function sanitizeState(levels, raw) {
    const known = new Set(levels.map((l) => l.id));
    const state = emptyState();
    if (Array.isArray(raw)) raw = { done: raw };   // the first version stored a bare id list
    if (!raw || typeof raw !== "object") return state;
    (Array.isArray(raw.done) ? raw.done : []).forEach((id) => {
      if (typeof id === "string" && known.has(id) && !state.done.includes(id)) state.done.push(id);
    });
    const best = raw.best && typeof raw.best === "object" && !Array.isArray(raw.best) ? raw.best : {};
    Object.keys(best).forEach((id) => {
      if (!known.has(id) || !state.done.includes(id)) return;
      const b = best[id];
      if (!b || typeof b !== "object") return;
      const entry = {};
      if (typeof b.value === "number" && Number.isFinite(b.value)) entry.value = b.value;
      if (typeof b.text === "string" && b.text.trim()) entry.text = b.text.trim().slice(0, 60);
      if (Object.keys(entry).length) state.best[id] = entry;
    });
    return state;
  }

  function cloneState(state) {
    return { done: state.done.slice(), best: JSON.parse(JSON.stringify(state.best)) };
  }

  function titleOf(levels, id) { const l = levels.find((x) => x.id === id); return l ? l.title : id; }

  // "" when the level can be played, otherwise the reason it cannot.
  function lockReason(levels, state, level) {
    const missing = (level.requires || []).filter((id) => !state.done.includes(id));
    if (missing.length) {
      return level.unlock_text || "Complete " + missing.map((id) => titleOf(levels, id)).join(" and ") + " first";
    }
    const need = Number.isInteger(level.requires_count) ? level.requires_count : 0;
    const have = state.done.filter((id) => id !== level.id).length;
    if (need > have) return level.unlock_text || "Complete " + (need - have) + " more level" + (need - have === 1 ? "" : "s") + " first";
    return "";
  }
  function isUnlocked(levels, state, level) { return lockReason(levels, state, level) === ""; }

  function normaliseResult(level, result) {
    if (typeof result === "number" && Number.isFinite(result)) result = { value: result };
    else if (typeof result === "string") result = { text: result };
    if (!result || typeof result !== "object") return null;
    const out = {};
    if (typeof result.value === "number" && Number.isFinite(result.value)) out.value = result.value;
    if (typeof result.text === "string" && result.text.trim()) out.text = result.text.trim().slice(0, 60);
    if (!("text" in out) && "value" in out) out.text = String(out.value) + (level.unit ? " " + level.unit : "");
    return Object.keys(out).length ? out : null;
  }

  function isBetter(level, candidate, current) {
    if (!current) return true;
    if (!("value" in candidate) || !("value" in current)) return false;   // text-only results never replace a best
    return level.better === "lower" ? candidate.value < current.value : candidate.value > current.value;
  }

  // Returns { state, changed, improved } without touching the input.
  function recordResult(levels, state, id, result) {
    const level = levels.find((l) => l.id === id);
    const next = cloneState(state);
    if (!level) return { state: next, changed: false, improved: false };
    let changed = false;
    let improved = false;
    if (!next.done.includes(id)) { next.done.push(id); changed = true; }
    const candidate = normaliseResult(level, result);
    if (candidate && isBetter(level, candidate, next.best[id])) {
      improved = Boolean(next.best[id]);
      next.best[id] = candidate;
      changed = true;
    }
    return { state: next, changed, improved };
  }

  function progress(levels, state) {
    return { done: levels.filter((l) => state.done.includes(l.id)).length, total: levels.length };
  }

  // The first level that is unlocked and not yet completed (what to focus on open).
  function nextUp(levels, state) {
    return levels.find((l) => !state.done.includes(l.id) && isUnlocked(levels, state, l)) || null;
  }

  // Every fifth level should be a mode or a mechanic; list the ones that are not.
  function audit(levels) {
    const warnings = [];
    levels.forEach((l, i) => {
      if ((i + 1) % COLUMNS === 0 && l.kind === "level") warnings.push("level " + (i + 1) + " (" + l.id + ") should be a mode or a mechanic");
    });
    const ids = new Set(levels.map((l) => l.id));
    levels.forEach((l) => (l.requires || []).forEach((r) => { if (!ids.has(r)) warnings.push(l.id + " requires unknown level " + r); }));
    return warnings;
  }

  const logic = { normaliseLevels, sanitizeState, lockReason, isUnlocked, recordResult, progress, nextUp, audit, isBetter, emptyState };

  // ---- styles (injected once) ---------------------------------------------

  function ensureStyles() {
    if (document.getElementById("noyvj-level-select-styles")) return;
    const lightTokens =
      "--lv-bg: #f7f8fc; --lv-fg: #1b2033; --lv-muted: #4a5275; --lv-border: rgba(60,85,160,0.5); --lv-focus: #8a5a00; --lv-accent: #1f6b3a; --lv-on-accent: #ffffff; --lv-done-bg: rgba(60,150,90,0.12); --lv-scrim: rgba(20,25,50,0.5);";
    const style = document.createElement("style");
    style.id = "noyvj-level-select-styles";
    style.textContent =
      ".level-select { --lv-bg: var(--level-bg, #1c2033); --lv-fg: var(--level-fg, #eaeaf0); --lv-muted: #aab0c8; --lv-border: rgba(140,160,255,0.45); --lv-focus: #ffd866; --lv-accent: #9fe0ab; --lv-on-accent: #0e1a12; --lv-done-bg: rgba(110,190,130,0.16); --lv-scrim: rgba(0,0,0,0.6);" +
      " position: fixed; inset: 0; z-index: 900; display: flex; align-items: center; justify-content: center; background: var(--lv-scrim); font-size: 1rem; }" +
      "html[data-theme=\"light\"] .level-select { " + lightTokens + " }" +
      "@media (prefers-color-scheme: light) { :root:not([data-theme]) .level-select { " + lightTokens + " } }" +
      ".level-select[hidden] { display: none !important; }" +
      ".level-select .level-select-panel { box-sizing: border-box; max-width: 1000px; width: calc(100% - 1.5rem); max-height: 90vh; max-height: 90dvh; overflow: auto; padding: 1rem 1.1rem; border-radius: 12px; background: var(--lv-bg); color: var(--lv-fg); border: 1px solid var(--lv-border); text-align: left; }" +
      ".level-select .level-head { display: flex; flex-wrap: wrap; align-items: center; gap: 0.4rem 1rem; }" +
      ".level-select .level-head h2 { margin: 0; font-size: 1.2rem; flex: 1 1 auto; }" +
      ".level-select .level-progress { margin: 0; font-size: 0.85rem; color: var(--lv-muted); font-weight: 600; }" +
      ".level-select .level-help { margin: 0.4rem 0 0; font-size: 0.78rem; color: var(--lv-muted); }" +
      ".level-select .level-grid { list-style: none; padding: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 0.6rem; margin: 0.8rem 0; }" +
      "@media (min-width: 900px) { .level-select .level-grid { grid-template-columns: repeat(5, minmax(0, 1fr)); } }" +
      ".level-select .level-card { display: flex; flex-direction: column; gap: 0.25rem; padding: 0.6rem; border: 2px solid var(--lv-border); border-radius: 8px; font-size: 0.85rem; background: transparent; }" +
      ".level-select .level-card--done { border-width: 3px; background: var(--lv-done-bg); }" +
      ".level-select .level-card--locked { border-style: dashed; }" +
      ".level-select .level-card--mode, .level-select .level-card--mechanic { border-style: double; border-width: 5px; }" +
      ".level-select .level-card--locked.level-card--mode, .level-select .level-card--locked.level-card--mechanic { border-style: dashed; border-width: 4px; }" +
      ".level-select .level-card strong { font-size: 0.95rem; }" +
      ".level-select .level-kind { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.04em; color: var(--lv-muted); font-weight: 700; }" +
      ".level-select .level-card p { margin: 0; flex: 1; }" +
      ".level-select .level-status { font-size: 0.78rem; min-height: 1em; font-weight: 600; }" +
      ".level-select .level-best { font-size: 0.78rem; color: var(--lv-muted); margin: 0; }" +
      ".level-select button { font: inherit; color: inherit; cursor: pointer; min-height: 2.75rem; padding: 0.3rem 0.8rem; background: transparent; border: 1px solid var(--lv-border); border-radius: 999px; }" +
      ".level-select button[aria-disabled=\"true\"] { cursor: default; border-style: dashed; opacity: 0.8; }" +
      ".level-select button:focus-visible { outline: 3px solid var(--lv-focus); outline-offset: 2px; }" +
      ".level-select .level-live { position: absolute; width: 1px; height: 1px; margin: -1px; padding: 0; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; border: 0; }" +
      "@media (prefers-reduced-motion: no-preference) { html:not([data-reduced-motion=\"true\"]) .level-select .level-card { transition: background-color 0.2s ease; } }";
    document.head.append(style);
  }

  // ---- the component ------------------------------------------------------

  function create(options) {
    const opts = options || {};
    const id = ++instanceCounter;
    const domId = opts.domId || (id === 1 ? "level-select" : "level-select-" + id);
    let levels = normaliseLevels(opts.levels);
    let title = typeof opts.title === "string" && opts.title ? opts.title : "Levels";
    let state = sanitizeState(levels, opts.state);
    let onChange = typeof opts.onChange === "function" ? opts.onChange : null;
    let onStart = typeof opts.onStart === "function" ? opts.onStart : null;
    let canPlay = typeof opts.canPlay === "function" ? opts.canPlay : null;
    let overlay = null; let grid = null; let progressEl = null; let live = null; let closeBtn = null;
    let focusId = null; let opener = null; let built = false;
    const cards = new Map();   // level id -> { li, button, status }

    function persist() {
      const copy = cloneState(state);
      if (onChange) { try { onChange(copy); } catch (e) { /* the game's callback must not break the screen */ } }
      else if (typeof opts.persist === "function") opts.persist(copy);
    }

    function reasonFor(level) {
      const base = lockReason(levels, state, level);
      if (base) return base;
      if (canPlay) {
        let verdict = true;
        try { verdict = canPlay(level); } catch (e) { verdict = true; }
        if (verdict === false) return level.unlock_text || "Not available yet";
        if (typeof verdict === "string" && verdict) return verdict;
      }
      return "";
    }

    function say(text) {
      if (!live) return;
      live.textContent = "";
      setTimeout(() => { live.textContent = text; }, 20);
    }

    function build() {
      if (built || typeof document === "undefined") return;
      built = true;
      ensureStyles();
      overlay = document.createElement("div");
      overlay.id = domId;
      overlay.className = "level-select";
      overlay.hidden = true;
      overlay.setAttribute("role", "dialog");
      overlay.setAttribute("aria-modal", "true");
      const panel = document.createElement("div");
      panel.className = "level-select-panel";
      const head = document.createElement("div");
      head.className = "level-head";
      const heading = document.createElement("h2");
      heading.id = domId + "-title";
      heading.textContent = title;
      overlay.setAttribute("aria-labelledby", heading.id);
      progressEl = document.createElement("p");
      progressEl.className = "level-progress";
      head.append(heading, progressEl);
      const help = document.createElement("p");
      help.className = "level-help";
      help.id = domId + "-help";
      help.textContent = "Arrow keys move between levels, Enter plays the focused level, Escape closes. Every fifth level is a game mode or a new mechanic.";
      grid = document.createElement("ol");
      grid.className = "level-grid";
      grid.setAttribute("aria-describedby", help.id);
      live = document.createElement("p");
      live.className = "level-live";
      live.setAttribute("role", "status");
      live.setAttribute("aria-live", "polite");
      closeBtn = document.createElement("button");
      closeBtn.type = "button";
      closeBtn.className = "secondary level-close";
      closeBtn.textContent = "Close";
      closeBtn.addEventListener("click", close);
      panel.append(head, help, grid, closeBtn, live);
      overlay.append(panel);
      document.addEventListener("keydown", onOverlayKey);
      overlay.addEventListener("mousedown", (event) => { if (event.target === overlay) close(); });
      document.body.append(overlay);
      buildCards();
    }

    function buildCards() {
      grid.textContent = "";
      cards.clear();
      levels.forEach((level, index) => {
        const li = document.createElement("li");
        li.className = "level-card level-card--" + level.kind;
        li.dataset.level = level.id;
        const head = document.createElement("strong");
        head.textContent = (index + 1) + ". " + level.title;
        const kind = document.createElement("span");
        kind.className = "level-kind";
        kind.textContent = KIND_GLYPH[level.kind] + KINDS[level.kind];
        const blurb = document.createElement("p");
        blurb.textContent = level.blurb || "";
        const status = document.createElement("span");
        status.className = "level-status";
        status.id = domId + "-st-" + index;
        const best = document.createElement("p");
        best.className = "level-best";
        best.id = domId + "-best-" + index;
        const button = document.createElement("button");
        button.type = "button";
        button.className = "secondary level-play";
        button.tabIndex = -1;
        button.dataset.level = level.id;
        button.setAttribute("aria-describedby", [status.id, best.id].join(" "));
        button.addEventListener("click", () => { setFocus(level.id); activate(level.id); });
        button.addEventListener("focus", () => setFocus(level.id));
        button.addEventListener("keydown", (event) => onCardKey(event, level.id));
        li.append(head, kind, blurb, status, best, button);
        grid.append(li);
        cards.set(level.id, { li, button, status, best, head });
      });
    }

    function paint() {
      if (!built) return;
      const p = progress(levels, state);
      progressEl.textContent = p.done + " of " + p.total + " complete";
      levels.forEach((level, index) => {
        const c = cards.get(level.id);
        const done = state.done.includes(level.id);
        const reason = reasonFor(level);
        const open = reason === "";
        c.li.className = "level-card level-card--" + level.kind + (done ? " level-card--done" : "") + (open ? "" : " level-card--locked");
        c.li.dataset.state = done ? "done" : open ? "ready" : "locked";
        c.status.textContent = done ? "✓ Completed" : open ? "▶ Ready" : "⊘ Locked: " + reason;
        const best = state.best[level.id];
        c.best.textContent = best ? "Best: " + (best.text || best.value) : "";
        c.best.hidden = !best;
        const verb = done ? "Play again" : open ? "Play" : "Locked";
        c.button.textContent = verb;
        c.button.setAttribute("aria-disabled", open ? "false" : "true");
        c.button.setAttribute("aria-label", verb + ": level " + (index + 1) + ", " + level.title);
        c.button.tabIndex = level.id === focusId ? 0 : -1;
      });
    }

    function setFocus(levelId) {
      if (!cards.has(levelId)) return;
      focusId = levelId;
      cards.forEach((c, k) => { c.button.tabIndex = k === levelId ? 0 : -1; });
    }

    function activate(levelId) {
      const level = levels.find((l) => l.id === levelId);
      if (!level) return false;
      const reason = reasonFor(level);
      if (reason) { say(level.title + " is locked. " + reason + "."); return false; }
      return start(levelId);
    }

    function columnCount() {
      const list = levels.map((l) => cards.get(l.id).li);
      if (!list.length) return 1;
      const top = list[0].offsetTop;
      let n = 0;
      while (n < list.length && list[n].offsetTop === top) n++;
      return Math.max(n, 1);
    }

    function onCardKey(event, levelId) {
      if (event.altKey || event.ctrlKey || event.metaKey) return;
      const index = levels.findIndex((l) => l.id === levelId);
      const cols = columnCount();
      let target = index;
      switch (event.key) {
        case "ArrowRight": target = Math.min(index + 1, levels.length - 1); break;
        case "ArrowLeft": target = Math.max(index - 1, 0); break;
        case "ArrowDown": target = index + cols < levels.length ? index + cols : index; break;
        case "ArrowUp": target = index - cols >= 0 ? index - cols : index; break;
        case "Home": target = event.shiftKey ? 0 : index - (index % cols); break;
        case "End": target = event.shiftKey ? levels.length - 1 : Math.min(index - (index % cols) + cols - 1, levels.length - 1); break;
        default: return;
      }
      event.preventDefault();
      const next = cards.get(levels[target].id);
      setFocus(levels[target].id);
      next.button.focus();
    }

    function onOverlayKey(event) {
      if (!overlay || overlay.hidden) return;
      if (event.key === "Escape") { event.preventDefault(); close(); return; }
      if (event.key !== "Tab") return;
      // Two tab stops inside the dialog (the current level and Close): keep Tab on them.
      const stops = [focusId && cards.get(focusId) ? cards.get(focusId).button : null, closeBtn].filter(Boolean);
      if (!stops.length) return;
      const at = stops.indexOf(document.activeElement);
      const next = event.shiftKey ? (at <= 0 ? stops.length - 1 : at - 1) : (at < 0 || at === stops.length - 1 ? 0 : at + 1);
      event.preventDefault();
      stops[next].focus();
    }

    function start(levelId) {
      const level = levels.find((l) => l.id === levelId);
      if (!level || reasonFor(level)) return false;
      close();
      try { if (onStart) onStart(levelId, level); } catch (e) { /* the game decides what a level does */ }
      return true;
    }

    function complete(levelId, result) {
      const outcome = recordResult(levels, state, levelId, result);
      if (!outcome.changed) return false;
      state = outcome.state;
      persist();
      paint();
      return true;
    }

    function open() {
      if (!levels.length) return;
      build();
      opener = document.activeElement && document.activeElement !== document.body ? document.activeElement : null;
      const next = nextUp(levels, state);
      if (!focusId || !cards.has(focusId)) focusId = (next || levels[0]).id;
      else if (next) focusId = next.id;
      paint();
      overlay.hidden = false;
      const target = cards.get(focusId).button;
      target.focus();
      if (target.scrollIntoView) target.scrollIntoView({ block: "nearest" });
    }

    function close() {
      if (!overlay || overlay.hidden) return;
      overlay.hidden = true;
      if (opener && document.contains(opener) && opener.focus) opener.focus();
      opener = null;
    }

    function setState(raw) {
      state = sanitizeState(levels, raw);
      paint();
    }

    function setLevels(list, newTitle) {
      levels = normaliseLevels(list);
      if (typeof newTitle === "string" && newTitle) title = newTitle;
      state = sanitizeState(levels, state);
      if (built) {
        const heading = document.getElementById(domId + "-title");
        if (heading) heading.textContent = title;
        buildCards();
        paint();
      }
    }

    const api = {
      open, close, complete, start, setState, setLevels,
      refresh: paint,
      getState: () => cloneState(state),
      isDone: (levelId) => state.done.includes(levelId),
      done: () => state.done.slice(),
      best: (levelId) => (state.best[levelId] ? Object.assign({}, state.best[levelId]) : null),
      isOpen: () => Boolean(overlay && !overlay.hidden),
      configure(cfg) {
        const c = cfg || {};
        if (typeof c.onChange === "function") onChange = c.onChange;
        if (typeof c.onStart === "function") onStart = c.onStart;
        if (typeof c.canPlay === "function") canPlay = c.canPlay;
        if (c.state !== undefined) setState(c.state);
        else paint();
      },
      hasOnChange: () => Boolean(onChange),
      levels: () => levels.slice(),
    };

    if (opts.trigger && typeof document !== "undefined") {
      const el = typeof opts.trigger === "string" ? document.querySelector(opts.trigger) : opts.trigger;
      if (el) el.addEventListener("click", open);
    }
    return api;
  }

  // ---- the <script data-game-id> path (the first version's API) -----------

  const script = typeof document !== "undefined" ? document.currentScript : null;
  const GAME_ID = script && script.dataset ? script.dataset.gameId : "";
  const NS = { create, logic, KINDS };
  root.NoyvjLevels = NS;
  if (!GAME_ID) return;   // no data-game-id: the factory only, nothing auto-loaded

  const KEY = "levels:" + GAME_ID;
  const LEVELS_URL = script.dataset.levels || "levels.json";
  function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* convenience only */ } }

  // Calls made before levels.json arrives wait here and are replayed.
  let instance = null;
  let pending = { config: null, completes: [], state: undefined, openRequested: false };

  const singleton = {
    create, logic, KINDS,
    open() { if (instance) instance.open(); else pending.openRequested = true; },
    close() { if (instance) instance.close(); },
    complete(id, result) { if (instance) return instance.complete(id, result); pending.completes.push([id, result]); return false; },
    start(id) { return instance ? instance.start(id) : false; },
    isDone: (id) => (instance ? instance.isDone(id) : false),
    done: () => (instance ? instance.done() : []),
    best: (id) => (instance ? instance.best(id) : null),
    getState: () => (instance ? instance.getState() : emptyState()),
    setState(s) { if (instance) instance.setState(s); else pending.state = s; },
    refresh() { if (instance) instance.refresh(); },
    configure(cfg) {
      if (instance) instance.configure(cfg);
      else pending.config = Object.assign({}, pending.config || {}, cfg || {});
    },
    isOpen: () => Boolean(instance && instance.isOpen()),
    ready: () => Boolean(instance),   // levels.json has loaded and the screen can open
    levels: () => (instance ? instance.levels() : []),
  };
  root.NoyvjLevels = singleton;

  fetch(LEVELS_URL, { cache: "no-cache" })
    .then((r) => (r.ok ? r.json() : null))
    .then((data) => {
      const list = normaliseLevels(data && data.levels);
      if (!list.length) return;
      const saved = (() => { try { return JSON.parse(lsGet(KEY) || "[]"); } catch (e) { return []; } })();
      instance = create({
        game: GAME_ID, title: data.title, levels: list, state: saved, domId: "level-select",
        persist: (s) => lsSet(KEY, JSON.stringify(s.done)),   // fallback only: replaced the moment a game supplies onChange
        onStart: (id) => { try { if (typeof root.NoyvjLevelStart === "function") root.NoyvjLevelStart(id); } catch (e) { /* the game decides */ } },
      });
      const cfg = pending.config;
      if (cfg) {
        const userStart = cfg.onStart;
        const merged = Object.assign({}, cfg);
        if (userStart) merged.onStart = (id, level) => { userStart(id, level); try { if (typeof root.NoyvjLevelStart === "function") root.NoyvjLevelStart(id); } catch (e) { /* ignore */ } };
        instance.configure(merged);
      }
      if (pending.state !== undefined) instance.setState(pending.state);
      pending.completes.forEach(([id, result]) => instance.complete(id, result));
      const trigger = document.querySelector(script.dataset.open || "#levels-open-button");
      if (trigger) trigger.addEventListener("click", () => instance.open());
      if (pending.openRequested) instance.open();
      pending = { config: null, completes: [], state: undefined, openRequested: false };
    })
    .catch(() => { /* no levels file: the game is unchanged */ });
})(typeof window !== "undefined" ? window : globalThis);
