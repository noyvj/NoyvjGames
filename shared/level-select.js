/*
 * Shared level select (planning/TODO.md W-1, from your Round 3 answer: "a
 * level select where every 5 levels is either a game mode or a new mechanic").
 * One include per game that has grown complex enough to want one:
 *   <button id="levels-open-button" type="button">Levels</button>
 *   <script src="../../shared/level-select.js" data-game-id="canopy"
 *           data-levels="levels.json" data-open="#levels-open-button"></script>
 *
 * levels.json:
 *   { "title": "Canopy levels",
 *     "levels": [ { "id": "wren_hollow", "title": "Wren Hollow",
 *                   "kind": "level",            // "level" | "mode" | "mechanic"
 *                   "blurb": "The standard forest.",
 *                   "requires": []              // ids that must be completed first
 *                 }, ... ] }
 * The list is shown in order in rows of five; by convention every fifth entry is
 * a "mode" (a different way to play) or a "mechanic" (a new rule the base game
 * does not have). A level is locked until every id in `requires` is completed.
 *
 * Games talk to it through window.NoyvjLevels:
 *   complete(id)   mark a level completed (persisted per browser)
 *   isDone(id) / done()  read progress
 *   open() / close()
 * and it calls window.NoyvjLevelStart(levelId) (a function the game defines, for
 * Python: assign a proxy to window.NoyvjLevelStart) when the player presses
 * Play on an unlocked level. Progress lives in localStorage
 * (`levels:<game>`), never in the save. Text is written with textContent only,
 * and a missing or malformed levels.json leaves the game unchanged.
 */
(function () {
  const script = document.currentScript;
  const GAME_ID = script && script.dataset.gameId;
  const LEVELS_URL = (script && script.dataset.levels) || "levels.json";
  if (!GAME_ID) {
    console.error("level-select.js: needs data-game-id");
    return;
  }
  const KEY = `levels:${GAME_ID}`;
  const KINDS = { level: "Level", mode: "Game mode", mechanic: "New mechanic" };
  let title = "Levels";
  let levels = [];
  let doneIds = [];
  let overlay = null;
  let grid = null;

  function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* convenience only */ } }

  function loadDone() {
    const known = new Set(levels.map((l) => l.id));
    let stored = [];
    try { stored = JSON.parse(lsGet(KEY) || "[]"); } catch (e) { stored = []; }
    doneIds = Array.isArray(stored) ? stored.filter((id, i) => typeof id === "string" && known.has(id) && stored.indexOf(id) === i) : [];
  }

  function unlocked(level) {
    return (level.requires || []).every((id) => doneIds.includes(id));
  }

  function render() {
    if (!grid) return;
    grid.textContent = "";
    levels.forEach((level, index) => {
      const card = document.createElement("div");
      card.className = `level-card level-card--${level.kind}`;
      const done = doneIds.includes(level.id);
      const open = unlocked(level);
      const head = document.createElement("strong");
      head.textContent = `${index + 1}. ${level.title}`;
      const kind = document.createElement("span");
      kind.className = "level-kind";
      kind.textContent = KINDS[level.kind] || "Level";
      const blurb = document.createElement("p");
      blurb.textContent = level.blurb || "";
      const button = document.createElement("button");
      button.type = "button";
      button.className = "secondary";
      button.disabled = !open;
      button.textContent = done ? "Play again" : open ? "Play" : "Locked";
      button.addEventListener("click", () => start(level.id));
      const status = document.createElement("span");
      status.className = "level-status";
      status.textContent = done ? "Completed" : open ? "" : "Complete the earlier levels first";
      card.append(head, kind, blurb, status, button);
      grid.append(card);
    });
  }

  function start(id) {
    const level = levels.find((l) => l.id === id);
    if (!level || !unlocked(level)) return false;
    close();
    try {
      if (typeof window.NoyvjLevelStart === "function") window.NoyvjLevelStart(id);
    } catch (e) { /* the game decides what a level does */ }
    return true;
  }

  function complete(id) {
    if (!levels.some((l) => l.id === id) || doneIds.includes(id)) return false;
    doneIds.push(id);
    lsSet(KEY, JSON.stringify(doneIds));
    render();
    return true;
  }

  function build() {
    overlay = document.createElement("div");
    overlay.id = "level-select";
    overlay.hidden = true;
    overlay.setAttribute("role", "dialog");
    overlay.setAttribute("aria-modal", "true");
    overlay.setAttribute("aria-label", title);
    const panel = document.createElement("div");
    panel.className = "level-select-panel";
    const heading = document.createElement("h2");
    heading.textContent = title;
    const close_ = document.createElement("button");
    close_.type = "button";
    close_.className = "secondary";
    close_.textContent = "Close";
    close_.addEventListener("click", close);
    grid = document.createElement("div");
    grid.className = "level-grid";
    panel.append(heading, grid, close_);
    overlay.append(panel);
    const style = document.createElement("style");
    style.textContent =
      "#level-select { position: fixed; inset: 0; z-index: 900; display: flex; align-items: center; justify-content: center; background: rgba(0,0,0,0.6); }" +
      "#level-select[hidden] { display: none; }" +
      "#level-select .level-select-panel { max-width: 860px; width: calc(100% - 2rem); max-height: 85vh; overflow: auto; padding: 1rem 1.2rem; border-radius: 12px; background: var(--level-bg, #1c2033); color: var(--level-fg, #eaeaf0); border: 1px solid rgba(140,160,255,0.3); }" +
      "html[data-theme=\"light\"] #level-select .level-select-panel { --level-bg: #f7f8fc; --level-fg: #1b2033; }" +
      "#level-select .level-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 0.6rem; margin: 0.8rem 0; }" +
      "#level-select .level-card { display: flex; flex-direction: column; gap: 0.25rem; padding: 0.6rem; border: 1px solid rgba(140,160,255,0.25); border-radius: 8px; font-size: 0.85rem; }" +
      "#level-select .level-card--mode, #level-select .level-card--mechanic { border-width: 2px; }" +
      "#level-select .level-kind { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.04em; opacity: 0.7; }" +
      "#level-select .level-card p { margin: 0; flex: 1; }" +
      "#level-select .level-status { font-size: 0.75rem; opacity: 0.8; min-height: 1em; }";
    document.head.append(style);
    document.body.append(overlay);
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && !overlay.hidden) close();
    });
  }

  function open() { if (overlay) { render(); overlay.hidden = false; } }
  function close() { if (overlay) overlay.hidden = true; }

  window.NoyvjLevels = {
    open, close, complete,
    isDone: (id) => doneIds.includes(id),
    done: () => doneIds.slice(),
    start,
  };

  fetch(LEVELS_URL, { cache: "no-cache" })
    .then((r) => (r.ok ? r.json() : null))
    .then((data) => {
      const list = data && Array.isArray(data.levels) ? data.levels : [];
      levels = list.filter((l) => l && typeof l.id === "string" && typeof l.title === "string");
      if (!levels.length) return;
      title = typeof data.title === "string" ? data.title : title;
      loadDone();
      build();
      const trigger = document.querySelector(script.dataset.open || "#levels-open-button");
      if (trigger) trigger.addEventListener("click", open);
    })
    .catch(() => { /* no levels file: the game is unchanged */ });
})();
